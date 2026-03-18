# Determinism Audit Note

- Date: 2026-02-11
- Issue: #309
- Finding: `src/cilly_trading/smoke_run.py` did not provide a `__main__` entry point, so `python -m cilly_trading.smoke_run` imported the module and exited without executing the smoke-run contract. Determinism verification was therefore not provable through module execution.
- Fix: Added a module `main()` entry point with `if __name__ == "__main__": raise SystemExit(main())`, and added a deterministic test that runs the module twice, verifies the four smoke-run stdout markers, and compares `artifacts/smoke-run/result.json` bytes across runs.
