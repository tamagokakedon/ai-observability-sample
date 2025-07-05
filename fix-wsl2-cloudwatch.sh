#!/bin/bash

# Quick fix script for CloudWatch agent metadata service error in WSL2
# This script fixes the "Please check if you can access the metadata service" error

set -e

echo "🔧 Fixing CloudWatch Agent for WSL2"
echo "==================================="

# Check if running on WSL
if ! grep -qi "microsoft" /proc/version; then
    echo "⚠️  This script is designed for WSL2. Detected non-WSL environment."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if CloudWatch agent is installed
if [ ! -f "/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl" ]; then
    echo "❌ CloudWatch agent not found. Please run ./install-cloudwatch-agent.sh first"
    exit 1
fi

echo "📋 Stopping existing CloudWatch agent..."
sudo systemctl stop cloudwatch-agent || sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent -a stop || true

echo "🔐 Checking AWS credentials for CloudWatch agent..."

# Check and configure credentials for CloudWatch agent (root user)
AWS_ACCESS_KEY=""
AWS_SECRET_KEY=""
AWS_REGION=""

# Check if .env file exists and source it
if [ -f ".env" ]; then
    echo "📄 Found .env file, extracting credentials..."
    AWS_ACCESS_KEY=$(grep "^AWS_ACCESS_KEY_ID=" .env | cut -d'=' -f2)
    AWS_SECRET_KEY=$(grep "^AWS_SECRET_ACCESS_KEY=" .env | cut -d'=' -f2)
    AWS_REGION=$(grep "^AWS_DEFAULT_REGION=" .env | cut -d'=' -f2)
fi

# Fallback to environment variables
if [ -z "$AWS_ACCESS_KEY" ]; then
    AWS_ACCESS_KEY="$AWS_ACCESS_KEY_ID"
fi
if [ -z "$AWS_SECRET_KEY" ]; then
    AWS_SECRET_KEY="$AWS_SECRET_ACCESS_KEY"
fi
if [ -z "$AWS_REGION" ]; then
    AWS_REGION="$AWS_DEFAULT_REGION"
fi

# Set defaults if still empty
if [ -z "$AWS_REGION" ]; then
    AWS_REGION="us-east-1"
fi

if [ -n "$AWS_ACCESS_KEY" ] && [ -n "$AWS_SECRET_KEY" ]; then
    echo "🔑 Configuring AWS credentials for root user..."
    
    # Create AWS credentials directory for root
    sudo mkdir -p /root/.aws
    
    # Create credentials file for root user
    sudo tee /root/.aws/credentials > /dev/null <<EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY
aws_secret_access_key = $AWS_SECRET_KEY
EOF

    # Create config file for root user
    sudo tee /root/.aws/config > /dev/null <<EOF
[default]
region = $AWS_REGION
output = json
EOF

    # Set proper permissions
    sudo chmod 600 /root/.aws/credentials
    sudo chmod 600 /root/.aws/config
    
    echo "✅ AWS credentials configured for CloudWatch agent"
else
    echo "⚠️  Could not find AWS credentials in .env file or environment variables"
    echo "    CloudWatch agent will try to use IAM role or other credential sources"
fi

echo "🐧 Configuring for WSL2 environment..."

# Set environment variables
export AWS_EC2_METADATA_DISABLED="true"
export CW_CONFIG_MODE="onPremise"

echo "⚙️  Reconfiguring CloudWatch agent for WSL2..."
sudo AWS_EC2_METADATA_DISABLED=true /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m onPremise \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

echo "🔄 Updating systemd service..."
sudo tee /etc/systemd/system/cloudwatch-agent.service > /dev/null <<EOF
[Unit]
Description=Amazon CloudWatch Agent
After=network.target

[Service]
Type=simple
Environment=AWS_EC2_METADATA_DISABLED=true
ExecStart=/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent -c /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -a start -m onPremise
ExecStop=/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent -a stop
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Reloading systemd and starting agent..."
sudo systemctl daemon-reload
sudo systemctl enable cloudwatch-agent.service
sudo systemctl start cloudwatch-agent.service

echo "📊 Checking CloudWatch agent status..."
if sudo systemctl status cloudwatch-agent.service --no-pager -l; then
    echo "✅ CloudWatch agent is running successfully in WSL2"
else
    echo "❌ CloudWatch agent failed to start. Trying manual start..."
    sudo AWS_EC2_METADATA_DISABLED=true /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent \
        -c /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
        -a start \
        -m onPremise
fi

echo ""
echo "🎉 WSL2 CloudWatch Agent Fix Complete!"
echo "======================================"
echo ""
echo "✅ The agent is now configured for WSL2 environment"
echo "✅ EC2 metadata service check disabled"
echo "✅ Using onPremise mode instead of ec2 mode"
echo ""
echo "🔧 Management Commands:"
echo "   • Check status: sudo systemctl status cloudwatch-agent"
echo "   • Restart: sudo systemctl restart cloudwatch-agent"
echo "   • View logs: sudo journalctl -u cloudwatch-agent -f"
echo ""