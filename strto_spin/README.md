# StratoSpin

A YAML-based multi-cloud infrastructure deployment tool for AWS, Azure, and GCP.

## Features
- Deploy AWS resources (Lambda, KMS, S3, SQS, DynamoDB) with assert-based logic.
- Extensible plugin system for Azure and GCP.
- Environment flavours (dev, uat, prod) with name suffixing.
- Parallel deployment of independent resources.
- Poetry-based dependency management and private registry support.

## Installation
```bash
poetry install
```

## Usage
```bash
strato-spin deploy --infra examples/infra_dev.yaml --flavour dev
```

## Publish to Private Registry
```bash
poetry config repositories.company https://your-private-registry.com
poetry config http-basic.company username password
poetry publish --repository company
```

## Extending Plugins
Create a separate project (e.g., strato_spin_examples) with custom plugins in an extensions/ directory. Example:
```python
# strato_spin_examples/extensions/custom_s3_bucket.py
from strato_spin.resources.aws.s3.s3_bucket import S3Bucket

class CustomS3Bucket(S3Bucket):
    required_tags = ["ApplicationID", "CostCentre", "Environment", "SupportGroup"]
```
