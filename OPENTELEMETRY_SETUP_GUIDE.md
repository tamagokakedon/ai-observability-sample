# OpenTelemetry CloudWatch Setup Guide

## Issue Resolution: `opentelemetry-exporter-cloudwatch` Package Not Found

### Problem
When attempting to install the original requirements.txt, users encounter this error:
```
ERROR: Could not find a version that satisfies the requirement opentelemetry-exporter-cloudwatch>=1.15.0 (from versions: none)
ERROR: No matching distribution found for opentelemetry-exporter-cloudwatch>=1.15.0
```

### Root Cause
**As of 2024, there is no standalone `opentelemetry-exporter-cloudwatch` PyPI package.** AWS has adopted a different architecture for OpenTelemetry integration with CloudWatch.

### Solution Implemented

#### 1. Updated Dependencies
The `requirements.txt` has been updated to use the correct packages:

**Removed:**
- `opentelemetry-exporter-cloudwatch>=1.15.0` (does not exist)

**Added:**
- `aws-opentelemetry-distro>=0.4b0` - AWS distribution of OpenTelemetry
- `opentelemetry-sdk-extension-aws>=2.0.1` - AWS SDK extensions for X-Ray ID generation

#### 2. Architecture Changes
The application now follows AWS's recommended approach for 2024:

**Previous (Non-functional) Approach:**
```
Application → Direct CloudWatch Exporters → CloudWatch
```

**New (AWS-Recommended) Approach:**
```
Application → OTLP Exporter → ADOT Collector → CloudWatch
```

Or alternatively:
```
Application → Structured Log Files → CloudWatch Agent → CloudWatch
```

#### 3. Code Changes Made

1. **Removed non-existent imports:**
   ```python
   # Removed these (don't exist):
   from opentelemetry.exporter.cloudwatch.logs import CloudWatchLogsExporter
   from opentelemetry.exporter.cloudwatch.trace import CloudWatchSpanExporter
   from opentelemetry.exporter.cloudwatch.metrics import CloudWatchMetricsExporter
   ```

2. **Added correct AWS extensions:**
   ```python
   # Added these (actual packages):
   from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator
   from opentelemetry.sdk.extension.aws.resource import AwsEcsResourceDetector, AwsEc2ResourceDetector
   ```

3. **Updated exporter configuration:**
   - Uses OTLP exporter targeting ADOT Collector endpoint
   - Maintains X-Ray propagator for distributed tracing
   - Implements file-based structured logging for CloudWatch Agent

### Installation Instructions

#### Step 1: Install Correct Dependencies
```bash
# Install pip if not available
sudo apt update && sudo apt install python3-pip -y

# Install the corrected requirements
pip3 install -r requirements.txt
```

#### Step 2: Verify Installation
```bash
# Test OpenTelemetry installation
python3 -c "from opentelemetry import trace; print('OpenTelemetry installed successfully')"

# Run comprehensive tests
python3 test_task07_observability.py
```

#### Step 3: Production Setup (Optional)
For full CloudWatch integration in production:

1. **Install ADOT Collector:**
   ```bash
   wget https://github.com/aws-observability/aws-otel-collector/releases/latest/download/aws-otel-collector.deb
   sudo dpkg -i aws-otel-collector.deb
   sudo systemctl enable aws-otel-collector
   sudo systemctl start aws-otel-collector
   ```

2. **Install CloudWatch Agent:**
   ```bash
   ./install-cloudwatch-agent.sh
   ```

### Expected Test Results
With correct installation:
- ✅ **OpenTelemetry Imports**: Should pass
- ✅ **X-Ray Propagator**: Should pass (with packages installed)
- ✅ **Enhanced Metrics**: Should pass (with packages installed)
- ✅ **Correlation Context**: Should pass
- ✅ **Tracing Decorators**: Should pass
- ✅ **Dashboard Configuration**: Should pass
- ✅ **CloudWatch Agent Files**: Should pass

### Graceful Degradation
The application is designed with graceful degradation:
- Works without OpenTelemetry packages (basic functionality)
- Provides enhanced observability when packages are installed
- Maintains correlation context and structured logging regardless

### AWS Official Documentation
This implementation follows AWS best practices as documented in:
- [AWS Distro for OpenTelemetry](https://aws-otel.github.io/docs/)
- [Using CloudWatch Metrics with AWS Distro for OpenTelemetry](https://aws-otel.github.io/docs/getting-started/cloudwatch-metrics/)

### Troubleshooting
If you still encounter issues:

1. Check Python version: `python3 --version` (requires 3.8+)
2. Verify pip installation: `pip3 --version`
3. Check AWS credentials: `aws sts get-caller-identity`
4. View detailed logs by setting `DEBUG=true` in your `.env` file