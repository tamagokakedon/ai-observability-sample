# WSL2 CloudWatch Agent Fix

## Problem Resolved
Fixed the CloudWatch agent metadata service error that occurs when running in WSL2 environment:
```
E! Please check if you can access the metadata service. For example, on linux, run 'wget -q -O - http://169.254.169.254/latest/meta-data/instance-id && echo'
```

## Root Cause
WSL2 doesn't have access to AWS EC2 metadata service (169.254.169.254) because it's not running on actual EC2 infrastructure. The CloudWatch agent was configured in `ec2` mode and trying to access instance metadata that doesn't exist in WSL2.

## Solution Implemented

### 1. Automatic WSL2 Detection
The installation script now automatically detects WSL2 and configures accordingly:

```bash
# WSL2-specific configuration
if grep -qi "microsoft" /proc/version; then
    echo "🐧 WSL2 detected - configuring for on-premise mode"
    export CW_CONFIG_MODE="onPremise"
    export AWS_EC2_METADATA_DISABLED="true"
else
    export CW_CONFIG_MODE="ec2"
fi
```

### 2. Configuration Changes

**Before (Problematic):**
- Mode: `ec2`
- Log stream names: `{instance_id}/application.log`
- Metadata service: Required

**After (WSL2 Compatible):**
- Mode: `onPremise` 
- Log stream names: `{hostname}/application.log`
- Metadata service: Disabled with `AWS_EC2_METADATA_DISABLED=true`

### 3. Updated Files

#### `install-cloudwatch-agent.sh`
- ✅ Auto-detects WSL2 environment
- ✅ Sets appropriate configuration mode (`onPremise` for WSL2, `ec2` for real EC2)
- ✅ Disables metadata service for WSL2
- ✅ Updates all CloudWatch agent commands with proper environment variables

#### `cloudwatch-agent-config.json`
- ✅ Changed `{instance_id}` to `{hostname}` in log stream names
- ✅ Compatible with onPremise mode

#### `fix-wsl2-cloudwatch.sh` (New)
- ✅ Quick fix script for existing installations
- ✅ Reconfigures running CloudWatch agent for WSL2
- ✅ Updates systemd service configuration

## Usage Instructions

### For New Installations
Just run the updated installation script:
```bash
./install-cloudwatch-agent.sh
```
The script will automatically detect WSL2 and configure appropriately.

### For Existing Installations with Metadata Error
Run the fix script:
```bash
./fix-wsl2-cloudwatch.sh
```

### Manual Fix (if needed)
```bash
# Stop the agent
sudo systemctl stop cloudwatch-agent

# Reconfigure for WSL2
export AWS_EC2_METADATA_DISABLED=true
sudo AWS_EC2_METADATA_DISABLED=true /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m onPremise \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Restart the agent
sudo systemctl start cloudwatch-agent
```

## Verification

### Check Agent Status
```bash
sudo systemctl status cloudwatch-agent
```

### Test Configuration
```bash
sudo AWS_EC2_METADATA_DISABLED=true /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -m onPremise \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -a query-config
```

### Expected Output
- No metadata service errors
- Agent starts successfully
- Logs appear in CloudWatch with hostname-based stream names

## Benefits

1. **WSL2 Compatibility**: Works seamlessly in WSL2 environment
2. **Automatic Detection**: No manual configuration needed
3. **Backward Compatibility**: Still works on real EC2 instances
4. **Easy Fix**: Existing installations can be quickly updated
5. **Proper Log Streams**: Uses hostname instead of non-existent instance ID

## Architecture

```
WSL2 Environment:
Application → Structured Log Files → CloudWatch Agent (onPremise mode) → CloudWatch Logs

EC2 Environment:
Application → Structured Log Files → CloudWatch Agent (ec2 mode) → CloudWatch Logs
```

## Files Created/Modified

- ✅ `install-cloudwatch-agent.sh` - Updated with WSL2 auto-detection
- ✅ `cloudwatch-agent-config.json` - Updated log stream naming
- ✅ `fix-wsl2-cloudwatch.sh` - New quick fix script
- ✅ `README.md` - Added WSL2 troubleshooting section
- ✅ `test_task07_observability.py` - Tests now include WSL2 fix script

This fix ensures the CloudWatch agent works reliably in WSL2 development environments while maintaining compatibility with production EC2 deployments.