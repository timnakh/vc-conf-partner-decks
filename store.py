"""Public PDF links via S3-compatible storage (Cloudflare R2)."""

from __future__ import annotations

import os
from urllib.parse import quote

from fill import ascii_filename

KEYS = (
    "S3_ENDPOINT",
    "S3_BUCKET",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_PUBLIC_BASE",
)

MISSING = (
    "Нет бакета для ссылок. Cloudflare R2: создай public-бакет, "
    "в Render → Environment впиши S3_ENDPOINT (https://<accountid>.r2.cloudflarestorage.com), "
    "S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, "
    "S3_PUBLIC_BASE (https://decks.твой-домен или https://pub-….r2.dev)."
)


def configured() -> bool:
    return all(os.environ.get(k, "").strip() for k in KEYS)


def public_base() -> str:
    return os.environ.get("S3_PUBLIC_BASE", "").rstrip("/")


def put_pdf(key: str, data: bytes, filename: str) -> str:
    if not configured():
        raise RuntimeError(MISSING)
    import boto3
    from botocore.config import Config

    ascii_name = ascii_filename(filename)
    client = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"].rstrip("/"),
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("S3_REGION") or "auto",
        config=Config(signature_version="s3v4"),
    )
    client.put_object(
        Bucket=os.environ["S3_BUCKET"].strip(),
        Key=key,
        Body=data,
        ContentType="application/pdf",
        ContentDisposition=(
            f'inline; filename="{ascii_name}"; '
            f"filename*=UTF-8''{quote(filename)}"
        ),
        CacheControl="public, max-age=31536000, immutable",
    )
    return public_base() + "/" + quote(key, safe="/")
