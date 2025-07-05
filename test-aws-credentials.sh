#!/bin/bash

# AWS Credentials Test Script for CloudWatch Agent
# This script helps diagnose AWS credential issues

echo "🔍 AWS Credentials Diagnostic Test"
echo "=================================="
echo ""

# Test user credentials
echo "1. Testing user AWS credentials:"
if aws sts get-caller-identity >/dev/null 2>&1; then
    echo "✅ User can access AWS services"
    aws sts get-caller-identity | jq -r '"   Account: " + .Account + ", User: " + .Arn'
else
    echo "❌ User cannot access AWS services"
    echo "   Please run: aws configure"
fi
echo ""

# Test root credentials
echo "2. Testing root user AWS credentials:"
if sudo aws sts get-caller-identity >/dev/null 2>&1; then
    echo "✅ Root user can access AWS services"
    sudo aws sts get-caller-identity | jq -r '"   Account: " + .Account + ", User: " + .Arn'
else
    echo "❌ Root user cannot access AWS services"
    echo "   This is likely the cause of CloudWatch agent credential errors"
fi
echo ""

# Check credential files
echo "3. Checking credential file locations:"

# User credentials
if [ -f "$HOME/.aws/credentials" ]; then
    echo "✅ User credentials file exists: $HOME/.aws/credentials"
else
    echo "❌ User credentials file not found: $HOME/.aws/credentials"
fi

# Root credentials
if sudo test -f "/root/.aws/credentials"; then
    echo "✅ Root credentials file exists: /root/.aws/credentials"
else
    echo "❌ Root credentials file not found: /root/.aws/credentials"
fi
echo ""

# Check environment variables
echo "4. Checking environment variables:"
if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    echo "✅ AWS_ACCESS_KEY_ID is set"
else
    echo "❌ AWS_ACCESS_KEY_ID not set"
fi

if [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "✅ AWS_SECRET_ACCESS_KEY is set"
else
    echo "❌ AWS_SECRET_ACCESS_KEY not set"
fi

if [ -n "$AWS_DEFAULT_REGION" ]; then
    echo "✅ AWS_DEFAULT_REGION is set to: $AWS_DEFAULT_REGION"
else
    echo "❌ AWS_DEFAULT_REGION not set"
fi
echo ""

# Check .env file
echo "5. Checking .env file:"
if [ -f ".env" ]; then
    echo "✅ .env file found"
    
    if grep -q "^AWS_ACCESS_KEY_ID=" .env; then
        echo "✅ AWS_ACCESS_KEY_ID found in .env"
    else
        echo "❌ AWS_ACCESS_KEY_ID not found in .env"
    fi
    
    if grep -q "^AWS_SECRET_ACCESS_KEY=" .env; then
        echo "✅ AWS_SECRET_ACCESS_KEY found in .env"
    else
        echo "❌ AWS_SECRET_ACCESS_KEY not found in .env"
    fi
    
    if grep -q "^AWS_DEFAULT_REGION=" .env; then
        REGION=$(grep "^AWS_DEFAULT_REGION=" .env | cut -d'=' -f2)
        echo "✅ AWS_DEFAULT_REGION found in .env: $REGION"
    else
        echo "❌ AWS_DEFAULT_REGION not found in .env"
    fi
else
    echo "❌ .env file not found"
fi
echo ""

# CloudWatch agent specific tests
echo "6. CloudWatch agent specific checks:"

# Check if CloudWatch agent is installed
if [ -f "/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl" ]; then
    echo "✅ CloudWatch agent is installed"
    
    # Check agent status
    if systemctl is-active --quiet cloudwatch-agent; then
        echo "✅ CloudWatch agent is running"
    else
        echo "❌ CloudWatch agent is not running"
    fi
    
    # Test agent configuration
    echo "   Testing agent configuration..."
    if sudo AWS_EC2_METADATA_DISABLED=true /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
        -m onPremise \
        -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
        -a query-config >/dev/null 2>&1; then
        echo "✅ CloudWatch agent configuration is valid"
    else
        echo "❌ CloudWatch agent configuration test failed"
    fi
else
    echo "❌ CloudWatch agent is not installed"
fi
echo ""

# Recommendations
echo "🔧 Recommendations:"
echo "=================="

if ! sudo aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❗ CRITICAL: Root user cannot access AWS services"
    echo "   Solutions:"
    echo "   1. Run: ./fix-wsl2-cloudwatch.sh (automatic fix)"
    echo "   2. Manually configure root credentials (see README.md)"
    echo ""
fi

if ! systemctl is-active --quiet cloudwatch-agent 2>/dev/null; then
    echo "❗ CloudWatch agent is not running"
    echo "   Solutions:"
    echo "   1. Run: sudo systemctl start cloudwatch-agent"
    echo "   2. Check logs: sudo journalctl -u cloudwatch-agent -f"
    echo ""
fi

echo "✅ Run this script anytime to diagnose AWS credential issues"
echo "✅ For automatic fixes, run: ./fix-wsl2-cloudwatch.sh"