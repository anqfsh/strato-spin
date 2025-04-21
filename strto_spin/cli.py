import click
from .core.deployer import Deployer

@click.group()
def cli():
    pass

@cli.command()
@click.option("--infra", required=True, help="Path to infra YAML file")
@click.option("--flavour", default="prod", help="Environment flavour (dev, uat, prod)")
@click.option("--extensions-path", default=None, help="Path to custom extensions directory")
def deploy(infra, flavour, extensions_path):
    """Deploy cloud infrastructure from YAML configuration"""
    deployer = Deployer(infra, flavour, extensions_path)
    deployer.deploy()
    click.echo("Deployment completed successfully")

if __name__ == "__main__":
    cli()
