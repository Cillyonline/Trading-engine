# Purpose of an Analyst Run
An analyst run produces deterministic results by executing the trading engine against a fixed snapshot of inputs, yielding signals and results that can be inspected and reasoned about without variability.

# Terminology
- Snapshot: An immutable capture of all input data and configuration required for a run.
- Run: A single execution of the engine using a snapshot.
- Signal: A discrete output emitted by the run that represents the engine’s computed decision data.
- Result: The structured outcome set produced by the run, including signals and their associated metadata.
- Deterministic: The property that the same snapshot produces the same results on every run.

# Preconditions
A snapshot exists and is complete, containing all input data and configuration required for execution. Deterministic behavior is assumed for the engine and its dependencies when operating on the snapshot.

# Define Analysis Run
An analysis run is defined by binding the run to a specific snapshot. This definition establishes the exact input state that will be used during execution.

# Execute Run
The engine executes the run strictly against the bound snapshot. No inputs outside the snapshot are consulted, and no mutable state alters the execution path.

# Fetch Signals
Signals produced by the run are retrieved from the run’s results. The signals reflect the deterministic outputs computed from the snapshot.

# Inspect Results
The results are inspected as the authoritative record of the run. They include the signals and any metadata produced by the engine during execution.

# Reason About Output
Reasoning about the output is based solely on the snapshot and the deterministic run semantics. Identical snapshots yield identical signals and results, enabling consistent interpretation.

# Guarantees
The engine guarantees snapshot-first execution and deterministic results for a run bound to a snapshot. Signals and results are reproducible for the same snapshot.

# Non-Goals
The workflow does not cover live trading, broker integrations, backtesting, or AI-based decision logic.
