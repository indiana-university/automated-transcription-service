# AWS code for Automated Transcription Service (ATS)

## Instructions for generating a Word document from an ATS json file via the command line without an AWS pipeline

This is guide for using a Python script in this project to generate a Word document from an AWS ATS json files. This is primarily written for use an a *nix machine but should similarly work on other Operating Systems. These steps will install required Python libraries in the Users' space.

Once this is complete it does not need to be repeated. Simply follow step #5 for executing the generation. If a developer changes the translate script step #6 may be used to update your local version.

1. Open a `Terminal`. Hint: By default Paste is done via Shift+Ctrl+V, if in doubt check the menu of your Terminal
2. Verify python3 is installed. This should return `Python 3.x.x`
```
python3 --version
```
2. Prepare Python's package manager for installing required Python libraries. Hint: Run this as two commands consecutively as shown, otherwise an error occurs
```
python3 -m pip install --user --upgrade pip
python3 -m pip install --user --upgrade Pillow
```
3. Install required libraries
```
python3 -m pip install --user python-docx boto3
```
4. Checkout this project
```
git clone <REPO URL>
```
5. Execute json to Word. The result will be dropped in the location of inputFile
```
python3 ~/automated-transcription-service/aws/src/lambda/transcribe_to_docx.py --inputFile <JSON_FILE>
```
6. (Optional) If a developer makes changes they can be picked up with the following command
```
cd automated-transcription-service; git pull
cd ~/
```

## Building an AWS pipeline
### Part I: Build and push the container image

Begin by creating an ECR repository:

```
aws ecr create-repository --repository-name ats
```

Change to the `src` folder and build the container image:

```
cd aws/src
docker build -t ats .
```

NOTE: The instructions to tag and push the image can easily be found by clicking on the name of the repository in the web console and then clicking the `View push commands` button in the upper right corner. The web console will insert the appropriate values into each command. Alternatively, you can use the examples below to tag and push the image, supplying the appropriate values for account and region.

Log in to ECR:

```
aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com
```

Tag the image:

```
docker tag ats:latest <ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/ats:latest
```

Push the image to ECR for deployment:

```
docker push <ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/ats:latest
```

### Part II: Deploy infrastructure

The deployment is set up to store remote state in an S3 bucket, so begin by creating that bucket:
```
aws s3 mb s3://<TF_STATE_BUCKET_NAME>
```

Switch to the `terraform` directory:

```
cd ./terraform
```

Rename the auto.tfvars template:

```
mv ats.auto.tfvars.template ats.auto.tfvars
```

Edit the variables in the ats.auto.tfvars as necessary.

Run `terraform init` to download the necessary provider(s). Note that you must provide the name of remote state bucket created above. If you are not using the default AWS profile for access then you should also include an AWS named profile:

```
terraform init -backend-config="bucket=<TF_STATE_BUCKET_NAME>" -backend-config="profile=<AWS named profile>"
```

Now run `terraform plan` to preview the deployment:

```
terraform plan
```

Finally, run `terraform apply` to actually deploy the components of the application:

```
terraform apply
```

### (Optional) Part III: Retrieving files from S3

The AWS web console does not allow downloading multiple files at once. There are ways to get around that:

* Use the AWS CLI

All files in the S3 bucket
```
aws s3 cp s3://my-download-20221110204121545700000002 ~/Downloads --recursive
```
or a specific folder
```
aws s3 cp s3://my-download-20221110204121545700000002/20230324 ~/Downloads --recursive
```
There are also ways to include / exclude files using the `--exclude` and `--include` flags. See https://docs.aws.amazon.com/cli/latest/reference/s3/cp.html for more details.

* If using AWS CLI is not viable the AWS web console allows multi select and using "Open" which barring popup blockers and depending on the file type will open the files in new tabs and download them
