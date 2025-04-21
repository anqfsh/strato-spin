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
