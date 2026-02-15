# Strategy Documentation Standard

## Purpose

This standard defines REQUIRED documentation rules for every strategy pack. All strategy documentation MUST be clear, deterministic, and governance-aligned. All requirements in this document are normative.

## Scope

IN SCOPE:
- Define REQUIRED `README.md` structure per strategy pack.
- Define REQUIRED parameter documentation.
- Define REQUIRED deterministic behavior explanation.
- Define REQUIRED risk disclosure section.
- Provide a REQUIRED template example.

OUT OF SCOPE:
- Strategy marketing language.
- Performance claims.
- Benchmark comparisons.

## Mandatory README Structure

A `README.md` file is REQUIRED for every strategy pack.

Every strategy pack `README.md` MUST include the following sections in this exact order:
1. `## Overview`
2. `## Strategy Objective`
3. `## Strategy Logic Summary`
4. `## Parameter Definitions`
5. `## Deterministic Behavior`
6. `## Risk Disclosure`
7. `## Version & Compatibility`
8. `## Change Log Reference`

Additional rules:
- All section headings listed above MUST use Markdown H2 (`##`).
- The required sections MUST appear in the defined order.
- Required sections MUST NOT be renamed.

## Parameter Documentation Requirements

Each parameter entry in `## Parameter Definitions` MUST include all of the following fields:
- Name
- Type
- Default value
- Allowed range or enum values
- Deterministic impact description
- Whether required or optional

Normative requirements:
- Undocumented parameters are forbidden.
- Implicit defaults are forbidden.
- Parameter order MUST be stable across documentation updates unless a documented version change requires reordering.
- Every documented parameter MUST map to actual strategy inputs and MUST NOT include unused placeholders in production strategy packs.

## Deterministic Behavior Explanation

Each strategy `README.md` MUST include a `## Deterministic Behavior` section that explains:
- All explicit inputs.
- All derived values.
- Absence of hidden state.
- Absence of randomness.
- Absence of time dependency.
- Absence of environment dependency.

The following statement is REQUIRED verbatim:

`This strategy produces identical outputs for identical inputs across environments.`

Normative prohibitions:
- Hidden state is forbidden.
- Randomized behavior is forbidden unless explicitly modeled as an input.
- Undocumented environment-dependent logic is forbidden.

## Risk Disclosure Requirements

Each strategy `README.md` MUST include a `## Risk Disclosure` section containing:
- Market risk explanation.
- Model risk explanation.
- Parameter sensitivity warning.

The section MUST include both explicit statements:
- No guarantee of performance.
- No future return prediction.

The following are prohibited in strategy documentation:
- Performance promises.
- Marketing claims.
- Benchmark comparison language.

## Governance Alignment

Governance requirements:
- Documentation changes affecting strategy logic MUST trigger a version bump.
- `README.md` MUST align with `metadata.yaml`.
- Inconsistency between documentation and metadata is forbidden.
- The pull request implementing this standard MUST include `Closes #369`.

## Template Example

```markdown
# <pack_name>

## Overview
Strategy pack identifier: `<strategy_id>`.

This README defines the required, deterministic, and risk-aware documentation for this strategy pack.

## Strategy Objective
Describe the objective in neutral terms.

Example placeholder:
- Objective: Define how the strategy transforms inputs into outputs without performance claims.

## Strategy Logic Summary
Describe the strategy logic at a high level.

Example placeholder:
1. Accept explicit inputs.
2. Compute derived values from explicit inputs.
3. Produce outputs using deterministic rules only.

## Parameter Definitions
| Name | Type | Default value | Allowed range or enum values | Deterministic impact description | Required or optional |
| --- | --- | --- | --- | --- | --- |
| `<parameter_name>` | `<type>` | `<default_value>` | `<allowed_values>` | `<deterministic_impact>` | `<required_or_optional>` |
| `<parameter_name_2>` | `<type>` | `<default_value>` | `<allowed_values>` | `<deterministic_impact>` | `<required_or_optional>` |

Parameter rules:
- Undocumented parameters are forbidden.
- Implicit defaults are forbidden.
- Parameter order is stable.

## Deterministic Behavior
Document all explicit inputs and derived values.

Required declaration:
`This strategy produces identical outputs for identical inputs across environments.`

Determinism checks:
- No hidden state.
- No randomness.
- No time dependency.
- No environment dependency.

## Risk Disclosure
This strategy documentation includes required risk disclosures.

Required disclosures:
- Market risk: Outcomes remain exposed to market conditions.
- Model risk: Rule design can be incomplete or misaligned with real-world behavior.
- Parameter sensitivity: Small parameter changes can materially alter outcomes.
- No guarantee of performance.
- No future return prediction.

Prohibited language:
- No performance promises.
- No marketing claims.
- No benchmark comparison language.

## Version & Compatibility
- Strategy version: `<version>`
- Compatible metadata schema: `<metadata_schema_version>`
- Compatibility notes: `<compatibility_notes>`

## Change Log Reference
Reference the authoritative changelog entry.

Example placeholder:
- See: `CHANGELOG.md` entry for `<version>`.
```

## Non-Goals

The following remain out of scope for this standard:
- Strategy marketing language.
- Performance claims.
- Benchmark comparisons.

FILES CHANGED: docs/strategy/documentation_standard.md

Acceptance Criteria Mapping:
- File exists → `# Strategy Documentation Standard`
- Required sections listed → `## Mandatory README Structure`
- Template included → `## Template Example`
- Governance alignment → `## Governance Alignment`
