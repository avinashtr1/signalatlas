# SignalAtlas Rebuild Readiness v1

Date: 26 September 2026

Status: PASSED

## Scope

Same-machine isolated reconstruction test using a clean exported source tree under /tmp.

This is a Rebuild Readiness certification.

It is NOT a Clean-VPS Rebuild Rehearsal certification.

## Source baseline

Git baseline at test start:

f455db8

## Validation performed

The isolated reconstruction successfully proved:

- clean certified source export
- no inherited .api-venv
- no inherited EdgeAtlas node_modules
- no inherited canonical SQLite database
- clean core Python virtual environment creation
- installation from requirements-core.txt
- canonical Polymarket adapter import
- canonical market measurement collector import
- canonical CLOB collector import
- forward outcome engine import
- system monitor import
- resolution collector import
- data durability module import
- clean API virtual environment creation
- installation from requirements-api.txt
- FastAPI / Uvicorn API imports
- canonical Python source compilation
- clean EdgeAtlas npm ci
- successful EdgeAtlas production build
- recovery manifest verification
- canonical SQLite backup verification
- canonical SQLite restore-drill

Final isolated test result:

REBUILD READINESS ISOLATED TEST: PASSED

## Dependency contracts established

Core measurement runtime:

requirements-core.txt

API runtime:

requirements-api.txt

EdgeAtlas:

edgeatlas_web/package.json
edgeatlas_web/package-lock.json

## Recovery infrastructure established

signalatlas_registry/recovery/

including:

- RECOVER.md
- RUNTIME_BASELINE.txt
- READINESS_AUDIT.md
- crontab.txt
- env.example
- systemd unit snapshots
- MANIFEST.sha256

## Safety findings

SignalAtlas read-only recovery does not require Polymarket trading credentials.

POLY_PRIVATE_KEY and POLY_FUNDER are VelocityAtlas-only.

VelocityAtlas must remain disabled during a SignalAtlas recovery.

No experimental/untracked execution source is required for the certified SignalAtlas rebuild.

## Remaining final DR gate

Clean-VPS Rebuild Rehearsal v1 remains outstanding.

It requires:

1. genuinely independent machine
2. certified Git source
3. fresh runtime reconstruction
4. off-host database backup sourced from the Windows DR machine
5. backup hash verification
6. restore-drill
7. service installation
8. scheduler installation
9. reboot/restart validation
10. SignalAtlas API health validation
11. EdgeAtlas validation
12. confirmation that VelocityAtlas remains disabled

Until that independent-machine test passes, status remains:

Rebuild Readiness v1 — PASSED
Clean-VPS Rebuild Rehearsal v1 — DEFERRED
