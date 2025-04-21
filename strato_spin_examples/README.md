# StratoSpin Examples

This project contains example YAML configurations and custom extensions for the StratoSpin tool.

## Structure
- `examples/`: YAML files and Lambda code for deploying AWS resources (KMS, S3, Lambda, SQS, EventBridge).
- `extensions/`: Custom plugins (e.g., CustomS3Bucket with enforced tags).

## Installation
```bash
poetry install
```

## Usage
Deploy to AWS:
```bash
strato-spin deploy --infra examples/infra_dev.yaml --flavour dev --extensions-path extensions
```

Run Lambda locally:
```bash
cd strato_spin_examples/examples/lambda_code/scheduler
poetry run scheduler --file path/to/policy.yaml
cd strato_spin_examples/examples/lambda_code/executor
poetry run executor --file path/to/message.json
```
