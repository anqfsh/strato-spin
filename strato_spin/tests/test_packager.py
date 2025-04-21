import pytest
import os
from strato_spin.resources.aws.lambda.packager import Packager

def test_packager_initialization(tmpdir):
    s3_client = None
    packager = Packager(s3_client, "test-bucket", "test-resource")
    assert os.path.exists(packager.temp_dir)
    assert packager.temp_dir.startswith(str(tmpdir))

def test_packager_cleanup(tmpdir):
    s3_client = None
    packager = Packager(s3_client, "test-bucket", "test-resource")
    temp_dir = packager.temp_dir
    del packager
    assert not os.path.exists(temp_dir)
