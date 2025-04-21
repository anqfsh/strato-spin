import json
import boto3
import yaml
import os
import logging
from .logic import process_policy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    s3 = boto3.client("s3")
    sqs = boto3.client("sqs")
    bucket_name = os.environ["BUCKET_NAME"]
    queue_url = os.environ["QUEUE_URL"]

    try:
        # List objects in S3 policies/ prefix
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix="policies/")
        if "Contents" not in response:
            logger.info("No policies found in S3")
            return {"statusCode": 200, "body": "No policies to process"}

        for obj in response["Contents"]:
            key = obj["Key"]
            # Get YAML file
            file_obj = s3.get_object(Bucket=bucket_name, Key=key)
            policy_data = yaml.safe_load(file_obj["Body"].read().decode("utf-8"))

            # Process policy using core logic
            processed_data = process_policy(policy_data)

            # Write to SQS
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(processed_data)
            )
            logger.info(f"Sent policy {key} to SQS")

            # Write processed policy back to S3
            processed_key = f"processed/{key.split('/')[-1]}"
            s3.put_object(
                Bucket=bucket_name,
                Key=processed_key,
                Body=yaml.dump(processed_data)
            )
            logger.info(f"Wrote processed policy to s3://{bucket_name}/{processed_key}")

        return {"statusCode": 200, "body": "Policies processed successfully"}

    except Exception as e:
        logger.error(f"Error processing policies: {e}")
        return {"statusCode": 500, "body": str(e)}
