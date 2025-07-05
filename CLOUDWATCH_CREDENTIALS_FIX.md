# CloudWatch Agent Credentials Fix

## Problem Resolved
Fixed the CloudWatch agent credentials error that occurs when the agent runs as root but cannot access AWS credentials:
```
E! Please make sure the credentials and region set correctly on your hosts.
```

## Root Cause
The CloudWatch agent runs as the root user, but AWS credentials are typically configured for the regular user account. Even though `aws sts get-caller-identity` works for your user, the root user cannot access the same credentials.

## Solution Implemented

### 1. Automatic Credential Configuration
Both installation scripts now automatically configure AWS credentials for the root user:

**`install-cloudwatch-agent.sh`** and **`fix-wsl2-cloudwatch.sh`** now:
- ✅ Read credentials from `.env` file
- ✅ Extract `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION`
- ✅ Create `/root/.aws/credentials` and `/root/.aws/config`
- ✅ Set proper file permissions (600)
- ✅ Test root user AWS access

### 2. Credential Sources (Priority Order)
The scripts check for credentials in this order:
1. `.env` file (recommended for development)
2. Environment variables
3. Default region fallback to `us-east-1`

### 3. Diagnostic Script
Created `test-aws-credentials.sh` to help diagnose credential issues:
- ✅ Tests both user and root AWS access
- ✅ Checks credential file locations
- ✅ Verifies environment variables
- ✅ Analyzes `.env` file
- ✅ Tests CloudWatch agent configuration
- ✅ Provides specific recommendations

## Files Updated

### `install-cloudwatch-agent.sh`
Added comprehensive credential configuration:
```bash
# Check and configure credentials for CloudWatch agent (root user)
echo "🔐 Configuring AWS credentials for CloudWatch agent..."

# Extract credentials from .env file
if [ -f ".env" ]; then
    AWS_ACCESS_KEY=$(grep "^AWS_ACCESS_KEY_ID=" .env | cut -d'=' -f2)
    AWS_SECRET_KEY=$(grep "^AWS_SECRET_ACCESS_KEY=" .env | cut -d'=' -f2)
    AWS_REGION=$(grep "^AWS_DEFAULT_REGION=" .env | cut -d'=' -f2)
fi

# Create root AWS configuration
sudo mkdir -p /root/.aws
sudo tee /root/.aws/credentials > /dev/null <<EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY
aws_secret_access_key = $AWS_SECRET_KEY
EOF
```

### `fix-wsl2-cloudwatch.sh`
Updated to include the same credential configuration logic.

### `test-aws-credentials.sh` (New)
Comprehensive diagnostic script that checks:
- User AWS access
- Root AWS access
- Credential file locations
- Environment variables
- .env file configuration
- CloudWatch agent status

## Usage Instructions

### For New Installations
```bash
./install-cloudwatch-agent.sh
```
The script automatically configures credentials for the root user.

### For Existing Installations with Credential Errors
```bash
# Option 1: Use the fix script (recommended)
./fix-wsl2-cloudwatch.sh

# Option 2: Use the diagnostic script first
./test-aws-credentials.sh
```

### Manual Fix (if needed)
```bash
# Configure credentials for root user
sudo mkdir -p /root/.aws

# Copy your credentials from .env file
AWS_ACCESS_KEY=$(grep "^AWS_ACCESS_KEY_ID=" .env | cut -d'=' -f2)
AWS_SECRET_KEY=$(grep "^AWS_SECRET_ACCESS_KEY=" .env | cut -d'=' -f2)
AWS_REGION=$(grep "^AWS_DEFAULT_REGION=" .env | cut -d'=' -f2)

sudo tee /root/.aws/credentials > /dev/null <<EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY
aws_secret_access_key = $AWS_SECRET_KEY
EOF

sudo tee /root/.aws/config > /dev/null <<EOF
[default]
region = $AWS_REGION
output = json
EOF

# Set proper permissions
sudo chmod 600 /root/.aws/credentials
sudo chmod 600 /root/.aws/config

# Test root access
sudo aws sts get-caller-identity
```

## Verification

### Check Root User AWS Access
```bash
sudo aws sts get-caller-identity
```
Should return your AWS account information.

### Test CloudWatch Agent
```bash
sudo systemctl status cloudwatch-agent
```
Should show the agent running without credential errors.

### Run Diagnostic Script
```bash
./test-aws-credentials.sh
```
Should show all green checkmarks for credential access.

## Security Considerations

### Development Environment (Current Setup)
- ✅ Uses access keys from `.env` file
- ✅ Files have proper permissions (600)
- ✅ Works in WSL2 and local development

### Production Environment (Recommended)
For production deployments, use IAM roles instead of access keys:
```bash
# Attach CloudWatchAgentServerPolicy to your EC2 instance role
# No credential files needed when using IAM roles
```

## Architecture

```
Development (WSL2):
User: ~/.aws/credentials (your credentials)
Root: /root/.aws/credentials (copied from .env)
CloudWatch Agent (root) → Uses /root/.aws/credentials → CloudWatch

Production (EC2):
EC2 Instance Role → IAM Policy (CloudWatchAgentServerPolicy)
CloudWatch Agent (root) → Uses instance role → CloudWatch
```

## Test Results
With the fix applied, the diagnostic script shows:
- ✅ User can access AWS services
- ✅ Root user can access AWS services  
- ✅ CloudWatch agent configuration is valid
- ✅ CloudWatch agent is running

This resolves the "Please make sure the credentials and region set correctly" error permanently.