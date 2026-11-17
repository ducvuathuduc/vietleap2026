"""Explicit S3-compatible mirror of the local gold Parquet files."""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import duckdb

from .warehouse import KIT

S3_ENV = ("KIT_S3_ENDPOINT", "KIT_S3_BUCKET", "KIT_S3_ACCESS_KEY_ID", "KIT_S3_SECRET_ACCESS_KEY")


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sync_gold(lake: Path = KIT / "data/lake") -> list[str]:
    settings = [os.environ.get(key, "") for key in S3_ENV]
    missing = [key for key, value in zip(S3_ENV, settings) if not value]
    if missing:
        raise ValueError("Thiếu biến môi trường: " + ", ".join(missing))
    endpoint, bucket, access, secret = settings
    endpoint = urlsplit(endpoint if "://" in endpoint else f"https://{endpoint}")
    if (endpoint.scheme not in ("http", "https") or not endpoint.hostname or endpoint.username is not None
            or endpoint.path not in ("", "/") or endpoint.query or endpoint.fragment):
        raise ValueError("KIT_S3_ENDPOINT phải là một địa chỉ HTTP(S) không kèm đường dẫn hay thông tin đăng nhập")
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        raise ValueError("KIT_S3_BUCKET không đúng định dạng")
    files = sorted((lake / "gold").glob("*.parquet"))
    if not files:
        raise ValueError("Không có Parquet gold để đồng bộ")
    region = "auto" if endpoint.hostname.endswith(".r2.cloudflarestorage.com") else "us-east-1"
    con = duckdb.connect(database=":memory:")
    synced = []
    try:
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        con.execute(f"CREATE SECRET mirror (TYPE s3, ENDPOINT {_literal(endpoint.netloc)}, REGION {_literal(region)}, "
                    f"KEY_ID {_literal(access)}, SECRET {_literal(secret)}, URL_STYLE 'path', USE_SSL {endpoint.scheme == 'https'})")
        for source in files:
            dest = f"s3://{bucket}/gold/{source.name}"
            con.execute("COPY (SELECT * FROM read_parquet(?)) TO ? (FORMAT PARQUET)", [str(source), dest])
            synced.append(dest)
    except Exception:
        raise RuntimeError(f"Đồng bộ S3 qua httpfs thất bại sau {len(synced)} tệp. Kiểm tra endpoint, quyền ghi và cấu hình DuckDB.") from None
    finally:
        con.close()
    return synced
