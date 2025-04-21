import click
import yaml
import logging
from .logic import process_policy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@click.command()
@click.option("--file", required=True, type=click.Path(exists=True), help="Path to input YAML policy file")
@click.option("--output", type=click.Path(), help="Path to output processed YAML file")
def scheduler(file, output):
    """Process a policy YAML file locally"""
    try:
        with open(file, "r") as f:
            policy_data = yaml.safe_load(f)

        processed_data = process_policy(policy_data, output_file=output)
        click.echo(f"Processed policy: {processed_data['name']}")

    except Exception as e:
        logger.error(f"Error processing policy: {e}")
        click.echo(f"Error: {e}", err=True)
        exit(1)

if __name__ == "__main__":
    scheduler()
