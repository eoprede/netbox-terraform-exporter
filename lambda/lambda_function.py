#!/usr/bin/env python3

"""Basic example of an HTTP client that does not depend on any external libraries.
Copy-pasted from https://github.com/bowmanjd/pysimpleurl/blob/main/pysimpleurl.py"""


import json
import typing
import urllib.error
import urllib.parse
import urllib.request
from email.message import Message
from git import Repo, exc
import os
import time
import ssl


class Response(typing.NamedTuple):
    """Container for HTTP response."""

    body: str
    headers: Message
    status: int
    error_count: int = 0

    def json(self) -> typing.Any:
        """
        Decode body's JSON.

        Returns:
            Pythonic representation of the JSON object
        """
        try:
            output = json.loads(self.body)
        except json.JSONDecodeError:
            output = ""
        return output


def request(
    url: str,
    data: dict = None,
    params: dict = None,
    headers: dict = None,
    method: str = "GET",
    data_as_json: bool = True,
    error_count: int = 0,
) -> Response:
    """
    Perform HTTP request.

    Args:
        url: url to fetch
        data: dict of keys/values to be encoded and submitted
        params: dict of keys/values to be encoded in URL query string
        headers: optional dict of request headers
        method: HTTP method , such as GET or POST
        data_as_json: if True, data will be JSON-encoded
        error_count: optional current count of HTTP errors, to manage recursion

    Raises:
        URLError: if url starts with anything other than "http"

    Returns:
        A dict with headers, body, status code, and, if applicable, object
        rendered from JSON
    """
    if not url.startswith("http"):
        raise urllib.error.URLError("Incorrect and possibly insecure protocol in url")
    method = method.upper()
    request_data = None
    headers = headers or {}
    data = data or {}
    params = params or {}
    headers = {"Accept": "application/json", **headers}

    if method == "GET":
        params = {**params, **data}
        data = None

    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True, safe="/")

    if data:
        if data_as_json:
            request_data = json.dumps(data).encode()
            headers["Content-Type"] = "application/json; charset=UTF-8"
        else:
            request_data = urllib.parse.urlencode(data).encode()

    httprequest = urllib.request.Request(
        url, data=request_data, headers=headers, method=method
    )

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(httprequest, context=ctx) as httpresponse:
            response = Response(
                headers=httpresponse.headers,
                status=httpresponse.status,
                body=httpresponse.read().decode(
                    httpresponse.headers.get_content_charset("utf-8")
                ),
            )
    except urllib.error.HTTPError as e:
        response = Response(
            body=str(e.reason),
            headers=e.headers,
            status=e.code,
            error_count=error_count + 1,
        )

    return response


def read_json(path):
    with open(path, "r") as read_file:
        output = json.load(read_file)
    return output


def write_json(path, data):
    with open(path, "w") as write_file:
        json.dump(data, write_file, indent=4)


def get_prefixes(netbox_url, params):
    params_list = []
    for k, v in params.items():
        params_list.append(f"{k}={v}")
    params_string = "&".join(params_list)
    url = f"{netbox_url}/api/ipam/prefixes/?{params_string}"
    headers = {
        "Authorization": "Token "
        + os.environ.get("NETBOX_TOKEN")
    }
    response = request(url, headers=headers)
    return response.json()


def build_list_output(input, filename_key):
    # Build output as a list of maps, currently only prefix and description are available
    results = {"output": {}}
    for k, v in input["lookup_prefixes"].items():
        json_response = get_prefixes(os.environ.get("NETBOX_URL"), v)
        if json_response["count"] > 0:
            results["output"].update({f"{filename_key}_{k}": {"value": []}})
            for p in json_response["results"]:
                results["output"][f"{filename_key}_{k}"]["value"].append(
                    {"prefix": p["prefix"], "description": p["description"]}
                )
    return results


def clone_git_repo(repo_url, clone_path):
    return Repo.clone_from(repo_url, clone_path)


def create_git_pr(git_repo, git_token, head_ref):
    url = f"https://api.github.com/repos/{git_repo}/pulls"
    headers = {
        "Authorization": "Bearer " + git_token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = {
        "title": "Automatic Prefix Merge",
        "head": head_ref,
        "base": "main",
        "body": "Automatically created PR by Netbox Lambda",
    }
    response = request(url, headers=headers, data=data, method="POST")
    return response


def get_secrets(secret_key) -> str:
    # Grab secret keys from secrets manager
    session = boto3.session.Session()
    client = session.client(
        service_name="secretsmanager", endpoint_url=os.environ["SECRETSMANAGER_URL"]
    )
    secret_name = client.describe_secret(SecretId=secret_key)["ARN"]
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    secret = get_secret_value_response.get("SecretBinary")
    if secret:
        return secret.decode("utf-8")
    else:
        print("Secret Irretrievable!")
        return None


def lambda_handler(event, context):
    # Handles setting up virtual environment when being executed as Lambda
    global boto3
    import boto3
    os.environ["HTTPS_PROXY"] = os.environ.get("PROXY_URL", "") #in case you need to set a proxy from another env
    os.environ[
        "SECRETSMANAGER_URL"
    ] = f"https://secretsmanager.{os.environ.get('AWS_REGION')}.amazonaws.com"
    os.environ[
        "NO_PROXY"
    ] = f"secretsmanager.{os.environ.get('AWS_REGION')}.amazonaws.com, {os.environ.get('NETBOX_URL').replace('https://', '')}"
    os.environ["GIT_TOKEN"] = get_secrets("GithubTOKEN")
    os.environ["NETBOX_TOKEN"] = get_secrets("NetboxTOKEN")
    run()


def run() -> None:
    git_repo = os.environ.get("GIT_REPO")
    git_repo_path = os.environ.get("GIT_REPO_PATH", "/tmp/git_repo")
    git_token = os.environ.get("GIT_TOKEN")

    try:
        print(f"Cloning {git_repo} to {git_repo_path}")
        repo = clone_git_repo(
            f"https://{git_token}@github.com/{git_repo}.git", git_repo_path
        )
    except exc.GitCommandError as e:
        #print(e)
        if "already exists and is not an empty directory" in str(e):
            print("Repo already exists, pulling latest")
            repo = Repo(git_repo_path)
            repo.git.checkout("main")
            repo.remotes.origin.pull()

    print("Clone complete, checking out new branch")
    new_branch = repo.create_head(f"{int(time.time())}_auto_update")
    new_branch.checkout()
    print(f"Checked out {str(repo.head.ref)}")
    commits_added = False

    repo.config_writer().set_value("user", "name", "Bot").release()
    repo.config_writer().set_value("user", "email", "bot@local.com").release()

    for f in os.listdir(f"{git_repo_path}/input"):
        if f.endswith(".json"):
            print(f"Processing {f}")
            input = read_json(f"{git_repo_path}/input/{f}")
            results = build_list_output(input, f.replace(".json", ""))
            write_json(
                f"{git_repo_path}/output/{f.replace('.json', '.tf.json')}", results
            )
            if "nothing to commit, working tree clean" in repo.git.status():
                print("No changes to commit")
            else:
                repo.git.add(f"{git_repo_path}/output/{f.replace('.json', '.tf.json')}")
                repo.git.commit(m=f"Update {f.replace('.json', '.tf.json')}")
                print("Changes commited")
                commits_added = True

    if commits_added:
        print("Pushing changes")
        repo.git.push("--set-upstream", "origin", str(repo.head.ref))
        print(f"Creating PR for {str(repo.head.ref)}")
        r = create_git_pr(git_repo, git_token, str(repo.head.ref))
        print(r.status)


if __name__ == "__main__":
    run()
