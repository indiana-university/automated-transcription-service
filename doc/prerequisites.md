# Prerequisites for AWS Deployment

You can deploy the application either from your own workstation or from CloudShell in your AWS account. Both methods have the same requirements:
- Docker
- Terraform
- AWS CLI

## CloudShell
CloudShell already includes Docker and the CLI, so you only need to install Terraform. Follow these steps:
1. Open CloudShell in your AWS account.
2. Run the following commands to install Terraform:

```bash
sudo yum install -y yum-utils shadow-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
sudo yum -y install terraform
```

## Workstation
If you are deploying from your own workstation, you need to install Docker, Terraform, and the AWS CLI. Follow the instructions for your operating system:
- https://docs.docker.com/desktop/
- https://developer.hashicorp.com/terraform/install
- https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

## Installation
Once you have installed the prerequisites, you can proceed with the installation of the application. Refer to the [installation guide](../aws/README.md) for further instructions.