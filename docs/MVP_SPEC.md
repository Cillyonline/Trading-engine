# MVP_SPEC.md
## Cilly Trading Engine – MVP v1

> Status: Context Only  
> This document defines PRODUCT SCOPE AND EXCLUSIONS only.  
> It is NOT an operational, workflow, or implementation document.

---

## 1. Purpose of this Document

This MVP specification exists to provide a stable product anchor.

It answers:
- What this project fundamentally is
- What it explicitly is NOT
- What the intended direction is

All operational decisions are made via:
- GitHub Issues
- Engineering Workflow
- Architectural Review Gate

---

## 2. Product Definition

The Cilly Trading Engine MVP is a:

**Deterministic, modular trading analysis engine**
designed to power a **website-based trading analysis tool**.

The MVP focuses on:
- Market data ingestion
- Indicator calculation
- Strategy-based signal generation
- Signal persistence
- API-based access for frontend consumption

The system is designed for **analysis and decision support**, not execution.

---

## 3. Included in MVP v1

- Deterministic strategies (e.g. RSI2, Turtle)
- Modular engine architecture
- Clear separation of:
  - data layer
  - indicators
  - strategies
  - persistence
  - API
- Signal generation and storage
- Robust error isolation per symbol / strategy
- SQLite-based persistence (MVP scale)
- FastAPI-based API layer

---

## 4. Explicitly Excluded from MVP v1

The following are NOT part of the MVP:

- Live trading
- Broker integrations
- Order execution
- Portfolio management
- Backtesting frameworks
- Strategy optimization
- AI-based signal generation
- Fully automated decision-making

Any inclusion of the above requires:
- A separate Epic
- Explicit scope discussion
- Potential MVP version increment

---

## 5. Intended Usage

The MVP is intended to be used as:

- A backend service for a trading analysis website
- A signal exploration and screening tool
- A foundation for future, clearly scoped extensions

It is NOT intended to:
- Trade autonomously
- Replace professional risk management
- Guarantee profitable outcomes

---

## 6. Relationship to Other Documents

This document:
- Provides context to Codex A (Architect)
- Anchors scope discussions
- Prevents long-term drift

This document does NOT:
- Define tasks
- Define acceptance criteria
- Define workflows
- Override GitHub Issues

---

## 7. Change Policy

This document should be changed ONLY if:
- The fundamental product direction changes
- MVP boundaries are redefined

Such changes require:
- A new Epic
- Explicit discussion before implementation
