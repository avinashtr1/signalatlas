import argparse
import gzip
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "analytics" / "market_measurements.sqlite3"
BACKUP_DIR = ROOT / "analytics" / "backups" / "market_measurements"

HOURLY_KEEP = 6
DAILY_KEEP = 7

STAMP_RE = re.compile(
    r"market_measurements_(\d{8}T\d{6}Z)\.sqlite3(?:\.gz)?$"
)


def utc_now():
    return datetime.now(timezone.utc)


def connect_ro(path):
    uri = f"file:{path.resolve()}?mode=ro"
    conn = sqlite3.connect(
        uri,
        uri=True,
        timeout=10.0,
    )
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def quote_ident(name):
    return '"' + name.replace('"', '""') + '"'


def quick_check(path):
    with connect_ro(path) as conn:
        rows = [
            row[0]
            for row in conn.execute(
                "PRAGMA quick_check"
            )
        ]

    if rows != ["ok"]:
        raise RuntimeError(
            f"SQLITE_QUICK_CHECK_FAILED:{rows}"
        )

    return "ok"


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as fp:
        for chunk in iter(
            lambda: fp.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def database_metadata(path):
    with connect_ro(path) as conn:
        page_size = conn.execute(
            "PRAGMA page_size"
        ).fetchone()[0]

        page_count = conn.execute(
            "PRAGMA page_count"
        ).fetchone()[0]

        tables = [
            row[0]
            for row in conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
        ]

        counts = {}

        for table in tables:
            counts[table] = conn.execute(
                f"SELECT COUNT(*) FROM {quote_ident(table)}"
            ).fetchone()[0]

    return {
        "page_size": page_size,
        "page_count": page_count,
        "logical_bytes": page_size * page_count,
        "tables": tables,
        "table_counts": counts,
    }


def fsync_file(path):
    with path.open("rb") as fp:
        os.fsync(fp.fileno())


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY)

    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def backup_artifacts():
    artifacts = []

    if not BACKUP_DIR.exists():
        return artifacts

    for pattern in (
        "market_measurements_*.sqlite3",
        "market_measurements_*.sqlite3.gz",
    ):
        artifacts.extend(
            BACKUP_DIR.glob(pattern)
        )

    return sorted(
        set(artifacts),
        key=lambda p: backup_timestamp(p),
    )


def backup_timestamp(path):
    m = STAMP_RE.match(path.name)

    if not m:
        raise RuntimeError(
            f"INVALID_BACKUP_NAME:{path}"
        )

    return datetime.strptime(
        m.group(1),
        "%Y%m%dT%H%M%SZ",
    ).replace(tzinfo=timezone.utc)


def latest_backup():
    artifacts = backup_artifacts()

    if not artifacts:
        raise RuntimeError("NO_BACKUPS_FOUND")

    return artifacts[-1]


def resolve_backup(value):
    if value == "latest":
        return latest_backup()

    path = Path(value)

    if not path.is_absolute():
        path = ROOT / path

    return path.resolve()


def manifest_path(path):
    return Path(
        str(path) + ".manifest.json"
    )


def gzip_sqlite(source, destination):
    with source.open("rb") as src:
        with destination.open("wb") as raw_out:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                compresslevel=1,
                fileobj=raw_out,
                mtime=0,
            ) as gz:
                while True:
                    chunk = src.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    gz.write(chunk)

            raw_out.flush()
            os.fsync(raw_out.fileno())


def materialize_backup(path, output):
    if path.name.endswith(".sqlite3.gz"):
        with gzip.open(path, "rb") as src:
            with output.open("wb") as dst:
                while True:
                    chunk = src.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    dst.write(chunk)

                dst.flush()
                os.fsync(dst.fileno())

    elif path.name.endswith(".sqlite3"):
        with connect_ro(path) as src:
            dst = sqlite3.connect(
                output,
                timeout=10.0,
            )

            try:
                dst.execute(
                    "PRAGMA synchronous=FULL"
                )

                src.backup(
                    dst,
                    pages=256,
                    sleep=0.050,
                )

                dst.commit()

                dst.execute(
                    "PRAGMA journal_mode=DELETE"
                )

                dst.commit()

            finally:
                dst.close()

    else:
        raise RuntimeError(
            f"UNSUPPORTED_BACKUP_FORMAT:{path}"
        )


def create_backup():
    if not DB.exists():
        raise RuntimeError(
            f"CANONICAL_DATABASE_MISSING:{DB}"
        )

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = utc_now().strftime(
        "%Y%m%dT%H%M%SZ"
    )

    final_path = (
        BACKUP_DIR /
        f"market_measurements_{stamp}.sqlite3.gz"
    )

    raw_tmp = (
        BACKUP_DIR /
        f".market_measurements_{stamp}.sqlite3.tmp"
    )

    gz_tmp = Path(
        str(final_path) + ".tmp"
    )

    final_manifest = manifest_path(
        final_path
    )

    manifest_tmp = Path(
        str(final_manifest) + ".tmp"
    )

    for path in (
        final_path,
        raw_tmp,
        gz_tmp,
        final_manifest,
        manifest_tmp,
    ):
        if path.exists():
            raise RuntimeError(
                f"BACKUP_PATH_ALREADY_EXISTS:{path}"
            )

    source_wal = Path(
        str(DB) + "-wal"
    )

    source_shm = Path(
        str(DB) + "-shm"
    )

    started = utc_now()

    try:
        with connect_ro(DB) as src:
            dst = sqlite3.connect(
                raw_tmp,
                timeout=10.0,
            )

            try:
                dst.execute(
                    "PRAGMA synchronous=FULL"
                )

                src.backup(
                    dst,
                    pages=256,
                    sleep=0.050,
                )

                dst.commit()

                dst.execute(
                    "PRAGMA journal_mode=DELETE"
                )

                dst.commit()

            finally:
                dst.close()

        quick_check(raw_tmp)

        metadata = database_metadata(
            raw_tmp
        )

        raw_bytes = raw_tmp.stat().st_size

        gzip_sqlite(
            raw_tmp,
            gz_tmp,
        )

        os.chmod(
            gz_tmp,
            0o600,
        )

        os.replace(
            gz_tmp,
            final_path,
        )

        fsync_directory(
            BACKUP_DIR
        )

        digest = sha256_file(
            final_path
        )

        completed = utc_now()

        compressed_bytes = (
            final_path.stat().st_size
        )

        manifest = {
            "schema_version":
                "signalatlas_data_durability_v1_1",

            "backup_type":
                "sqlite_online_backup",

            "artifact_format":
                "gzip_sqlite",

            "compression":
                "gzip_level_1",

            "source_database":
                str(DB.relative_to(ROOT)),

            "backup_database":
                str(final_path.relative_to(ROOT)),

            "started_at":
                started.isoformat(),

            "created_at":
                completed.isoformat(),

            "duration_seconds":
                round(
                    (
                        completed - started
                    ).total_seconds(),
                    3,
                ),

            "source_db_bytes":
                DB.stat().st_size,

            "source_wal_bytes":
                (
                    source_wal.stat().st_size
                    if source_wal.exists()
                    else 0
                ),

            "source_shm_bytes":
                (
                    source_shm.stat().st_size
                    if source_shm.exists()
                    else 0
                ),

            "uncompressed_backup_bytes":
                raw_bytes,

            "backup_bytes":
                compressed_bytes,

            "compression_ratio":
                round(
                    compressed_bytes /
                    raw_bytes,
                    6,
                ),

            "sha256":
                digest,

            "quick_check":
                "ok",

            "metadata":
                metadata,

            "python_sqlite_version":
                sqlite3.sqlite_version,
        }

        with manifest_tmp.open(
            "w",
            encoding="utf-8",
        ) as fp:
            json.dump(
                manifest,
                fp,
                indent=2,
                sort_keys=True,
            )

            fp.write("\n")
            fp.flush()
            os.fsync(fp.fileno())

        os.chmod(
            manifest_tmp,
            0o600,
        )

        os.replace(
            manifest_tmp,
            final_manifest,
        )

        fsync_directory(
            BACKUP_DIR
        )

        return manifest

    finally:
        for path in (
            raw_tmp,
            gz_tmp,
            manifest_tmp,
        ):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def verify_backup(path):
    if not path.exists():
        raise RuntimeError(
            f"BACKUP_NOT_FOUND:{path}"
        )

    mpath = manifest_path(path)

    if not mpath.exists():
        raise RuntimeError(
            f"MANIFEST_NOT_FOUND:{mpath}"
        )

    manifest = json.loads(
        mpath.read_text(
            encoding="utf-8"
        )
    )

    actual_hash = sha256_file(
        path
    )

    expected_hash = manifest.get(
        "sha256"
    )

    if actual_hash != expected_hash:
        raise RuntimeError(
            "BACKUP_SHA256_MISMATCH"
        )

    with tempfile.TemporaryDirectory(
        prefix="signalatlas_verify_"
    ) as tmpdir:

        materialized = (
            Path(tmpdir) /
            "verified.sqlite3"
        )

        materialize_backup(
            path,
            materialized,
        )

        qc = quick_check(
            materialized
        )

        metadata = database_metadata(
            materialized
        )

    expected_counts = (
        manifest
        .get("metadata", {})
        .get("table_counts", {})
    )

    if (
        metadata["table_counts"]
        != expected_counts
    ):
        raise RuntimeError(
            "BACKUP_TABLE_COUNT_MISMATCH"
        )

    return {
        "status": "VERIFIED",
        "backup": str(path),
        "sha256": actual_hash,
        "quick_check": qc,
        "backup_bytes":
            path.stat().st_size,
        "table_counts":
            metadata["table_counts"],
    }


def restore_drill(path):
    verification = verify_backup(
        path
    )

    with tempfile.TemporaryDirectory(
        prefix="signalatlas_restore_drill_"
    ) as tmpdir:

        tmpdir = Path(tmpdir)

        source = (
            tmpdir /
            "source.sqlite3"
        )

        restored = (
            tmpdir /
            "restored.sqlite3"
        )

        materialize_backup(
            path,
            source,
        )

        source_metadata = (
            database_metadata(source)
        )

        with connect_ro(source) as src:
            dst = sqlite3.connect(
                restored,
                timeout=10.0,
            )

            try:
                dst.execute(
                    "PRAGMA synchronous=FULL"
                )

                src.backup(
                    dst,
                    pages=256,
                    sleep=0.050,
                )

                dst.commit()

                dst.execute(
                    "PRAGMA journal_mode=DELETE"
                )

                dst.commit()

            finally:
                dst.close()

        qc = quick_check(
            restored
        )

        restored_metadata = (
            database_metadata(restored)
        )

        if (
            restored_metadata["tables"]
            != source_metadata["tables"]
        ):
            raise RuntimeError(
                "RESTORE_TABLE_SET_MISMATCH"
            )

        if (
            restored_metadata["table_counts"]
            != source_metadata["table_counts"]
        ):
            raise RuntimeError(
                "RESTORE_TABLE_COUNT_MISMATCH"
            )

        return {
            "status":
                "RESTORE_DRILL_OK",

            "source_backup":
                str(path),

            "backup_verified":
                verification["status"],

            "restored_quick_check":
                qc,

            "restored_tables":
                restored_metadata["tables"],

            "table_counts":
                restored_metadata[
                    "table_counts"
                ],
        }


def retention_plan():
    artifacts = backup_artifacts()

    if not artifacts:
        return {
            "keep": [],
            "delete": [],
        }

    newest = list(
        reversed(artifacts)
    )

    keep = set(
        newest[:HOURLY_KEEP]
    )

    daily_seen = set()
    daily_count = 0

    for path in newest:
        day = backup_timestamp(
            path
        ).date()

        if day in daily_seen:
            continue

        daily_seen.add(day)
        keep.add(path)
        daily_count += 1

        if daily_count >= DAILY_KEEP:
            break

    delete = [
        path
        for path in artifacts
        if path not in keep
    ]

    return {
        "keep": sorted(
            keep,
            key=backup_timestamp,
        ),
        "delete": delete,
    }


def apply_retention(apply=False):
    plan = retention_plan()

    deleted_bytes = 0
    deleted = []

    if apply:
        for path in plan["delete"]:
            mpath = manifest_path(
                path
            )

            if not mpath.exists():
                raise RuntimeError(
                    "RETENTION_REFUSES_UNMANIFESTED:"
                    f"{path}"
                )

            deleted_bytes += (
                path.stat().st_size
            )

            path.unlink()
            mpath.unlink()

            deleted.append(
                str(path)
            )

        fsync_directory(
            BACKUP_DIR
        )

    return {
        "status":
            (
                "RETENTION_APPLIED"
                if apply
                else "RETENTION_DRY_RUN"
            ),

        "hourly_keep":
            HOURLY_KEEP,

        "daily_keep":
            DAILY_KEEP,

        "keep": [
            str(p)
            for p in plan["keep"]
        ],

        "delete": [
            str(p)
            for p in plan["delete"]
        ],

        "deleted":
            deleted,

        "deleted_bytes":
            deleted_bytes,
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "SignalAtlas canonical SQLite "
            "durability tooling"
        )
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser(
        "backup",
    )

    verify_parser = sub.add_parser(
        "verify",
    )

    verify_parser.add_argument(
        "--backup",
        default="latest",
    )

    drill_parser = sub.add_parser(
        "restore-drill",
    )

    drill_parser.add_argument(
        "--backup",
        default="latest",
    )

    retention_parser = sub.add_parser(
        "retention",
    )

    retention_parser.add_argument(
        "--apply",
        action="store_true",
    )

    args = parser.parse_args()

    if args.command == "backup":
        result = create_backup()

    elif args.command == "verify":
        result = verify_backup(
            resolve_backup(
                args.backup
            )
        )

    elif args.command == "restore-drill":
        result = restore_drill(
            resolve_backup(
                args.backup
            )
        )

    elif args.command == "retention":
        result = apply_retention(
            apply=args.apply
        )

    else:
        raise RuntimeError(
            "UNKNOWN_COMMAND"
        )

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
