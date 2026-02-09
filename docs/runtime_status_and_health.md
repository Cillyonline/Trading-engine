# How to Read Runtime Status & Health

## 1) Audience & Purpose

This document is for operators, reviewers, and non-developer stakeholders who need to understand what the system is reporting right now.

Its purpose is to make runtime reporting readable at a glance: what state the runtime is in, whether it is healthy, and what additional context introspection provides.

## 2) Runtime Status

Runtime status answers one basic question: **"What is the runtime doing right now?"**

It is a snapshot of the current operating state, not a history of everything that happened before.

### Typical Runtime States

- **starting**: The runtime is initializing and not yet in steady operation.
- **running**: The runtime is active and operating normally.
- **stopped**: The runtime is not active.
- **degraded**: The runtime is active but not in ideal operating condition.

### Example Response (JSON)

```json
{
  "engine_id": "engine-main",
  "runtime_state": "running",
  "since": "2026-02-08T10:00:00Z",
  "uptime_seconds": 8640,
  "version": {
    "build": "2026.02.08.1",
    "commit": "abc123def",
    "api": "v1"
  },
  "clock": {
    "now": "2026-02-08T12:24:00Z"
  },
  "last_event": {
    "at": "2026-02-08T12:23:58Z",
    "kind": "heartbeat",
    "message": "Runtime loop active"
  }
}
```

### Operational Meaning of Fields

- **engine_id**: Which runtime instance produced this status.
- **runtime_state**: The current high-level operating state.
- **since**: When the current state started.
- **uptime_seconds**: How long the runtime has been active in total.
- **version.build**: Build identifier for this runtime release.
- **version.commit**: Source revision identifier tied to this runtime build.
- **version.api**: API contract version in use.
- **clock.now**: Current server time when the status was generated.
- **last_event.at**: Time of the latest reported runtime event.
- **last_event.kind**: Category of the latest event.
- **last_event.message**: Human-readable summary of the latest event.

## 3) Health Information

Health answers a different question: **"How safe is normal operation right now?"**

Status can tell you that something is running. Health tells you whether it appears operationally sound.

### Health Levels

- **healthy**: Checks indicate normal operational condition.
- **unhealthy**: One or more critical checks indicate operation is not currently reliable.
- **unknown**: Health could not be confidently determined from available checks.

### Example Response (JSON)

```json
{
  "level": "healthy",
  "summary": "Runtime checks are passing",
  "checks": [
    {
      "name": "runtime_loop",
      "status": "ok",
      "detail": "Loop heartbeat is current",
      "last_ok_at": "2026-02-08T12:23:59Z"
    },
    {
      "name": "queue_backlog",
      "status": "ok",
      "detail": "Backlog is within expected limits",
      "last_ok_at": "2026-02-08T12:23:57Z"
    }
  ]
}
```

### Operational Meaning of Fields

- **level**: Overall health conclusion (`healthy`, `unhealthy`, or `unknown`).
- **summary**: One-line plain-language explanation of the overall level.
- **checks**: Individual condition checks contributing to the overall level.
- **checks[].name**: Name of the specific check.
- **checks[].status**: Result for that check (for example `ok`, `warn`, `fail`, or `unknown`).
- **checks[].detail**: Short context about that check result.
- **checks[].last_ok_at**: Last known time the check was in an OK state.

## 4) Introspection Data

Introspection provides **context about current runtime configuration and limits** so operators can interpret status and health more accurately.

It is informational metadata, not a command surface.

### Typical Fields You Might See

- **configuration_snapshot**: Safe, high-level current configuration view.
- **feature_flags**: Which optional runtime features are enabled or disabled.
- **runtime_limits**: Operational limits and thresholds currently in effect.
- **dependencies**: High-level condition of internal/external dependencies.

### Example Response (JSON)

```json
{
  "configuration_snapshot": {
    "mode": "production",
    "region": "eu-central"
  },
  "feature_flags": {
    "extended_metrics": true,
    "verbose_events": false
  },
  "runtime_limits": {
    "max_queue_depth": 1000,
    "warning_queue_depth": 800
  },
  "dependencies": [
    {
      "name": "market_data_feed",
      "status": "available",
      "updated_at": "2026-02-08T12:24:00Z"
    },
    {
      "name": "storage",
      "status": "degraded",
      "updated_at": "2026-02-08T12:23:55Z"
    }
  ]
}
```

### Safe-to-Act-On Signals vs Informational Signals

High-level signals typically safe to act on operationally:
- **runtime_state** from status
- **level** from health
- **dependencies[].status** from introspection

Primarily informational context:
- **version** metadata
- **feature_flags**
- **configuration_snapshot**
- **runtime_limits**

"Safe to act on" here means these are suitable for high-level monitoring and escalation decisions. It does **not** imply direct runtime control actions.

## 5) How to Read This Holistically

Status, health, and introspection describe different layers of the same picture:

- **Status** = current operating state
- **Health** = operational condition confidence
- **Introspection** = surrounding context for interpretation

Common high-level combinations:

- **running + healthy + stable dependencies**: normal operating profile.
- **running + unhealthy + degraded dependencies**: active runtime with elevated operational risk.
- **starting + unknown health**: transitional phase where health signals may not yet be fully established.
- **stopped + unhealthy**: inactive runtime with unresolved critical conditions.

As a rule, read them together:
1. Confirm state in **status**.
2. Confirm confidence in **health**.
3. Use **introspection** to understand *why* the first two look the way they do.
