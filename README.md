# RateScript

Compiles a plain-language tariff into an immutable, validator-checked tier formula, then calculates exact usage quotes in cents.

## Why this is an intelligent contract

A namespaced formula registry and deterministic tier calculator; no bids, approvals, or payments. The source interpretation runs inside GenLayer consensus; the stored result and read methods are on-chain.

## Scope

The tariff text is user-supplied. The contract checks its extraction and arithmetic, not whether the tariff is legally binding.

## Verify

```powershell
python -m pip install -r requirements.txt
genvm-lint check contracts/rate_script.py
genvm-lint typecheck contracts/rate_script.py
pytest tests/direct -q
gltest tests/integration/test_studionet.py --network studionet -v -s
```

Live tests submit permanent public StudioNet test transactions; use a fresh test wallet. See EVIDENCE.md for the completed run and explorer links.
