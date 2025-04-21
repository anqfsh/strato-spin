import yaml
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def process_policy(policy_data, output_file=None):
    """Core logic for processing policy data"""
    try:
        # Add timestamp to policy
        policy_data["processed_at"] = datetime.utcnow().isoformat()

        # Example: Log policy details
        logger.info(f"Processing policy: {policy_data['name']}")

        # If output file specified (local mode), write processed policy
        if output_file:
            with open(output_file, "w") as f:
                yaml.dump(policy_data, f)
            logger.info(f"Wrote processed policy to {output_file}")

        return policy_data

    except Exception as e:
        logger.error(f"Error processing policy: {e}")
        raise
