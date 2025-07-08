# AWS code for Automated Transcription Service (ATS)
### Deploy infrastructure

>[!NOTE]
>This guide assumes you have the prerequisites installed and configured. If you haven't done so, please refer to the [prerequisites guide](../doc/prerequisites.md) before proceeding.

Clone the repository:

```bash
git clone https://github.com/indiana-university/automated-transcription-service.git
cd automated-transcription-service/aws/terraform/
```

Run `terraform init` to download the necessary provider(s). If you are not using the default AWS profile for access then you should also include an AWS named profile:

```bash
terraform init -backend-config="profile=<AWS named profile>"
```

Now run `terraform plan` to preview the deployment:

```bash
terraform plan
```

Finally, run `terraform apply` to actually deploy the components of the application:

```bash
terraform apply
```

>[!NOTE]
>There are default values for all variables. If you want to change any values you can either rename and use the provided `ats.auto.tfvars.template` file or pass variables in as command line arguments. For example, to change the region you can run:

```bash
terraform apply -var="region=us-west-2"
```

The deployment will take a few minutes to complete. Once it is done, you should see the outputs and can test the application by uploading a file to the upload bucket. The upload bucket name is in the outputs of the terraform apply command. The output will be in the download bucket, also in the outputs of the terraform apply command.

### Testing
Download this short audio file to your workstation and then upload it to the upload bucket to test the application: https://upload.wikimedia.org/wikipedia/commons/0/0a/Charles_Duke_Intro.ogg

### Custom Docker Image (Optional)

By default, the DOCX Lambda function uses a pre-built Docker image from `quay.io/rds/ats:latest`. If you need to customize the image, you have two options:

#### Option 1: Build During Terraform Deployment (Legacy Mode)

Set the `build_docx_image` variable to `true` to build the image during deployment:

```bash
terraform apply -var="build_docx_image=true"
```

Or add it to your `ats.auto.tfvars` file:
```hcl
build_docx_image = true
```

This will create an ECR repository and build the image from the `../src/lambda/docx` directory during the Terraform deployment.

>[!WARNING]
>This option increases deployment time and resource usage significantly.

#### Option 2: Pre-build and Push to ECR (Recommended)

For better performance, pre-build your custom image and push it to ECR, then reference it:

1. **Create an ECR repository** in your AWS account:
   ```bash
   aws ecr create-repository --repository-name ats-custom --region us-east-1
   ```

2. **Build and push your custom image**:
   ```bash
   # Navigate to the lambda/docx directory
   cd ../src/lambda/docx
   
   # Get the login token for ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   
   # Build the Docker image
   docker build -t ats-custom .
   
   # Tag the image for ECR
   docker tag ats-custom:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/ats-custom:latest
   
   # Push the image to ECR
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/ats-custom:latest
   ```

3. **Update your Terraform configuration** to use the custom image:
   ```bash
   terraform apply -var="docx_image_uri=<account-id>.dkr.ecr.us-east-1.amazonaws.com/ats-custom:latest"
   ```

   Or add it to your `ats.auto.tfvars` file:
   ```hcl
   docx_image_uri = "<account-id>.dkr.ecr.us-east-1.amazonaws.com/ats-custom:latest"
   ```

>[!NOTE]
>Replace `<account-id>` with your actual AWS account ID.

### Clean up
To clean up the resources created by terraform, run:

```bash
terraform destroy
```
>[!WARNING]
>This will remove all the resources created by terraform.
