import pytest
from strato_spin.core.deployer import Deployer

def test_deployer_initialization(tmpdir):
    infra_file = tmpdir / "infra.yaml"
    infra_file.write("""
flavour: test
resources: []
""")
    deployer = Deployer(str(infra_file), flavour="test")
    assert deployer.parser.flavour == "test"
