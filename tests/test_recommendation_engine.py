from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path
from typing import Any

import pytest


def _ensure_src_on_path() -> None:
    src_path = Path(__file__).resolve().parents[1] / "src"
    src_text = str(src_path)
    if src_path.exists() and src_text not in sys.path:
        sys.path.insert(0, src_text)


def _load_symbol(module_name: str, symbol_name: str) -> Any:
    _ensure_src_on_path()
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        pytest.fail(f"Expected module '{module_name}' to exist for these tests: {error}")

    if not hasattr(module, symbol_name):
        pytest.fail(f"Expected symbol '{symbol_name}' in module '{module_name}'.")

    return getattr(module, symbol_name)


def _call_calculate_break_even_equity(pot_size: float, call_amount: float) -> float:
    calculate_break_even_equity = _load_symbol(
        "holdem_trainer.recommendation_engine",
        "calculate_break_even_equity",
    )
    signature = inspect.signature(calculate_break_even_equity)
    parameter_names = list(signature.parameters)

    if {"pot_size", "call_amount"}.issubset(parameter_names):
        return float(calculate_break_even_equity(pot_size=pot_size, call_amount=call_amount))
    if {"pot_size", "facing_bet"}.issubset(parameter_names):
        return float(calculate_break_even_equity(pot_size=pot_size, facing_bet=call_amount))
    if {"pot", "call"}.issubset(parameter_names):
        return float(calculate_break_even_equity(pot=pot_size, call=call_amount))
    if len(parameter_names) == 2:
        return float(calculate_break_even_equity(pot_size, call_amount))

    pytest.fail("Unsupported calculate_break_even_equity signature.")


def _build_scenario_input(scenario_fields: dict[str, Any]) -> Any:
    _ensure_src_on_path()
    try:
        module = importlib.import_module("holdem_trainer.recommendation_engine")
    except ModuleNotFoundError:
        return scenario_fields

    if not hasattr(module, "Scenario"):
        return scenario_fields

    scenario_type = getattr(module, "Scenario")
    if not inspect.isclass(scenario_type):
        return scenario_fields

    signature = inspect.signature(scenario_type)
    accepted_fields = {
        name: value
        for name, value in scenario_fields.items()
        if name in signature.parameters
    }
    return scenario_type(**accepted_fields)


def _call_recommend_action(scenario_fields: dict[str, Any]) -> Any:
    recommend_action = _load_symbol("holdem_trainer.recommendation_engine", "recommend_action")
    scenario_input = _build_scenario_input(scenario_fields)
    signature = inspect.signature(recommend_action)
    parameter_names = list(signature.parameters)

    if len(parameter_names) == 1:
        return recommend_action(scenario_input)
    if {"scenario"}.issubset(parameter_names):
        return recommend_action(scenario=scenario_input)
    if set(scenario_fields).issuperset(parameter_names):
        filtered_fields = {name: scenario_fields[name] for name in parameter_names}
        return recommend_action(**filtered_fields)
    if {"hero_hand", "board"}.issubset(parameter_names):
        filtered_fields = {
            name: value
            for name, value in scenario_fields.items()
            if name in parameter_names
        }
        return recommend_action(**filtered_fields)

    pytest.fail("Unsupported recommend_action signature.")


def _normalize_action_name(result: Any) -> str:
    if isinstance(result, str):
        return result.lower()
    if isinstance(result, dict):
        for key in ("kind", "action", "recommended_action", "correct_action"):
            if key in result:
                return str(result[key]).lower()
    for attribute_name in ("kind", "action", "recommended_action", "correct_action"):
        if hasattr(result, attribute_name):
            return str(getattr(result, attribute_name)).lower()
    if hasattr(result, "name"):
        return str(result.name).lower()
    if hasattr(result, "value"):
        return str(result.value).lower()

    pytest.fail(f"Could not extract an action name from {result!r}.")


def test_calculate_break_even_equity_for_half_pot_bet() -> None:
    break_even_equity = _call_calculate_break_even_equity(pot_size=60, call_amount=30)

    assert break_even_equity == pytest.approx(1 / 3, rel=1e-3)


def test_calculate_break_even_equity_for_pot_size_bet() -> None:
    break_even_equity = _call_calculate_break_even_equity(pot_size=100, call_amount=100)

    assert break_even_equity == pytest.approx(0.5, rel=1e-3)


def test_recommend_action_raises_with_a_full_house_on_the_river() -> None:
    result = _call_recommend_action(
        {
            "street": "river",
            "hero_hand": ["Ah", "Ad"],
            "board": ["As", "Kh", "Kd", "2c", "7d"],
            "players_at_table": 6,
            "players_in_hand": 2,
            "position": "button",
            "pot_size": 120,
            "facing_bet": 40,
            "effective_stack": 320,
        }
    )

    assert "raise" in _normalize_action_name(result)


def test_recommend_action_calls_with_correct_price_for_turn_flush_draw() -> None:
    result = _call_recommend_action(
        {
            "street": "turn",
            "hero_hand": ["Ah", "5h"],
            "board": ["Kh", "8h", "2c", "Jd"],
            "players_at_table": 6,
            "players_in_hand": 2,
            "position": "button",
            "pot_size": 150,
            "facing_bet": 30,
            "effective_stack": 240,
        }
    )

    assert "call" in _normalize_action_name(result)


def test_recommend_action_folds_gutshot_when_price_is_too_high() -> None:
    result = _call_recommend_action(
        {
            "street": "turn",
            "hero_hand": ["Ah", "Kc"],
            "board": ["Qd", "Js", "2c", "9h"],
            "players_at_table": 6,
            "players_in_hand": 2,
            "position": "small_blind",
            "pot_size": 100,
            "facing_bet": 80,
            "effective_stack": 300,
        }
    )

    assert "fold" in _normalize_action_name(result)
