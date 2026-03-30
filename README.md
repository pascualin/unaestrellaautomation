# Una Estrella Automation

AWS Lambda automation for the Una Estrella podcast workflow.

When a Notion `Grabaciones` record reaches `Estado invitado = Confirmado`, the Lambda:
- validates the webhook secret
- fetches the source Grabación from Notion
- validates business rules and idempotency
- creates one Google Calendar event in `primary`
- creates two Project records in Notion
- creates two episode records in Notion
- links those records back to the source Grabación
- writes status/error fields back to Grabaciones

## Repository layout
```text
src/
  config.py
  google_calendar_client.py
  handler.py
  naming.py
  notion_client.py
tests/
```

## Configuration
Environment variables:
- `NOTION_GRABACIONES_DS_ID`
- `NOTION_EPISODIOS_DS_ID`
- `NOTION_PROJECTS_DS_ID`
- `NOTION_AREA_UNA_ESTRELLA_ID`
- `GOOGLE_CALENDAR_ID`
- `SECRETS_MANAGER_SECRET_NAME`

Secrets Manager JSON secret:
```json
{
  "NOTION_TOKEN": "xxx",
  "GOOGLE_CLIENT_ID": "xxx",
  "GOOGLE_CLIENT_SECRET": "xxx",
  "GOOGLE_REFRESH_TOKEN": "xxx",
  "WEBHOOK_SHARED_SECRET": "xxx"
}
```

## Local testing
Install dependencies:
```bash
python3 -m pip install -r requirements.txt
```

Run unit tests:
```bash
PYTHONPATH=src pytest
```

## Deployment
Deploy this project as a single Python AWS Lambda function exposed through a Lambda Function URL.

The production implementation assumes:
- a 2-hour default Google Calendar event duration
- `GOOGLE_CALENDAR_ID=primary`
- all AWS resources live in the same region

## AWS setup checklist
1. Create a Secrets Manager secret named `podcast/una-estrella/automation`.
2. Store this JSON in that secret:
```json
{
  "NOTION_TOKEN": "xxx",
  "GOOGLE_CLIENT_ID": "xxx",
  "GOOGLE_CLIENT_SECRET": "xxx",
  "GOOGLE_REFRESH_TOKEN": "xxx",
  "WEBHOOK_SHARED_SECRET": "xxx"
}
```
3. Create an IAM role for the Lambda with:
   - `secretsmanager:GetSecretValue` on `podcast/una-estrella/automation`
   - `logs:CreateLogGroup`
   - `logs:CreateLogStream`
   - `logs:PutLogEvents`
4. Create a Lambda function:
   - Runtime: `Python 3.11`
   - Handler: `handler.lambda_handler`
   - Architecture: `x86_64`
   - Timeout: start with `30` seconds
5. Add these environment variables to the Lambda:
   - `NOTION_GRABACIONES_DS_ID=a064f802-b097-4c8e-b539-1fd5bafb736c`
   - `NOTION_EPISODIOS_DS_ID=2a964f5c-cfab-819d-b6ef-000b18cffd7b`
   - `NOTION_PROJECTS_DS_ID=4ab21bd1-d275-4d7d-b2bb-5147c64b8e2a`
   - `NOTION_AREA_UNA_ESTRELLA_ID=31486d6f-ebef-4ef5-98e1-266912e15376`
   - `GOOGLE_CALENDAR_ID=primary`
   - `SECRETS_MANAGER_SECRET_NAME=podcast/una-estrella/automation`
6. Enable a Lambda Function URL:
   - Auth type: `NONE`
   - CORS: disabled unless you know you need it
7. Create the Notion automation that sends a POST to the Function URL with:
   - Header: `x-webhook-secret`
   - Value: same value as `WEBHOOK_SHARED_SECRET`
   - Body:
```json
{
  "grabacion_page_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

## GitHub Actions deployment setup
1. Push this repository to GitHub.
2. In AWS IAM, add the GitHub OIDC identity provider if you do not already have it:
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`
3. Create an IAM role for GitHub Actions deployment with a trust policy that allows your GitHub repo to assume it:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:pascualin/unaestrellaautomation:ref:refs/heads/main"
        }
      }
    }
  ]
}
```
4. Attach a policy to that deploy role allowing:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:GetFunctionConfiguration",
        "lambda:UpdateFunctionCode"
      ],
      "Resource": "arn:aws:lambda:<AWS_REGION>:<AWS_ACCOUNT_ID>:function:una-estrella-automation"
    }
  ]
}
```
5. In GitHub repository settings, add this Actions secret:
   - `AWS_DEPLOY_ROLE_ARN=<the ARN of the deploy role>`
6. If your Lambda is not in `eu-west-1` or is not named `una-estrella-automation`, update `.github/workflows/deploy.yml`.
7. Push to `main` or run the workflow manually from the Actions tab.

## First deployment order
1. Create the AWS secret.
2. Create the Lambda execution role.
3. Create the Lambda function and set its environment variables.
4. Enable the Function URL.
5. Do one manual deploy from your machine or from the AWS console.
6. Confirm the function starts and can read Secrets Manager.
7. Create the GitHub OIDC deploy role.
8. Add `AWS_DEPLOY_ROLE_ARN` in GitHub.
9. Push to `main` and let GitHub Actions handle future deployments.

Suggested zip deployment flow:
```bash
rm -rf package lambda.zip
mkdir -p package
python3 -m pip install -r requirements.txt -t package
cp -R src/* package/
cd package && zip -r ../lambda.zip .
```

Lambda setup:
- Runtime: Python 3.11 or newer
- Handler: `handler.lambda_handler`
- Function URL: enable and configure as the HTTPS webhook endpoint
- Environment variables: set the six values from the requirements document
- IAM role: allow `secretsmanager:GetSecretValue` and CloudWatch Logs writes

Update flow:
```bash
aws lambda update-function-code \
  --function-name una-estrella-automation \
  --zip-file fileb://lambda.zip
```

## Manual verification checklist
- Valid webhook with no guests creates 1 calendar event, 2 projects, and 2 episodes
- Valid webhook with 1 guest adds the guest only to Episode 2
- Valid webhook with 2 guests renders `A y B`
- Valid webhook with 3+ guests uses compact calendar naming and full Project/Episode naming
- Invalid webhook secret returns `401`
- Repeated invocation does not create duplicates
