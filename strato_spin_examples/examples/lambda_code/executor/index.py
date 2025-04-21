import json
import boto3
import os
import logging
from .logic import execute_policy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    sqs = boto3.client("sqs")
    queue_url = os.environ["QUEUE_URL"]

    try:
        # Receive messages from SQS
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=10
        )

        if "Messages" not in response:
            logger.info("No messages to process")
            return {"statusCode": 200, "body": "No messages"}

        for message in response["Messages"]:
            body = json.loads(message["Body"])
            # Execute policy using core logic
            result = execute_policy(body)

            # Delete message from queue
            sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message["ReceiptHandle"]
            )
            logger.info(f"Deleted message {message['MessageId']} from SQS")

        return {"statusCode": 200, "body": "Messages processed successfully"}

    except Exception as e:
        logger.error(f"Error processing messages: {e}")
        return {"statusCode": 500, "body": str(e)}
