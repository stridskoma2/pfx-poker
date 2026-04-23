from __future__ import annotations

import importlib
import inspect
import re
import sys
from pathlib import Path
from typing import Any

import pytest


CARD_PATTERN = re.compile(r"^[2-9TJQKA][cdhs]$", re.IGNORECASE)
BOARD_SIZE_BY_STREET = {
    "preflop": 0,
    "flop": 3,
    "turn": 4,
    "river": 5,
}


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


def _create_engine(seed: int) -> Any:
    scenario_engine_type = _load_symbol("holdem_trainer.scenario_generator", "ScenarioEngine")
    signature = inspect.signature(scenario_engine_type)
    parameter_names = list(signature.parameters)

    if "seed" in parameter_names:
        return scenario_engine_type(seed=seed)
    if "random_seed" in parameter_names:
        return scenario_engine_type(random_seed=seed)
    if len(parameter_names) == 1:
        return scenario_engine_type(seed)
    if len(parameter_names) == 0:
        return scenario_engine_type()

    pytest.fail("Unsupported ScenarioEngine constructor signature.")


def _get_field(container: Any, field_name: str) -> Any:
    if isinstance(container, dict):
        return container[field_name]
    if hasattr(container, field_name):
        return getattr(container, field_name)
    pytest.fail(f"Scenario is missing field '{field_name}'.")


def _serialize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _serialize_value(inner_value) for key, inner_value in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    if hasattr(value, "name"):
        return str(value.name)
    if hasattr(value, "value"):
        return str(value.value)
    return value


def _serialize_card(card: Any) -> str:
    serialized = _serialize_value(card)
    return str(serialized)


def _scenario_snapshot(scenario: Any) -> dict[str, Any]:
    field_names = (
        "street",
        "hero_hand",
        "board",
        "players_at_table",
        "players_in_hand",
        "position",
        "pot_size",
        "facing_bet",
        "effective_stack",
    )
    return {
        field_name: _serialize_value(_get_field(scenario, field_name))
        for field_name in field_names
    }


def _next_scenario(engine: Any) -> Any:
    if not hasattr(engine, "next_scenario"):
        pytest.fail("ScenarioEngine must expose next_scenario().")
    return engine.next_scenario()


def test_next_scenario_is_repeatable_for_the_same_seed() -> None:
    left_engine = _create_engine(seed=17)
    right_engine = _create_engine(seed=17)

    left_snapshots = [_scenario_snapshot(_next_scenario(left_engine)) for _ in range(3)]
    right_snapshots = [_scenario_snapshot(_next_scenario(right_engine)) for _ in range(3)]

    assert left_snapshots == right_snapshots


def test_next_scenario_deals_unique_cards_to_hero_and_board() -> None:
    engine = _create_engine(seed=31)
    scenario = _next_scenario(engine)

    hero_hand = [_serialize_card(card) for card in _get_field(scenario, "hero_hand")]
    board = [_serialize_card(card) for card in _get_field(scenario, "board")]
    cards = [*hero_hand, *board]

    assert len(cards) == len(set(cards))
    assert all(CARD_PATTERN.match(card) for card in cards)


def test_next_scenario_matches_board_size_to_street() -> None:
    engine = _create_engine(seed=53)
    scenario = _next_scenario(engine)

    street = str(_serialize_value(_get_field(scenario, "street"))).lower()
    board = list(_get_field(scenario, "board"))

    assert street in BOARD_SIZE_BY_STREET
    assert len(board) == BOARD_SIZE_BY_STREET[street]


def test_next_scenario_returns_quiz_ready_training_fields() -> None:
    engine = _create_engine(seed=79)
    scenario = _next_scenario(engine)

    hero_hand = [_serialize_card(card) for card in _get_field(scenario, "hero_hand")]
    players_at_table = int(_get_field(scenario, "players_at_table"))
    players_in_hand = int(_get_field(scenario, "players_in_hand"))
    pot_size = float(_get_field(scenario, "pot_size"))
    facing_bet = float(_get_field(scenario, "facing_bet"))

    assert len(hero_hand) == 2
    assert players_at_table >= players_in_hand >= 2
    assert pot_size >= 0
    assert facing_bet >= 0
