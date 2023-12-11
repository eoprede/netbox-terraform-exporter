# Netbox to terraform/json exporter
This script is designed to address the issue of not having proper change control/change management in Netbox in a semi-automatic way. It will query the Netbox for specified prefixes and output them in a terraform.json format. If the script detects any changes to outputs, it will automatically create a Github pull request to merge the changes. Netowrk engieers or other responsible parties then can review the PR to ensure expected changes are making it through. This script is designed to be run either as a Lambda function in AWS or as a standalong script/cron job.

Note that while this script does work as is, it is more so meant not as a final product but as a starting point for your own customizations. 

## Environment variables
* NETBOX_URL - URL to the Netbox instance, i.e. "https://demo.nautobot.com"
* NETBOX_TOKEN - Token to access the Netbox API
* GIT_TOKEN - Token to access the Github API
* GIT_REPO - Github repository to work with, i.e. "eoprede/netbox-terraform-exporter"
* GIT_REPO_PATH - Path to the folder to clone repo into, optional

## Secrets to use for Lambda function
* GithubTOKEN - Token to access the Github API
* NetboxTOKEN - Token to access the Netbox API

## Packaging
As it is not possible to install additional packages for Lambda function, script has all the dependencies included. When deploying it to Lambda, make sure you zip the whole content of lambda folder and upload it to Lambda as zip.

## Running on a Linux/MacOS (or maybe even Windows) host
Make sure git CLI is installed, as the git library depends on it. Just set environments and run lambda function.py, make sure that lambda subfolder is in your path (or just execute file from it). 

## Running as a Lambda function
Create a new Lambda function, set the environment variables and upload the zip file. Set the handler to lambda_function.lambda_handler. Set the timeout to 5 minutes or however long it takes to execute. For security reasons, secrets are not set as environment variables but as Lambda secrets and your function will need sufficient permissions to access them. You will need to use git layer for your lambda, as git library requires it - https://github.com/lambci/git-lambda-layer

## Input file structure
Script is looking for the 2 keys in the file:

* lookup_prefixes - dictionary of prefixes to look up in Netbox, key is the name of the output and values are k:v pairs of parameters for Netbox query in URL format.
* return_fields - list of fields to return from Netbox, if not specified defaults to ["prefix,description"]

## Output file structure
Output files are in the tf.json format, suitable for the direct import to terraform import as a module. A very basic example of importing the values and displaying them as output:
```
module "test" {
source = "github.com/eoprede/netbox-terraform-exporter/output"
}
output "demo" {
value = module.test.sample_2_tenant_and_prefix_example
}
```

### Demo values
I am using Nautobot (a fork of Netbox) demo instance for the demo. I am not affiliated with Nautobot in any way, so I have no clue how long it will stay up. However, all the outputs in the output folder were automatically generated from it.
