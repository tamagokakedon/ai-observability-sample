#!/bin/bash

# CloudWatch Agent Installation Script for WSL2/Ubuntu
# This script installs and configures the CloudWatch agent for the AI Recipe Analyzer project

set -e

echo "🚀 Installing CloudWatch Agent for AI Recipe Analyzer on WSL2"
echo "=============================================================="

# Check if running on WSL
if ! grep -qi "microsoft" /proc/version; then
    echo "⚠️  This script is designed for WSL2. Proceed with caution on other systems."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for AWS credentials
echo "📋 Checking AWS credentials..."
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi
echo "✅ AWS credentials found for user"

# Check and configure credentials for CloudWatch agent (root user)
echo "🔐 Configuring AWS credentials for CloudWatch agent..."

# Try to get credentials from various sources
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
    
    # Test credentials as root
    if sudo aws sts get-caller-identity >/dev/null 2>&1; then
        echo "✅ Root user can access AWS services"
    else
        echo "⚠️  Root user AWS access test failed, but continuing..."
    fi
else
    echo "⚠️  Could not find AWS credentials in .env file or environment variables"
    echo "    CloudWatch agent will try to use IAM role or other credential sources"
fi

# Check required environment variables
if [ -z "$AWS_DEFAULT_REGION" ]; then
    export AWS_DEFAULT_REGION="us-east-1"
    echo "📍 Using default region: $AWS_DEFAULT_REGION"
fi

# WSL2-specific configuration
if grep -qi "microsoft" /proc/version; then
    echo "🐧 WSL2 detected - configuring for on-premise mode"
    export CW_CONFIG_MODE="onPremise"
    
    # Disable EC2 metadata service check for WSL2
    export AWS_EC2_METADATA_DISABLED="true"
    echo "📋 Disabled EC2 metadata service for WSL2 compatibility"
else
    export CW_CONFIG_MODE="ec2"
fi

# Create log directory
echo "📁 Creating log directories..."
sudo mkdir -p /var/log/ai-recipe-analyzer
sudo chown $USER:$USER /var/log/ai-recipe-analyzer
echo "✅ Log directory created: /var/log/ai-recipe-analyzer"

# Download and install CloudWatch agent
echo "⬇️  Downloading CloudWatch agent..."
AGENT_URL="https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb"
wget -q $AGENT_URL -O /tmp/amazon-cloudwatch-agent.deb

echo "📦 Installing CloudWatch agent..."
sudo dpkg -i /tmp/amazon-cloudwatch-agent.deb
rm /tmp/amazon-cloudwatch-agent.deb

# Copy configuration file
echo "⚙️  Configuring CloudWatch agent..."
sudo cp cloudwatch-agent-config.json /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Configure the agent with appropriate mode
echo "🔧 Setting up CloudWatch agent configuration in $CW_CONFIG_MODE mode..."
sudo AWS_EC2_METADATA_DISABLED=$AWS_EC2_METADATA_DISABLED /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m $CW_CONFIG_MODE \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Create systemd service for WSL
echo "🎯 Creating systemd service for WSL..."
sudo tee /etc/systemd/system/cloudwatch-agent.service > /dev/null <<EOF
[Unit]
Description=Amazon CloudWatch Agent
After=network.target

[Service]
Type=simple
Environment=AWS_EC2_METADATA_DISABLED=$AWS_EC2_METADATA_DISABLED
ExecStart=/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent -c /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -a start -m $CW_CONFIG_MODE
ExecStop=/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent -a stop
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service (if systemd is available)
if command -v systemctl >/dev/null 2>&1; then
    echo "🔄 Enabling CloudWatch agent service..."
    sudo systemctl daemon-reload
    sudo systemctl enable cloudwatch-agent.service
    sudo systemctl start cloudwatch-agent.service
    
    echo "📊 Checking CloudWatch agent status..."
    sudo systemctl status cloudwatch-agent.service --no-pager -l
else
    echo "⚠️  systemd not available. Starting CloudWatch agent manually..."
    sudo AWS_EC2_METADATA_DISABLED=$AWS_EC2_METADATA_DISABLED /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent \
        -c /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
        -a start \
        -m $CW_CONFIG_MODE
fi

# Create log rotation configuration
echo "🔄 Setting up log rotation..."
sudo tee /etc/logrotate.d/ai-recipe-analyzer > /dev/null <<EOF
/var/log/ai-recipe-analyzer/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        # Signal the application to reopen log files if needed
        pkill -USR1 -f "streamlit" || true
    endscript
}
EOF

# Test the configuration
echo "🧪 Testing CloudWatch agent configuration..."
if sudo AWS_EC2_METADATA_DISABLED=$AWS_EC2_METADATA_DISABLED /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -m $CW_CONFIG_MODE \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -a query-config; then
    echo "✅ CloudWatch agent configuration is valid"
else
    echo "❌ CloudWatch agent configuration test failed"
    exit 1
fi

# Create a test log entry
echo "📝 Creating test log entry..."
echo "$(date -Iseconds) [INFO] CloudWatch agent installation completed successfully" >> /var/log/ai-recipe-analyzer/test.log

echo ""
echo "🎉 CloudWatch Agent Installation Complete!"
echo "=============================================="
echo ""
echo "📊 Dashboard: Check the CloudWatch console for metrics and logs"
echo "📍 Region: $AWS_DEFAULT_REGION"
echo "📁 Log Groups:"
echo "   • /aws/ai-recipe-analyzer/application"
echo "   • /aws/ai-recipe-analyzer/debug"
echo "   • /aws/ai-recipe-analyzer/ai-recipe-analyzer (from OpenTelemetry)"
echo ""
echo "🔧 Management Commands:"
echo "   • Check status: sudo systemctl status cloudwatch-agent"
echo "   • Restart: sudo systemctl restart cloudwatch-agent"
echo "   • View logs: sudo journalctl -u cloudwatch-agent -f"
echo ""
echo "📖 Next Steps:"
echo "   1. Run your AI Recipe Analyzer application"
echo "   2. Check CloudWatch console for incoming metrics and logs"
echo "   3. Import the CloudWatch dashboard using cloudwatch-dashboard.json"
echo ""

# WSL-specific instructions
if grep -qi "microsoft" /proc/version; then
    echo "🐧 WSL-Specific Notes:"
    echo "   • The CloudWatch agent will start automatically with the system"
    echo "   • If WSL restarts, you may need to manually restart the agent:"
    echo "     sudo systemctl start cloudwatch-agent"
    echo "   • Consider adding the start command to your shell profile for auto-start"
    echo ""
fi