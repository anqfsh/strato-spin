import boto3
import logging

logger = logging.getLogger(__name__)

def chain_assume_role(role_chain, region="ap-southeast-2"):
    session = boto3.Session(region_name=region)
    try:
        sts_client = session.client("sts")
        sts_client.get_caller_identity()
        logger.info("Using default credentials from environment")
    except Exception as e:
        logger.error(f"No valid credentials found: {e}")
        raise

    for role in role_chain:
        try:
            sts_client = session.client("sts")
            response = sts_client.assume_role(
                RoleArn=role["role_arn"],
                RoleSessionName=role["session_name"]
            )
            credentials = response["Credentials"]
            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=region
            )
            logger.info(f"Assumed role: {role['role_arn']}")
        except Exception as e:
            logger.error(f"Failed to assume role {role['role_arn']}: {e}")
            raise
    return session
