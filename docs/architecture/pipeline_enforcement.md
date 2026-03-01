# Pipeline Enforcement Architecture

## Purpose
Phase 27b defines the structural enforcement layer for the trading pipeline. It exists to ensure execution access is controlled by one canonical orchestration path, not by distributed or ad hoc calls across modules. The architecture must enforce that execution happens only after upstream pipeline stages complete, including mandatory Risk Gate evaluation from Phase 27.

## Canonical Pipeline
The system must treat the following sequence as the only canonical pipeline:

**Trigger → Analysis → Signal → Risk Gate → Execution Adapter → Journal**

Each stage must be traversed in order. Stages must not be skipped, reordered, or duplicated through side entrypoints.

## Architectural Position
The central orchestrator sits above and between pipeline stages as the sole coordination authority for pipeline flow.

The orchestrator owns:
- Stage sequencing and transition control across the canonical pipeline.
- Invocation of Risk Gate before any execution access.
- The only permitted call path to the Execution Adapter.
- End-to-end pipeline integrity from Trigger through Journal.

The orchestrator must not be optional. Any execution-capable flow must be routed through it.

## Enforcement Boundary
The architecture defines a hard structural boundary around execution access:
- Execution modules must be unreachable from any module that is not the orchestrator.
- Any path that reaches execution without orchestration is invalid by definition.
- Risk decisions must be checked before execution is invoked, consistent with the Phase 27 Risk Gate contract.

This boundary is structural and mandatory, independent of runtime environment.

## Allowed Dependencies
High-level allowed dependency directions are:
- Trigger layer may depend on Analysis interfaces.
- Analysis layer may depend on Signal interfaces.
- Signal layer may depend on Risk Gate interfaces.
- Orchestrator may depend on Trigger, Analysis, Signal, Risk Gate, Execution Adapter, and Journal interfaces.
- Execution Adapter may depend on execution provider integrations.
- Journal layer may depend on persisted output/logging interfaces.

No dependency direction may create an alternate execution path outside the orchestrator.

## Prohibited Dependencies
The following are prohibited:
- Direct imports of execution modules from any module outside the orchestrator.
- Any alternative execution entrypoint that bypasses the orchestrator.
- Any dependency edge that enables execution invocation prior to Risk Gate evaluation.

## Governance Enforcement Rule
Enforcement is mandatory under repository governance:
- No module may call execution directly outside orchestrator-controlled flow.
- Pull requests that introduce direct execution imports outside orchestrator scope must be blocked.
- Pull requests that introduce execution bypass entrypoints must be blocked.

## Non-Goals
This document does not define or change:
- Orchestrator runtime implementation details.
- Lifecycle governance expansion beyond this boundary rule.
- Portfolio construction or portfolio management logic.
- Journal redesign or schema redesign.
- Live trading behavior or broker integration.
- Backtesting behavior.
