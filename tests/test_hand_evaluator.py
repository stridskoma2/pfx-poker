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


def _call_evaluate_best_hand(hero_hand: list[str], board: list[str]) -> Any:
    evaluate_best_hand = _load_symbol("holdem_trainer.hand_evaluator", "evaluate_best_hand")
    signature = inspect.signature(evaluate_best_hand)
    parameter_names = list(signature.parameters)
    all_cards = [*hero_hand, *board]

    if "cards" in parameter_names:
        return evaluate_best_hand(cards=all_cards)
    if {"hero_hand", "board"}.issubset(parameter_names):
        return evaluate_best_hand(hero_hand=hero_hand, board=board)
    if {"hero_cards", "board_cards"}.issubset(parameter_names):
        return evaluate_best_hand(hero_cards=hero_hand, board_cards=board)
    if len(parameter_names) == 1:
        return evaluate_best_hand(all_cards)
    if len(parameter_names) >= 2:
        return evaluate_best_hand(hero_hand, board)

    pytest.fail("Unsupported evaluate_best_hand signature.")


def _call_summarize_draws(hero_hand: list[str], board: list[str]) -> Any:
    summarize_draws = _load_symbol("holdem_trainer.hand_evaluator", "summarize_draws")
    signature = inspect.signature(summarize_draws)
    parameter_names = list(signature.parameters)
    all_cards = [*hero_hand, *board]

    if "cards" in parameter_names:
        return summarize_draws(cards=all_cards)
    if {"hero_hand", "board"}.issubset(parameter_names):
        return summarize_draws(hero_hand=hero_hand, board=board)
    if {"hero_cards", "board_cards"}.issubset(parameter_names):
        return summarize_draws(hero_cards=hero_hand, board_cards=board)
    if len(parameter_names) == 1:
        return summarize_draws(all_cards)
    if len(parameter_names) >= 2:
        return summarize_draws(hero_hand, board)

    pytest.fail("Unsupported summarize_draws signature.")


def _normalize_hand_category(result: Any) -> str:
    if isinstance(result, str):
        return result.lower()
    if isinstance(result, dict):
        for key in ("category", "hand_category", "rank_name", "hand_name"):
            if key in result:
                return str(result[key]).lower()
    for attribute_name in ("category", "hand_category", "rank_name", "hand_name"):
        if hasattr(result, attribute_name):
            return str(getattr(result, attribute_name)).lower()
    if hasattr(result, "name"):
        return str(result.name).lower()
    if hasattr(result, "value"):
        return str(result.value).lower()

    pytest.fail(f"Could not extract a hand category from {result!r}.")


def _normalize_draw_names(result: Any) -> set[str]:
    if isinstance(result, str):
        return {result.lower()}
    if isinstance(result, dict):
        if "draws" in result:
            return _normalize_draw_names(result["draws"])
        return {
            key.lower()
            for key, value in result.items()
            if isinstance(value, bool) and value
        }
    if isinstance(result, (list, tuple, set)):
        normalized: set[str] = set()
        for item in result:
            if isinstance(item, str):
                normalized.add(item.lower())
            elif hasattr(item, "name"):
                normalized.add(str(item.name).lower())
            elif hasattr(item, "value"):
                normalized.add(str(item.value).lower())
            else:
                normalized.add(str(item).lower())
        return normalized

    for attribute_name in ("draws", "active_draws"):
        if hasattr(result, attribute_name):
            return _normalize_draw_names(getattr(result, attribute_name))

    return {
        attribute_name.lower()
        for attribute_name in dir(result)
        if not attribute_name.startswith("_") and isinstance(getattr(result, attribute_name), bool) and getattr(result, attribute_name)
    }


def test_evaluate_best_hand_identifies_wheel_straight() -> None:
    result = _call_evaluate_best_hand(
        hero_hand=["Ah", "2d"],
        board=["3s", "4c", "5h", "Kd", "9c"],
    )

    assert "straight" in _normalize_hand_category(result)


def test_evaluate_best_hand_prefers_full_house_on_paired_board() -> None:
    result = _call_evaluate_best_hand(
        hero_hand=["Ah", "Ad"],
        board=["As", "Kh", "Kd", "2c", "7d"],
    )

    category = _normalize_hand_category(result)
    assert "full" in category
    assert "house" in category


def test_evaluate_best_hand_identifies_flush_from_seven_cards() -> None:
    result = _call_evaluate_best_hand(
        hero_hand=["Ah", "7h"],
        board=["Kh", "2h", "9h", "4c", "Jd"],
    )

    assert "flush" in _normalize_hand_category(result)


def test_summarize_draws_detects_combo_draw_on_the_flop() -> None:
    result = _call_summarize_draws(
        hero_hand=["8h", "7h"],
        board=["9h", "6h", "Kc"],
    )

    draw_names = _normalize_draw_names(result)
    assert any("flush" in draw_name for draw_name in draw_names)
    assert any(
        "open" in draw_name or "straight" in draw_name
        for draw_name in draw_names
    )
