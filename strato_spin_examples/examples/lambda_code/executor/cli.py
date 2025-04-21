import click
import json
import logging
from .logic import execute_policy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@click.command()
@click.option("--file", required=True, type=click.Path(exists=True), help="Path to input JSON message file")
def executor(file):
    """Execute a policy message locally"""
    try:
        with open(file, "r") as f:
            policy_data = json.load(f)

        result = execute_policy(policy_data)
        click.echo(f"Executed policy: {result['policy_name']}")

    except Exception as e:
        logger.error(f"Error executing policy: {e}")
        click.echo(f"Error: {e}", err=True)
        exit(1)

if __name__ == "__main__":
    executor()
