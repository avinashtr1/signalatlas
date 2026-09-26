# SignalAtlas Disaster Recovery Procedure

Canonical date: 26 September 2026

## Purpose

Reconstruct the certified SignalAtlas foundation from independently recoverable artifacts.

The recovery target is the read-only SignalAtlas measurement/intelligence infrastructure.

VelocityAtlas is a separate execution system and MUST remain disabled unless recovered under a separate explicit execution-security procedure.

## Required recovery inputs

1. Certified Git repository
2. Off-host `market_measurements.sqlite3` backup plus matching manifest
3. GitHub access or a newly-authorized deploy key
4. Recovery credential procedure
5. Ubuntu 24.04 x86_64 machine
6. Network access for package installation

Do not depend on untracked files from the failed/source VPS.

## Certified source

Current canonical baseline:

`f455db8`

The recovery must use the certified Git history and must not silently import experimental/untracked source files.

## Repository location

Canonical runtime path:

`/root/.openclaw/workspace`

## Python environments

### Core measurement runtime

Create an isolated environment from:

`requirements-core.txt`

Current direct dependency contract:

`py-clob-client==0.34.6`

Canonical collectors:

- polymarket_engine.market_raw_collector
- polymarket_engine.orderbook_collector
- polymarket_engine.outcome_engine
- polymarket_engine.system_monitor
- polymarket_engine.resolution_collector
- polymarket_engine.data_durability

### Measurement API

Create `.api-venv` from:

`requirements-api.txt`

Runtime:

`python -m polymarket_engine.api_server`

## EdgeAtlas

Install deterministically with:

`npm ci`

Then create the production build with:

`npm run build`

Run through the canonical systemd service on:

`127.0.0.1:3030`

## Database recovery

Canonical database:

`analytics/market_measurements.sqlite3`

Backups are produced by:

`python3 -m polymarket_engine.data_durability backup`

Backup verification:

`python3 -m polymarket_engine.data_durability verify --backup <backup>`

Supported recovery validation:

`python3 -m polymarket_engine.data_durability restore-drill --backup <backup>`

A restore drill MUST pass before a recovered database is promoted into the canonical database path.

Do not fabricate missing database state.

Do not overwrite the canonical database until backup hash validation and restore-drill validation have passed.

## Scheduler

Canonical scheduler is stored in:

`signalatlas_registry/recovery/crontab.txt`

Review it before installation.

The canonical sequence is:

- :01 snapshots
- :02 CLOB/event measurement
- :04 forward outcomes
- :06 health
- :08 resolution truth
- :12 durability backup

## systemd

Canonical unit snapshots are stored under:

`signalatlas_registry/recovery/systemd/`

SignalAtlas services:

- signalatlas-measurement-api.service
- edgeatlas-web.service

VelocityAtlas unit is retained for reconstruction reference only:

- velocityatlas-live5m.service

VelocityAtlas MUST remain disabled during SignalAtlas recovery.

## Credentials

The certified SignalAtlas read-only measurement stack does not require the Polymarket trading private key.

`POLY_PRIVATE_KEY` and `POLY_FUNDER` belong to VelocityAtlas execution.

Never copy historical/burned credentials into a rebuilt system.

Generate new SSH/deploy credentials on the replacement machine where possible.

## Recovery validation gates

A clean rebuild is not certified until all applicable gates pass:

1. Git checkout verified
2. Core Python environment reconstructed
3. API environment reconstructed
4. EdgeAtlas dependency install succeeds
5. EdgeAtlas production build succeeds
6. Database backup hash validates
7. Database restore-drill succeeds
8. SQLite quick_check passes
9. Canonical collectors import/compile successfully
10. SignalAtlas API starts and reports healthy
11. EdgeAtlas starts and reaches the canonical API
12. Scheduler installed exactly as documented
13. SignalAtlas services survive restart
14. VelocityAtlas remains disabled
15. No untracked source from the old machine is required

## Certification distinction

`Rebuild Readiness v1` can be proven on the existing VPS using an isolated clean clone and clean environments.

`Clean-VPS Rebuild Rehearsal v1` requires a genuinely independent machine and an off-host database backup.

Do not mark Clean-VPS Rebuild Rehearsal PASSED based only on a same-machine test.
