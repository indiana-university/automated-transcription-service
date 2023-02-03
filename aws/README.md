# AWS deployment code for Automated Transcription Service (ATS)

## Part I: Build and push the container image

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

## Part II: Deploy infrastructure

The deployment is set up to store remote state in an S3 bucket, so begin by creating that bucket:
```
aws s3 mb s3://<TF_STATE_BUCKET_NAME>
```

Switch to the `terraform` directory:

```
cd ../terraform
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

