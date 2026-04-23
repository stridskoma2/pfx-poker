# Texas Hold'em Card And Pot Odds Trainer

A desktop practice app for postflop Texas Hold'em spots built with [Dear PyGui](https://github.com/hoffstadt/DearPyGui).

The app deals a random hero hand, a random flop/turn/river board, a player count, and a bet to face. You choose the best action from multiple-choice options, then the app explains the recommendation using pot odds, hand strength, draw strength, and table context.

This first version is a training heuristic tool. It is not a GTO solver and it does not model opponent ranges in detail.

## Features

- Random postflop quiz spots
- Multiple-choice action selection
- Pot-odds and equity-based explanations
- Score tracking
- Deterministic tests for core poker logic

## Run

```powershell
python -m pip install -e .
python -m holdem_trainer.main
```

## Test

```powershell
python -m pytest -q -p no:cacheprovider
```

## Clean Code Snapshot

- Before: the repository had no application code, no module boundaries, and no tests.
- After: the project is split into typed domain logic, recommendation logic, UI wiring, and focused tests.
- Rules applied: `N1`, `F1`, `F3`, `G12`, `G25`, `G30`, `P3`, `T1`, `T5`.
