from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import boto3
from botocore.client import BaseClient

from app.core.settings import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider = self.settings.audio_storage_provider.lower()
        self._s3_client: BaseClient | None = None

    def _get_s3_client(self) -> BaseClient:
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                region_name=self.settings.aws_region,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
            )
        return self._s3_client

    def save_audio(self, content: bytes, filename_hint: str) -> str:
        suffix = Path(filename_hint).suffix or ".wav"
        object_name = f"audio/{uuid4().hex}{suffix}"

        if self.provider == "s3":
            if not self.settings.aws_s3_bucket:
                raise RuntimeError("AWS_S3_BUCKET is required for s3 provider")
            s3 = self._get_s3_client()
            s3.put_object(
                Bucket=self.settings.aws_s3_bucket,
                Key=object_name,
                Body=content,
                ContentType="audio/wav",
            )
            return f"s3://{self.settings.aws_s3_bucket}/{object_name}"

        upload_dir = Path(self.settings.local_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        target = upload_dir / object_name.replace("/", "_")
        target.write_bytes(content)
        return str(target)

