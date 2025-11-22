# CloudWatch Log Monitor

A serverless AWS Lambda function that monitors CloudWatch Logs for specific error patterns and sends notifications to Slack or SNS. It provides context by fetching preceding log events, helping developers and DevOps engineers troubleshoot issues faster.

## Credits

This project is written by Google Antigravity.

## Features

- **Real-time Monitoring**: Triggered automatically by CloudWatch Logs subscription filters.
- **Contextual Alerts**: Includes the preceding 10 log events for every matched error.
- **Flexible Filtering**: Supports regex patterns and whitelists to reduce noise.
- **Multi-Channel Routing**: Route alerts to different Slack channels or SNS topics based on log stream type (e.g., API vs. Worker).
- **External Configuration**: Load rules from Environment Variables, SSM Parameter Store, or S3.

## Project Structure

```
.
├── src/
│   ├── lambda_function.py      # Main entry point
│   ├── log_processor.py        # Pattern matching logic
│   ├── aws_client.py           # AWS SDK wrappers
│   ├── config.py               # Configuration loader (Env/SSM/S3)
│   └── notifications/          # Slack/SNS providers
├── simulate_event.py           # Local testing script
├── requirements.txt            # Python dependencies
└── specs/                      # Project requirements
```

## Usage

### Local Testing

You can simulate a CloudWatch Logs event locally using the provided script:

```bash
# Install dependencies
pip install -r requirements.txt

# Run simulation
python simulate_event.py
```

This script mocks the AWS environment and processes a sample log event, printing the output to the console.

### Deployment

This project is designed to be deployed as an AWS Lambda function.

1.  **Package the function**:
    Create a ZIP file containing the `src` directory and installed dependencies.
    ```bash
    pip install -r requirements.txt -t .
    zip -r lambda_package.zip src/ boto3/ requests/ pyyaml/ ...
    ```
    *(Note: `boto3` is usually available in the Lambda runtime, so you might not need to include it if using the standard Python runtime).*

2.  **Create Lambda Function**:
    Upload `lambda_package.zip` to AWS Lambda. Set the handler to `src.lambda_function.lambda_handler`.

3.  **Set Permissions**:
    Ensure the Lambda execution role has permissions to:
    - `logs:GetLogEvents` (to fetch context)
    - `ssm:GetParameter` (if using SSM config)
    - `s3:GetObject` (if using S3 config)
    - `sns:Publish` (if using SNS notifications)

4.  **Configure Triggers**:
    Add a CloudWatch Logs Subscription Filter to the Log Groups you want to monitor, pointing to this Lambda function.

## Configuration

The function can be configured via Environment Variables.

### Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `CONFIG_SOURCE` | Source of config: `ENV`, `SSM`, or `S3` | `ENV` |
| `STREAM_CONFIG` | JSON string of stream configuration (used if source is `ENV`) | - |
| `SSM_PARAMETER_NAME` | SSM Parameter name or path (used if source is `SSM`) | - |
| `S3_BUCKET` | S3 Bucket name (used if source is `S3`) | - |
| `S3_KEY` | S3 Object key (used if source is `S3`) | - |

### SSM Parameter Store Configuration

When using `CONFIG_SOURCE=SSM`, you can store configuration in two ways:

**1. Single Parameter**
Store the entire JSON configuration in a single parameter.
- **Parameter Name**: e.g., `/my-app/log-monitor-config`
- **Value**: The full JSON string (see format below).
- **Lambda Env**: `SSM_PARAMETER_NAME=/my-app/log-monitor-config`

**2. Parameter Path (Split Config)**
Split configuration across multiple parameters under a common path. Useful for large configurations exceeding the 4KB limit.
- **Parameter 1**: `/my-app/config/api` -> `{ "stream_types": [...] }`
- **Parameter 2**: `/my-app/config/worker` -> `{ "stream_types": [...] }`
- **Lambda Env**: `SSM_PARAMETER_NAME=/my-app/config/` (Must end with `/`)


### Stream Configuration Format

The configuration defines how to identify log streams and where to send alerts.

**Example JSON:**

```json
{
  "stream_types": [
    {
      "type": "api-server",
      "pattern": "api-.*",
      "filters": ["ERROR", "Exception"],
      "whitelist": ["HealthCheck", "ThrottlingException"],
      "slack_webhook_url": "https://hooks.slack.com/services/..."
    },
    {
      "type": "worker",
      "pattern": "worker-.*",
      "filters": ["CRITICAL"],
      "sns_topic_arn": "arn:aws:sns:us-east-1:123456789012:alerts-topic"
    }
  ]
}
```

- **type**: Friendly name for the log source.
- **pattern**: Regex to match the Log Stream name (e.g., `api-.*` matches `api-server-123`).
- **filters**: List of keywords/regex to trigger an alert.
- **whitelist**: List of keywords/regex to ignore.
- **slack_webhook_url**: Destination for Slack notifications.
- **sns_topic_arn**: Destination for SNS notifications.



