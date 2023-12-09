# Netbox to terraform/json exporter
This script is designed to address the issue of not having proper change control/change management in Netbox in a semi-automatic way. It will query the Netbox for specified prefixes and output them in a terraform.json format. If the script detects any changes to outputs, it will automatically create a Github pull request to merge the changes. This script is designed to be run either as a Lambda function in AWS or as a standalong script/cron job.

Note that while this script does work as is, it is more so meant not as a final product but as a starting point for your own customizations. 

## Environment variables
* NETBOX_URL - URL to the Netbox instance
* NETBOX_TOKEN - Token to access the Netbox API
* GIT_TOKEN - Token to access the Github API
* GIT_REPO - Github repository to work with
* GIT_REPO_PATH - Path to the folder to clone repo into, optional

## Secrets to use for Lambda function
* GithubTOKEN - Token to access the Github API
* NetboxTOKEN - Token to access the Netbox API

## Packaging
As it is not possible to install additional packages for Lambda function, script has all the dependencies included. When deploying it to Lambda, make sure you zip the whole content of lambda folder and upload it to Lambda as zip.

## Running on a Linux/MacOS (or maybe even Windows) host
Just set environments and run lambda function.py, make sure that lambda subfolder is in your path (or just execute file from it).

## Running as a Lambda function
Create a new Lambda function, set the environment variables and upload the zip file. Set the handler to lambda_function.lambda_handler. Set the timeout to 5 minutes or however long it takes to execute. For security reasons, secrets are not set as environment variables but as Lambda secrets and your function will need sufficient permissions to access them.