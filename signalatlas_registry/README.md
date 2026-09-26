# SignalAtlas Unified Registry

This directory is the canonical architecture and inventory layer for SignalAtlas.

Purpose:

- prevent duplicate rebuilding
- preserve canonical architecture
- distinguish active, frozen, historical, and retired components
- inventory measurement, APIs, dashboards, execution boundaries, and distribution surfaces
- keep implementation aligned across development sessions

Primary files:

- SYSTEM_MAP.md
- CANONICAL_ARCHITECTURE.md
- SIGNALATLAS_MASTER_ROADMAP.md
- ENGINE_REGISTRY.json
- SIGNALATLAS_ENGINE_REGISTRY.md
- API_REGISTRY.json
- SIGNALATLAS_API_REGISTRY.md
- DASHBOARD_REGISTRY.json
- TELEGRAM_REGISTRY.json
- ANALYTICS_REGISTRY.json

Current operational truth:

Data
→ Measurement
→ Forward Outcomes
→ Health
→ Read-only API

The Brain is currently fail-closed.

Legacy intelligence distribution is retired.

VelocityAtlas remains a separate execution layer.
