# P18-EXT-CLIENTS: External Client Types and Trust Boundaries

## 1) Purpose
This document defines external client types and trust boundaries for **Phase 18 (P18-EXT-CLIENTS)**.

It exists to align documentation and integration expectations only. **This is documentation-only guidance and has no runtime impact.**

## 2) Definitions
- **External Client**: Any actor outside engine internals that interacts with exposed, documented integration layers.
- **Engine Internals**: Core implementation details, internal modules, and internal data/control flow not documented as external contracts.
- **Trust Boundary**: The conceptual line separating engine internals from external clients and their inputs/requests.
- **Read-Only Operation**: An interaction that retrieves information without changing engine state.
- **State-Affecting Operation**: An interaction that creates, updates, deletes, triggers, or otherwise changes engine state.

## 3) External Client Categories
- **CLI Consumer (human operator)**
  - A person invoking documented command-line entry points.
  - Boundary note: limited to documented CLI behavior and outputs; internal command wiring is not part of contract.

- **Programmatic API Consumer (external application/service)**
  - A non-human caller using documented API-facing integration points.
  - Boundary note: only documented request/response behavior is supported; internal models and execution paths are not.

- **Batch / Automation Consumer (scheduled/orchestrated invocations)**
  - Automated jobs or schedulers invoking documented interfaces on a schedule or workflow trigger.
  - Boundary note: contract applies to declared inputs/outputs only; internal scheduling assumptions are out of scope.

- **Tooling outside engine core (internal-but-external)**
  - Supporting tools maintained outside core runtime that consume documented engine interfaces.
  - Boundary note: organizational proximity does not remove boundary; internals remain non-contract.

## 4) Trust Boundary Definition
The trust boundary is between:
- **Inside**: engine internals (implementation details, internal state handling, and non-documented behavior).
- **Outside**: all external clients (human, programmatic, automated, and external tooling).

Only **documented contracts** are supported across this boundary. Engine internals are explicitly **not** part of the public contract and may change without external compatibility guarantees beyond documented contracts.

## 5) Read-Only vs State-Affecting Classification
Classification is performed at the **operation level**, not only by client type.

| Operation Example | Classification | Notes |
|---|---|---|
| Request status/health/summary data | Read-Only | Returns information only. |
| Query historical records/report output | Read-Only | No state mutation. |
| Submit execution command/job/action | State-Affecting | Initiates or changes internal processing/state. |
| Update or remove persisted configuration/data via documented interface | State-Affecting | Mutates stored state. |

A single client type may perform both classes of operations depending on the specific interaction.

## 6) Supported Integration Layers (High-Level)
Supported integration is defined only at a high level:
- **CLI layer**: documented command-line interactions.
- **API layer**: documented programmatic request/response interactions.
- **File-based / batch layer**: documented batch-oriented inputs/outputs and automation-facing invocation surfaces.

No protocol-level or implementation-level details are defined in this document.

## 7) Explicit Non-goals
The following are out of scope for this document:
- Authentication
- Authorization
- Security enforcement frameworks
- Broker integrations
- Live trading
- Runtime modifications
- Changing API surface
