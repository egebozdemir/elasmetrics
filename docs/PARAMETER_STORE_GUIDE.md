# 🔐 AWS Parameter Store Integration Guide

This guide explains how to use AWS Systems Manager Parameter Store for secure credential management in the ElasMetrics project.

---

## 📋 **Table of Contents**

1. [Overview](#overview)
2. [Setup](#setup)
3. [Configuration](#configuration)
4. [Parameter Structure](#parameter-structure)
5. [Usage](#usage)
6. [Local Development](#local-development)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 **Overview**

The Parameter Store integration allows you to:
- ✅ Store sensitive credentials securely in AWS
- ✅ Separate credentials by environment (STAGING, PRODUCTION)
- ✅ Use AWS IAM for access control
- ✅ Enable easy credential rotation
- ✅ Keep secrets out of your codebase

**Adapted from:** Anomalytics project structure

---

## 🚀 **Setup**

### **1. Install AWS Dependencies**

```bash
pip install boto3 botocore
```

Or install from requirements:

```bash
pip install -r requirements.txt
```

### **2. Configure AWS Credentials**

#### **Option A: AWS CLI Configuration** (Recommended)

```bash
aws configure
```

Enter:
- AWS Access Key ID
- AWS Secret Access Key
- Default region: `eu-west-1`
- Default output format: `json`

#### **Option B: Environment Variables**

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="eu-west-1"
```

#### **Option C: IAM Role** (For EC2/ECS/Lambda)

If running on AWS infrastructure, attach an IAM role with SSM permissions.

### **3. Verify AWS Access**

```bash
aws ssm describe-parameters --region eu-west-1
```

---

## ⚙️ **Configuration**

### **Environment Variables**

Add to your `.env`, `.env.staging`, or `.env.production`:

```bash
# Enable Parameter Store integration
USE_PARAMETER_STORE=true

# AWS region
AWS_REGION=eu-west-1

# Parameter Store prefix (namespace for your parameters)
PARAMETER_STORE_PREFIX=/ELASMETRICS

# Environment (STAGING or PRODUCTION)
ENV=STAGING

# For local development without AWS
LOCAL_DEV_MODE=false
```

### **Configuration Hierarchy**

The system uses this priority order:

1. **Parameter Store** (if `USE_PARAMETER_STORE=true`)
2. **Environment Variables** (from `.env` files)
3. **YAML Config File** (`config/config.yaml`)
4. **JSON Config** (for Airflow integration)

---

## 📁 **Parameter Structure**

### **Naming Convention**

```
/ELASMETRICS/<ENV>/<SERVICE>/<PARAMETER>
```

**Examples:**
```
/ELASMETRICS/STAGING/ELASTICSEARCH/PASSWORD
/ELASMETRICS/STAGING/MYSQL/PASSWORD
/ELASMETRICS/PRODUCTION/ELASTICSEARCH/API_KEY
```

### **Required Parameters**

#### **Elasticsearch Credentials:**

| Parameter Path | Type | Description |
|----------------|------|-------------|
| `/ELASMETRICS/<ENV>/ELASTICSEARCH/PASSWORD` | SecureString | ES password |
| `/ELASMETRICS/<ENV>/ELASTICSEARCH/USERNAME` | String | ES username (optional) |
| `/ELASMETRICS/<ENV>/ELASTICSEARCH/API_KEY` | SecureString | ES API key (optional) |

#### **MySQL Credentials:**

| Parameter Path | Type | Description |
|----------------|------|-------------|
| `/ELASMETRICS/<ENV>/MYSQL/PASSWORD` | SecureString | MySQL password |
| `/ELASMETRICS/<ENV>/MYSQL/USER` | String | MySQL username (optional) |
| `/ELASMETRICS/<ENV>/MYSQL/HOST` | String | MySQL host (optional) |

---

## 📝 **Usage**

### **Create Parameters in AWS**

#### **Using AWS CLI:**

```bash
# Elasticsearch password (encrypted)
aws ssm put-parameter \
    --name "/ELASMETRICS/STAGING/ELASTICSEARCH/PASSWORD" \
    --value "your-es-password" \
    --type "SecureString" \
    --description "Elasticsearch password for staging" \
    --region eu-west-1

# MySQL password (encrypted)
aws ssm put-parameter \
    --name "/ELASMETRICS/STAGING/MYSQL/PASSWORD" \
    --value "your-mysql-password" \
    --type "SecureString" \
    --description "MySQL password for staging" \
    --region eu-west-1

# Elasticsearch username (plain text - less sensitive)
aws ssm put-parameter \
    --name "/ELASMETRICS/STAGING/ELASTICSEARCH/USERNAME" \
    --value "elastic_user" \
    --type "String" \
    --description "Elasticsearch username for staging" \
    --region eu-west-1
```

#### **Using AWS Console:**

1. Navigate to **AWS Systems Manager** → **Parameter Store**
2. Click **Create parameter**
3. Enter parameter details:
   - **Name:** `/ELASMETRICS/STAGING/ELASTICSEARCH/PASSWORD`
   - **Type:** `SecureString`
   - **Value:** Your password
4. Click **Create parameter**

#### **Using Python Script:**

```python
from src.services.parameter_store_service import ParameterStoreService

# Create a parameter
ParameterStoreService.put_parameter(
    param_name="/ELASMETRICS/STAGING/ELASTICSEARCH/PASSWORD",
    param_value="your-password",
    param_type="SecureString",
    description="Elasticsearch password for staging"
)
```

### **Retrieve Parameters**

#### **Automatic (via ConfigLoader):**

```python
from src.utils import ConfigLoader

# ConfigLoader automatically fetches from Parameter Store if USE_PARAMETER_STORE=true
config_loader = ConfigLoader()
config = config_loader.load_config()

# Credentials are loaded from Parameter Store
es_config = config['elasticsearch']
mysql_config = config['mysql']
```

#### **Manual (direct access):**

```python
from src.services.parameter_store_service import ParameterStoreService

# Get a single parameter
es_password = ParameterStoreService.get_parameter(
    "/ELASMETRICS/STAGING/ELASTICSEARCH/PASSWORD"
)

# Get with default value
mysql_host = ParameterStoreService.get_parameter(
    "/ELASMETRICS/STAGING/MYSQL/HOST",
    default="localhost"
)

# Get multiple parameters by path
db_config = ParameterStoreService.get_parameters_by_path(
    "/ELASMETRICS/STAGING/MYSQL/",
    recursive=True
)
# Returns: {'PASSWORD': '...', 'USER': '...', 'HOST': '...'}
```

---

## 🏠 **Local Development**

### **Option 1: Use Local Mode** (Recommended)

Set in your `.env`:

```bash
LOCAL_DEV_MODE=true
USE_PARAMETER_STORE=false

# Use local credentials
ES_PASSWORD=local-es-password
MYSQL_PASSWORD=local-mysql-password
```

### **Option 2: Use LocalStack** (AWS Emulation)

```bash
# Install localstack
pip install localstack

# Start localstack
localstack start

# Configure to use localstack
export AWS_ENDPOINT_URL=http://localhost:4566
```

### **Option 3: Use AWS with Test Parameters**

Create test parameters in your AWS account:

```bash
aws ssm put-parameter \
    --name "/ELASMETRICS/DEV/ELASTICSEARCH/PASSWORD" \
    --value "dev-password" \
    --type "SecureString"
```

Then set:

```bash
ENV=DEV
USE_PARAMETER_STORE=true
```

---

## 🚀 **Production Deployment**

### **1. Create Production Parameters**

```bash
# Elasticsearch
aws ssm put-parameter \
    --name "/ELASMETRICS/PRODUCTION/ELASTICSEARCH/PASSWORD" \
    --value "STRONG_PRODUCTION_PASSWORD" \
    --type "SecureString" \
    --region eu-west-1

aws ssm put-parameter \
    --name "/ELASMETRICS/PRODUCTION/ELASTICSEARCH/USERNAME" \
    --value "elastic_prod" \
    --type "String" \
    --region eu-west-1

# MySQL
aws ssm put-parameter \
    --name "/ELASMETRICS/PRODUCTION/MYSQL/PASSWORD" \
    --value "STRONG_MYSQL_PASSWORD" \
    --type "SecureString" \
    --region eu-west-1

aws ssm put-parameter \
    --name "/ELASMETRICS/PRODUCTION/MYSQL/USER" \
    --value "metrics_user" \
    --type "String" \
    --region eu-west-1
```

### **2. Configure IAM Role**

Create an IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": [
        "arn:aws:ssm:eu-west-1:*:parameter/ELASMETRICS/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt"
      ],
      "Resource": [
        "arn:aws:kms:eu-west-1:*:key/*"
      ]
    }
  ]
}
```

Attach this policy to your EC2 instance role, ECS task role, or Lambda execution role.

### **3. Set Environment Variables**

In your production environment:

```bash
ENV=PRODUCTION
USE_PARAMETER_STORE=true
AWS_REGION=eu-west-1
PARAMETER_STORE_PREFIX=/ELASMETRICS
LOCAL_DEV_MODE=false
```

### **4. Test Connection**

```bash
python main.py health-check
```

---

## 🔧 **Troubleshooting**

### **Error: "AWS credentials not found"**

**Solution:**
```bash
# Set LOCAL_DEV_MODE=true for local development
echo "LOCAL_DEV_MODE=true" >> .env

# OR configure AWS credentials
aws configure
```

### **Error: "Parameter not found"**

**Solution:**
```bash
# List all parameters
aws ssm describe-parameters --region eu-west-1

# Check specific parameter
aws ssm get-parameter \
    --name "/ELASMETRICS/STAGING/ELASTICSEARCH/PASSWORD" \
    --with-decryption \
    --region eu-west-1

# Verify parameter path matches ENV
echo $ENV  # Should match the parameter path
```

### **Error: "Access Denied"**

**Solution:**
```bash
# Check IAM permissions
aws iam get-user
aws iam list-attached-user-policies --user-name YOUR_USERNAME

# Verify role has SSM permissions
aws ssm describe-parameters --region eu-west-1
```

### **Parameters Not Loading**

**Check:**

1. `USE_PARAMETER_STORE=true` is set
2. `LOCAL_DEV_MODE=false` (not in dev mode)
3. `ENV` variable matches parameter path
4. AWS credentials are configured
5. Parameter names are correct (case-sensitive)

**Debug:**

```python
import os
import logging

logging.basicConfig(level=logging.DEBUG)

from src.utils import ConfigLoader

# Check settings
print(f"USE_PARAMETER_STORE: {os.getenv('USE_PARAMETER_STORE')}")
print(f"LOCAL_DEV_MODE: {os.getenv('LOCAL_DEV_MODE')}")
print(f"ENV: {os.getenv('ENV')}")
print(f"AWS_REGION: {os.getenv('AWS_REGION')}")

# Load config (will show debug logs)
config_loader = ConfigLoader()
config = config_loader.load_config()
```

---

## 📚 **Examples**

### **Example 1: Basic Setup (Staging)**

```bash
# 1. Create parameters
aws ssm put-parameter \
    --name "/ELASMETRICS/STAGING/ELASTICSEARCH/PASSWORD" \
    --value "staging-es-pass" \
    --type "SecureString"

aws ssm put-parameter \
    --name "/ELASMETRICS/STAGING/MYSQL/PASSWORD" \
    --value "staging-mysql-pass" \
    --type "SecureString"

# 2. Configure environment
cat > .env.staging << EOF
ENV=STAGING
USE_PARAMETER_STORE=true
AWS_REGION=eu-west-1
PARAMETER_STORE_PREFIX=/ELASMETRICS
LOCAL_DEV_MODE=false
EOF

# 3. Run application
export ENV=STAGING
python main.py collect
```

### **Example 2: Multi-Environment Setup**

```bash
# Create staging parameters
for env in STAGING PRODUCTION; do
  aws ssm put-parameter \
      --name "/ELASMETRICS/$env/ELASTICSEARCH/PASSWORD" \
      --value "$env-es-password" \
      --type "SecureString" \
      --region eu-west-1
  
  aws ssm put-parameter \
      --name "/ELASMETRICS/$env/MYSQL/PASSWORD" \
      --value "$env-mysql-password" \
      --type "SecureString" \
      --region eu-west-1
done
```

### **Example 3: Programmatic Access**

```python
from src.services.parameter_store_service import ParameterStoreService

# Get single parameter
password = ParameterStoreService.get_parameter(
    "/ELASMETRICS/STAGING/MYSQL/PASSWORD"
)

# Get all MySQL config
mysql_params = ParameterStoreService.get_parameters_by_path(
    "/ELASMETRICS/STAGING/MYSQL/",
    recursive=True
)

print(mysql_params)
# Output: {'PASSWORD': '...', 'USER': '...', 'HOST': '...'}

# Store new parameter
ParameterStoreService.put_parameter(
    param_name="/ELASMETRICS/STAGING/NEW_PARAM",
    param_value="new-value",
    param_type="SecureString"
)
```

---

## 🎯 **Best Practices**

1. ✅ **Use SecureString** for all sensitive data (passwords, API keys)
2. ✅ **Use descriptive names** with clear hierarchy
3. ✅ **Separate by environment** (STAGING, PRODUCTION)
4. ✅ **Use IAM roles** instead of access keys when possible
5. ✅ **Enable CloudWatch Logs** for parameter access auditing
6. ✅ **Rotate credentials regularly**
7. ✅ **Use LOCAL_DEV_MODE** for local development
8. ✅ **Document your parameter structure**
9. ✅ **Set default values** when appropriate
10. ✅ **Test in staging** before production

---

## 📖 **Additional Resources**

- [AWS Parameter Store Documentation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [Boto3 SSM Client Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm.html)
- [IAM Policies for Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-access.html)
- [Anomalytics Project Reference](/Users/ege.bozdemir/PycharmProjects/anomalytics)

---

**Quick Command Reference:**

```bash
# List all parameters
aws ssm describe-parameters --region eu-west-1

# Get parameter value
aws ssm get-parameter --name "/ELASMETRICS/STAGING/MYSQL/PASSWORD" --with-decryption --region eu-west-1

# Delete parameter
aws ssm delete-parameter --name "/ELASMETRICS/STAGING/OLD_PARAM" --region eu-west-1

# Get parameters by path
aws ssm get-parameters-by-path --path "/ELASMETRICS/STAGING/" --recursive --with-decryption --region eu-west-1
```

---

🔐 **Your credentials are now secure and manageable!**

