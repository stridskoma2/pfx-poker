from __future__ import annotations


def calculate_break_even_equity(pot_size: float, call_amount: float) -> float:
    _validate_non_negative_number(pot_size, "pot_size")
    _validate_non_negative_number(call_amount, "call_amount")
    if call_amount == 0:
        return 0.0
    return call_amount / (pot_size + call_amount)


def calculate_pot_odds_ratio(pot_size: float, call_amount: float) -> float | None:
    _validate_non_negative_number(pot_size, "pot_size")
    _validate_non_negative_number(call_amount, "call_amount")
    if call_amount == 0:
        return None
    return pot_size / call_amount


def _validate_non_negative_number(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
