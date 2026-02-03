# CloudWatch Log Monitor

A serverless AWS Lambda function that monitors CloudWatch Logs for specific error patterns and sends notifications to Slack or SNS. It provides context by fetching preceding log events, helping developers and DevOps engineers troubleshoot issues faster.

## Credits

This project is written by Google Antigravity(Using Gemini 3 Pro and Claude Sonnet 4.5).

## Features

- **Real-time Monitoring**: Triggered automatically by CloudWatch Logs subscription filters.
- **Contextual Alerts**: Includes the preceding 10 log events for every matched error.
- **Flexible Filtering**: Supports regex patterns and whitelists to reduce noise.
- **Multi-Channel Routing**: Route alerts to different Slack channels or SNS topics based on log stream type (e.g., API vs. Worker).
- **External Configuration**: Load rules from Environment Variables, SSM Parameter Store, or S3.
- **Infrastructure as Code**: Deployed using AWS SAM.
- **Type Safe**: Fully typed Python codebase.

## Project Structure

```
.
├── src/
│   ├── lambda_function.py      # Main entry point
│   ├── log_processor.py        # Pattern matching logic
│   ├── aws_client.py           # AWS SDK wrappers
│   ├── config.py               # Configuration loader (Env/SSM/S3)
│   └── notifications/          # Slack/SNS providers
├── tests/                      # Unit tests
├── .github/workflows/          # CI/CD pipelines
├── template.yaml               # AWS SAM Infrastructure definition
├── simulate_event.py           # Local testing script
├── requirements.txt            # Python dependencies
└── requirements.lock           # Pinned dependencies
```

## Usage

### Prerequisites

- Python 3.12+
- AWS CLI installed and configured
- AWS SAM CLI installed

### Local Development

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run Tests**:
    ```bash
    pytest tests/
    ```

3.  **Simulate Event**:
    You can simulate a CloudWatch Logs event locally using the provided script:
    ```bash
    python simulate_event.py
    ```

### Deployment

This project is deployed using the AWS Serverless Application Model (SAM).

1.  **Build the application**:
    ```bash
    sam build
    ```

2.  **Deploy**:
    ```bash
    sam deploy --guided
    ```
    Follow the prompts to configure your stack name, AWS region, and parameter overrides.

3.  **Configure Triggers**:
    The `template.yaml` includes an example Log Group and Subscription Filter. In a real scenario, you would attach the `LogMonitorFunction` to your existing Log Groups using CloudWatch Subscription Filters.

### Updating Source Code

If you only need to update the Lambda function code (e.g., `src/`), you can use `sam sync` for faster updates during development:

```bash
sam sync --stack-name <your-stack-name> --code
```

Or, if you prefer the standard deployment but want to skip the guided prompts:

```bash
sam build
sam deploy
```

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
      "log_group_pattern": "/aws/lambda/main-app",
      "pattern": "api-.*",
      "filters": ["ERROR"],
      "severity": "ERROR",
      "mention": "@channel",
      "whitelist": ["HealthCheck", "ThrottlingException"],
      "slack_webhook_url": "..."
    },
    {
      "type": "worker",
      "log_group_pattern": "/aws/lambda/main-app", 
      "pattern": "worker-.*",
      "filters": ["CRITICAL"],
      "severity": "CRITICAL",
      "mention": "@oncall-dev",
      "sns_topic_arn": "..."
    },
    {
      "type": "legacy-app",
      "log_group_pattern": "/aws/lambda/legacy-.*",
      # No stream pattern needed if we want all logs from this group
      "filters": ["Exception"],
      "sns_topic_arn": "..."
    }
  ]
}
```

- **type**: Friendly name for the log source.
- **pattern**: (Optional) Regex to match the Log Stream name. Required if `log_group_pattern` is not set.
- **log_group_pattern**: (Optional) Regex to match the Log Group name. Useful when multiple log groups share stream naming patterns.
- **filters**: List of keywords to trigger an alert.
- **whitelist**: List of regex patterns to ignore.
- **severity**: (Optional) Severity level (CRITICAL, ERROR, WARNING, INFO, DEBUG). Defaults to CRITICAL (🚨).
- **mention**: (Optional) User or channel to mention (e.g., `@channel`, `@user`).
- **slack_webhook_url**: Destination for Slack notifications.
- **sns_topic_arn**: Destination for SNS notifications.

### Configuration Tuning

To reduce noise (`whitelist`) or catch more errors (`filters`):

**1. Whitelist (Silence Noise)**
Use Regex patterns to ignore specific messages.
```json
"whitelist": [
  "Connection reset by peer",
  "User \\d+ failed auth"  // Escape backslashes!
]
```

**2. Filters (Catch Errors)**
Use keywords (case-insensitive) to trigger alerts.
```json
"filters": ["ERROR", "Exception", "PaymentFailed"]
```
