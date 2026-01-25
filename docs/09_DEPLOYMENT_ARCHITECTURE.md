# Deployment Architecture

## 1. Infrastructure as Code Approach

### 1.1 Tooling Stack

| Tool | Purpose | Version |
|------|---------|---------|
| AWS CloudFormation | Infrastructure provisioning | Latest |
| AWS SAM | Serverless application deployment | 1.100+ |
| GitHub Actions | CI/CD automation | N/A |

### 1.2 Directory Structure

```
truthlayer/
├── infrastructure/
│   ├── cloudformation/
│   │   ├── main.yaml              # Root stack
│   │   ├── api-gateway.yaml       # API Gateway resources
│   │   ├── lambda.yaml            # Lambda functions
│   │   ├── dynamodb.yaml          # DynamoDB tables
│   │   ├── s3.yaml                # S3 buckets
│   │   └── iam.yaml               # IAM roles and policies
│   ├── parameters/
│   │   ├── dev.json               # Dev environment params
│   │   ├── staging.json           # Staging environment params
│   │   └── prod.json              # Production environment params
│   └── scripts/
│       ├── deploy.sh              # Deployment script
│       ├── teardown.sh            # Cleanup script
│       └── validate.sh            # Template validation
├── src/
│   ├── lambda/
│   │   ├── verification/          # Verification Lambda
│   │   ├── document_processor/    # Document processing Lambda
│   │   └── analytics/             # Analytics Lambda
│   └── layers/
│       └── common/                # Shared code layer
├── frontend/
│   └── dashboard/                 # React dashboard
└── .github/
    └── workflows/
        ├── deploy-dev.yaml        # Dev deployment
        ├── deploy-staging.yaml    # Staging deployment
        └── deploy-prod.yaml       # Production deployment
```

---

## 2. CloudFormation Template Structure

### 2.1 Main Stack (main.yaml)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: TruthLayer - AI Hallucination Verification System

Parameters:
  Environment:
    Type: String
    AllowedValues: [dev, staging, prod]
    Description: Deployment environment
  
  ApiStageName:
    Type: String
    Default: v1
    Description: API Gateway stage name

Resources:
  # Nested Stacks
  DynamoDBStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: ./dynamodb.yaml
      Parameters:
        Environment: !Ref Environment

  S3Stack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: ./s3.yaml
      Parameters:
        Environment: !Ref Environment

  IAMStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: ./iam.yaml
      Parameters:
        Environment: !Ref Environment
        DocumentsBucketArn: !GetAtt S3Stack.Outputs.DocumentsBucketArn
        DynamoDBTableArns: !GetAtt DynamoDBStack.Outputs.TableArns

  LambdaStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: ./lambda.yaml
      Parameters:
        Environment: !Ref Environment
        LambdaRoleArn: !GetAtt IAMStack.Outputs.LambdaRoleArn
        DocumentsBucketName: !GetAtt S3Stack.Outputs.DocumentsBucketName

  ApiGatewayStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: ./api-gateway.yaml
      Parameters:
        Environment: !Ref Environment
        StageName: !Ref ApiStageName
        VerificationLambdaArn: !GetAtt LambdaStack.Outputs.VerificationLambdaArn
        DocumentLambdaArn: !GetAtt LambdaStack.Outputs.DocumentLambdaArn
        AnalyticsLambdaArn: !GetAtt LambdaStack.Outputs.AnalyticsLambdaArn

Outputs:
  ApiEndpoint:
    Description: API Gateway endpoint URL
    Value: !GetAtt ApiGatewayStack.Outputs.ApiEndpoint
    Export:
      Name: !Sub ${Environment}-TruthLayer-ApiEndpoint

  DashboardUrl:
    Description: Dashboard URL
    Value: !GetAtt S3Stack.Outputs.DashboardUrl
```

### 2.2 DynamoDB Stack (dynamodb.yaml)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: TruthLayer DynamoDB Tables

Parameters:
  Environment:
    Type: String

Resources:
  DocumentsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub TruthLayer-${Environment}-Documents
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: document_id
          AttributeType: S
        - AttributeName: user_id
          AttributeType: S
        - AttributeName: created_at
          AttributeType: S
      KeySchema:
        - AttributeName: document_id
          KeyType: HASH
      GlobalSecondaryIndexes:
        - IndexName: UserDocumentsIndex
          KeySchema:
            - AttributeName: user_id
              KeyType: HASH
            - AttributeName: created_at
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      Tags:
        - Key: Environment
          Value: !Ref Environment
        - Key: Project
          Value: TruthLayer

  EmbeddingsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub TruthLayer-${Environment}-Embeddings
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: document_id
          AttributeType: S
        - AttributeName: chunk_id
          AttributeType: S
      KeySchema:
        - AttributeName: document_id
          KeyType: HASH
        - AttributeName: chunk_id
          KeyType: RANGE
      TimeToLiveSpecification:
        AttributeName: ttl
        Enabled: true
      Tags:
        - Key: Environment
          Value: !Ref Environment

  VerificationsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub TruthLayer-${Environment}-Verifications
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: user_id
          AttributeType: S
        - AttributeName: verification_id
          AttributeType: S
        - AttributeName: document_id
          AttributeType: S
        - AttributeName: created_at
          AttributeType: S
      KeySchema:
        - AttributeName: user_id
          KeyType: HASH
        - AttributeName: verification_id
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: DocumentVerificationsIndex
          KeySchema:
            - AttributeName: document_id
              KeyType: HASH
            - AttributeName: created_at
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      TimeToLiveSpecification:
        AttributeName: ttl
        Enabled: true

  ApiKeysTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub TruthLayer-${Environment}-ApiKeys
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: key_hash
          AttributeType: S
        - AttributeName: user_id
          AttributeType: S
      KeySchema:
        - AttributeName: key_hash
          KeyType: HASH
      GlobalSecondaryIndexes:
        - IndexName: UserKeysIndex
          KeySchema:
            - AttributeName: user_id
              KeyType: HASH
          Projection:
            ProjectionType: ALL

Outputs:
  TableArns:
    Value: !Join
      - ','
      - - !GetAtt DocumentsTable.Arn
        - !GetAtt EmbeddingsTable.Arn
        - !GetAtt VerificationsTable.Arn
        - !GetAtt ApiKeysTable.Arn
```

### 2.3 Lambda Stack (lambda.yaml)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: TruthLayer Lambda Functions

Parameters:
  Environment:
    Type: String
  LambdaRoleArn:
    Type: String
  DocumentsBucketName:
    Type: String

Resources:
  CommonLayer:
    Type: AWS::Lambda::LayerVersion
    Properties:
      LayerName: !Sub TruthLayer-${Environment}-Common
      Description: Shared dependencies
      Content:
        S3Bucket: !Sub truthlayer-artifacts-${Environment}
        S3Key: layers/common.zip
      CompatibleRuntimes:
        - python3.11

  VerificationFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub TruthLayer-${Environment}-Verification
      Runtime: python3.11
      Handler: handler.lambda_handler
      Code:
        S3Bucket: !Sub truthlayer-artifacts-${Environment}
        S3Key: lambda/verification.zip
      Role: !Ref LambdaRoleArn
      MemorySize: 512
      Timeout: 10
      Layers:
        - !Ref CommonLayer
      Environment:
        Variables:
          ENVIRONMENT: !Ref Environment
          DOCUMENTS_TABLE: !Sub TruthLayer-${Environment}-Documents
          EMBEDDINGS_TABLE: !Sub TruthLayer-${Environment}-Embeddings
          VERIFICATIONS_TABLE: !Sub TruthLayer-${Environment}-Verifications
          BEDROCK_MODEL_ID: amazon.titan-embed-text-v1
      TracingConfig:
        Mode: Active

  DocumentProcessorFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub TruthLayer-${Environment}-DocumentProcessor
      Runtime: python3.11
      Handler: handler.lambda_handler
      Code:
        S3Bucket: !Sub truthlayer-artifacts-${Environment}
        S3Key: lambda/document_processor.zip
      Role: !Ref LambdaRoleArn
      MemorySize: 1024
      Timeout: 30
      Layers:
        - !Ref CommonLayer
      Environment:
        Variables:
          ENVIRONMENT: !Ref Environment
          DOCUMENTS_BUCKET: !Ref DocumentsBucketName
          DOCUMENTS_TABLE: !Sub TruthLayer-${Environment}-Documents
          EMBEDDINGS_TABLE: !Sub TruthLayer-${Environment}-Embeddings

  AnalyticsFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Sub TruthLayer-${Environment}-Analytics
      Runtime: python3.11
      Handler: handler.lambda_handler
      Code:
        S3Bucket: !Sub truthlayer-artifacts-${Environment}
        S3Key: lambda/analytics.zip
      Role: !Ref LambdaRoleArn
      MemorySize: 256
      Timeout: 5
      Environment:
        Variables:
          ENVIRONMENT: !Ref Environment
          VERIFICATIONS_TABLE: !Sub TruthLayer-${Environment}-Verifications

Outputs:
  VerificationLambdaArn:
    Value: !GetAtt VerificationFunction.Arn
  DocumentLambdaArn:
    Value: !GetAtt DocumentProcessorFunction.Arn
  AnalyticsLambdaArn:
    Value: !GetAtt AnalyticsFunction.Arn
```

---

## 3. CI/CD Pipeline Design

### 3.1 Pipeline Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Commit    │───▶│    Build    │───▶│    Test     │───▶│   Deploy    │
│   (Push)    │    │   & Lint    │    │   & Scan    │    │   to Env    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │                  │
      │                  │                  │                  │
      ▼                  ▼                  ▼                  ▼
   GitHub           Run Tests          Security           CloudFormation
   Actions          Build Artifacts     Scan               Deploy
```

### 3.2 GitHub Actions Workflow (deploy-dev.yaml)

```yaml
name: Deploy to Development

on:
  push:
    branches: [develop]
  pull_request:
    branches: [develop]

env:
  AWS_REGION: us-east-1
  ENVIRONMENT: dev

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install cfn-lint
          pip install -r requirements-dev.txt
      
      - name: Lint CloudFormation
        run: cfn-lint infrastructure/cloudformation/*.yaml
      
      - name: Run Python linter
        run: |
          pip install flake8
          flake8 src/lambda --max-line-length=100

  test:
    runs-on: ubuntu-latest
    needs: validate
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      
      - name: Run unit tests
        run: pytest tests/unit --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Build Lambda packages
        run: |
          cd src/lambda/verification
          pip install -r requirements.txt -t ./package
          cd package && zip -r ../verification.zip . && cd ..
          zip -g verification.zip handler.py
      
      - name: Build common layer
        run: |
          cd src/layers/common
          pip install -r requirements.txt -t ./python
          zip -r common.zip python
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: lambda-packages
          path: |
            src/lambda/*/verification.zip
            src/layers/common/common.zip

  deploy:
    runs-on: ubuntu-latest
    needs: build
    if: github.event_name == 'push'
    environment: development
    steps:
      - uses: actions/checkout@v4
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: lambda-packages
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Upload to S3
        run: |
          aws s3 cp src/lambda/verification.zip s3://truthlayer-artifacts-dev/lambda/
          aws s3 cp src/layers/common/common.zip s3://truthlayer-artifacts-dev/layers/
      
      - name: Deploy CloudFormation
        run: |
          aws cloudformation deploy \
            --template-file infrastructure/cloudformation/main.yaml \
            --stack-name TruthLayer-dev \
            --parameter-overrides file://infrastructure/parameters/dev.json \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
            --no-fail-on-empty-changeset
      
      - name: Run integration tests
        run: pytest tests/integration --environment=dev
```

### 3.3 Production Deployment (deploy-prod.yaml)

```yaml
name: Deploy to Production

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to deploy'
        required: true

jobs:
  # ... similar structure with additional approval gates

  approve:
    runs-on: ubuntu-latest
    needs: [validate, test, build]
    environment: production
    steps:
      - name: Approval gate
        run: echo "Waiting for manual approval..."

  deploy-prod:
    runs-on: ubuntu-latest
    needs: approve
    steps:
      # Deploy with blue-green strategy
      - name: Deploy to production
        run: |
          aws cloudformation deploy \
            --template-file infrastructure/cloudformation/main.yaml \
            --stack-name TruthLayer-prod \
            --parameter-overrides file://infrastructure/parameters/prod.json \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
```

---

## 4. Environment Configuration

### 4.1 Parameter Files

**dev.json:**
```json
[
  {
    "ParameterKey": "Environment",
    "ParameterValue": "dev"
  },
  {
    "ParameterKey": "ApiStageName",
    "ParameterValue": "v1"
  },
  {
    "ParameterKey": "LambdaMemoryVerification",
    "ParameterValue": "512"
  },
  {
    "ParameterKey": "LambdaMemoryProcessor",
    "ParameterValue": "1024"
  },
  {
    "ParameterKey": "EnableTracing",
    "ParameterValue": "true"
  },
  {
    "ParameterKey": "LogRetentionDays",
    "ParameterValue": "7"
  }
]
```

**prod.json:**
```json
[
  {
    "ParameterKey": "Environment",
    "ParameterValue": "prod"
  },
  {
    "ParameterKey": "ApiStageName",
    "ParameterValue": "v1"
  },
  {
    "ParameterKey": "LambdaMemoryVerification",
    "ParameterValue": "512"
  },
  {
    "ParameterKey": "LambdaMemoryProcessor",
    "ParameterValue": "1024"
  },
  {
    "ParameterKey": "EnableTracing",
    "ParameterValue": "true"
  },
  {
    "ParameterKey": "LogRetentionDays",
    "ParameterValue": "30"
  },
  {
    "ParameterKey": "EnableWAF",
    "ParameterValue": "true"
  }
]
```

### 4.2 Environment Comparison

| Configuration | Dev | Staging | Prod |
|---------------|-----|---------|------|
| API Domain | api-dev.truthlayer.io | api-staging.truthlayer.io | api.truthlayer.io |
| Lambda Memory | 512 MB | 512 MB | 512 MB |
| Lambda Timeout | 10s | 10s | 10s |
| DynamoDB Mode | On-Demand | On-Demand | On-Demand |
| Log Retention | 7 days | 14 days | 30 days |
| X-Ray Tracing | Enabled | Enabled | Enabled |
| WAF | Disabled | Enabled | Enabled |
| CloudWatch Alarms | Basic | Standard | Full |
