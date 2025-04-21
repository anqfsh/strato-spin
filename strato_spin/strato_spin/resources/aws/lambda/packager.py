import os
import shutil
import zipfile
import subprocess
import tempfile
import uuid
import boto3
from poetry.factory import Factory
import logging

logger = logging.getLogger(__name__)

class Packager:
    def __init__(self, s3_client, bucket_name, resource_name):
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.resource_name = resource_name
        self.temp_dir = tempfile.mkdtemp(prefix=f"packager-{resource_name}-")

    def __del__(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def package_lambda(self, source_dir, output_zip, dependency_manager="pip"):
        code_dir = os.path.join(self.temp_dir, "code")
        os.makedirs(code_dir)
        for item in os.listdir(source_dir):
            src_path = os.path.join(source_dir, item)
            dst_path = os.path.join(code_dir, item)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
        if dependency_manager == "pip" and os.path.exists(os.path.join(source_dir, "requirements.txt")):
            subprocess.check_call([
                "pip", "install", "-r", os.path.join(source_dir, "requirements.txt"),
                "--target", code_dir, "--upgrade"
            ])
        elif dependency_manager == "poetry" and os.path.exists(os.path.join(source_dir, "pyproject.toml")):
            self._install_poetry_deps(source_dir, code_dir)
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(code_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, code_dir)
                    zipf.write(file_path, arcname)

    def package_layer(self, source_dir, output_zip, dependency_manager="pip"):
        layer_dir = os.path.join(self.temp_dir, "python")
        os.makedirs(layer_dir)
        if dependency_manager == "pip" and os.path.exists(os.path.join(source_dir, "requirements.txt")):
            subprocess.check_call([
                "pip", "install", "-r", os.path.join(source_dir, "requirements.txt"),
                "--target", layer_dir, "--upgrade"
            ])
        elif dependency_manager == "poetry" and os.path.exists(os.path.join(source_dir, "pyproject.toml")):
            self._install_poetry_deps(source_dir, layer_dir)
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(self.temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.temp_dir)
                    zipf.write(file_path, arcname)

    def _install_poetry_deps(self, source_dir, target_dir):
        poetry = Factory().create_poetry(source_dir)
        dependencies = poetry.package.dependencies
        for dep in dependencies:
            if not dep.is_optional() and not dep.is_vcs():
                subprocess.check_call([
                    "pip", "install", f"{dep.name}{dep.constraint}", "--target", target_dir, "--upgrade"
                ])

    def upload_to_s3(self, zip_path, s3_key_prefix):
        unique_key = f"{s3_key_prefix}/{self.resource_name}/{uuid.uuid4()}.zip"
        self.s3_client.upload_file(zip_path, self.bucket_name, unique_key)
        return unique_key
