from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cards import parse_cards
from .hand_evaluator import evaluate_best_hand, summarize_draws
from .models import (
    Action,
    Card,
    DrawSummary,
    HandCategory,
    HandEvaluation,
    Position,
    Scenario as DomainScenario,
    Street,
)
from .pot_odds import calculate_break_even_equity

POSITION_ALIASES = {
    "utg": Position.UTG,
    "hj": Position.HJ,
    "co": Position.CO,
    "cutoff": Position.CO,
    "btn": Position.BTN,
    "button": Position.BTN,
    "sb": Position.SB,
    "small_blind": Position.SB,
    "bb": Position.BB,
    "big_blind": Position.BB,
}

STREET_ALIASES = {
    "preflop": Street.PREFLOP,
    "flop": Street.FLOP,
    "turn": Street.TURN,
    "river": Street.RIVER,
}


@dataclass(frozen=True)
class TrainingRecommendation:
    correct_action: Action
    accepted_actions: tuple[Action, ...]
    reason_codes: tuple[str, ...]
    explanation: str
    difficulty: str
    hand_evaluation: HandEvaluation
    draw_summary: DrawSummary
    break_even_equity: float
    estimated_equity: float


def recommend_action(scenario: Any | None = None, **scenario_fields: Any) -> TrainingRecommendation:
    domain_scenario = _coerce_scenario(scenario, scenario_fields)
    hand_evaluation = evaluate_best_hand(domain_scenario.hero_cards + domain_scenario.board_cards)
    draw_summary = summarize_draws(domain_scenario.hero_cards, domain_scenario.board_cards)
    break_even_equity = calculate_break_even_equity(domain_scenario.pot_size, domain_scenario.call_amount)
    estimated_equity = _estimate_equity(domain_scenario, hand_evaluation, draw_summary)
    equity_margin = estimated_equity - break_even_equity

    correct_action, accepted_actions, reason_codes = _select_action(
        domain_scenario,
        hand_evaluation,
        draw_summary,
        equity_margin,
    )
    explanation = _build_explanation(
        domain_scenario,
        hand_evaluation,
        draw_summary,
        estimated_equity,
        break_even_equity,
        correct_action,
    )

    return TrainingRecommendation(
        correct_action=correct_action,
        accepted_actions=accepted_actions,
        reason_codes=reason_codes,
        explanation=explanation,
        difficulty=_difficulty_label(equity_margin),
        hand_evaluation=hand_evaluation,
        draw_summary=draw_summary,
        break_even_equity=break_even_equity,
        estimated_equity=estimated_equity,
    )


def _coerce_scenario(scenario: Any | None, scenario_fields: dict[str, Any]) -> DomainScenario:
    if isinstance(scenario, DomainScenario):
        return scenario

    payload = _scenario_payload(scenario, scenario_fields)
    hero_cards = _coerce_cards(payload["hero_hand"])
    board_cards = _coerce_cards(payload["board"])
    street = _coerce_street(payload.get("street", "flop"))
    players_in_hand = int(payload.get("players_in_hand", 2))
    players_at_table = int(payload.get("players_at_table", players_in_hand))
    position = _coerce_position(payload.get("position", "btn"))
    pot_size = float(payload.get("pot_size", 0.0))
    facing_bet = float(payload.get("facing_bet", payload.get("call_amount", 0.0)))
    effective_stack = float(payload.get("effective_stack", max(100.0, pot_size + facing_bet)))
    seed_tags = tuple(str(tag) for tag in payload.get("seed_tags", ()))

    return DomainScenario(
        street=street,
        hero_cards=hero_cards,
        board_cards=board_cards,
        players_at_table=players_at_table,
        players_in_hand=players_in_hand,
        position=position,
        pot_size=pot_size,
        call_amount=facing_bet,
        effective_stack=effective_stack,
        seed_tags=seed_tags,
    )


def _scenario_payload(scenario: Any | None, scenario_fields: dict[str, Any]) -> dict[str, Any]:
    if isinstance(scenario, dict):
        return scenario
    if scenario is None:
        return scenario_fields
    payload = {
        "street": getattr(scenario, "street", "flop"),
        "hero_hand": getattr(scenario, "hero_hand", getattr(scenario, "hero_cards", ())),
        "board": getattr(scenario, "board", getattr(scenario, "board_cards", ())),
        "players_at_table": getattr(scenario, "players_at_table", 2),
        "players_in_hand": getattr(scenario, "players_in_hand", 2),
        "position": getattr(scenario, "position", "btn"),
        "pot_size": getattr(scenario, "pot_size", 0.0),
        "facing_bet": getattr(scenario, "facing_bet", getattr(scenario, "call_amount", 0.0)),
        "effective_stack": getattr(scenario, "effective_stack", 100.0),
        "seed_tags": getattr(scenario, "seed_tags", ()),
    }
    payload.update(scenario_fields)
    return payload


def _coerce_cards(cards: Any) -> tuple[Card, ...]:
    if cards and isinstance(cards[0], Card):
        return tuple(cards)
    return parse_cards(cards)


def _coerce_street(street_value: Any) -> Street:
    if isinstance(street_value, Street):
        return street_value
    return STREET_ALIASES[str(street_value).lower()]


def _coerce_position(position_value: Any) -> Position:
    if isinstance(position_value, Position):
        return position_value
    return POSITION_ALIASES[str(position_value).lower()]


def _estimate_equity(
    scenario: DomainScenario,
    hand_evaluation: HandEvaluation,
    draw_summary: DrawSummary,
) -> float:
    made_hand_equity = _made_hand_equity(scenario, hand_evaluation)
    draw_equity = _draw_equity(scenario, draw_summary)
    position_adjustment = 0.02 if scenario.position in {Position.CO, Position.BTN} else -0.01 if scenario.position in {Position.SB, Position.BB} else 0.0
    player_penalty = 0.03 * max(0, scenario.players_in_hand - 2)
    estimated_equity = max(made_hand_equity, made_hand_equity + draw_equity * 0.6)
    return max(0.02, min(0.98, estimated_equity + position_adjustment - player_penalty))


def _made_hand_equity(scenario: DomainScenario, hand_evaluation: HandEvaluation) -> float:
    category = hand_evaluation.category
    if category == HandCategory.STRAIGHT_FLUSH:
        return 0.99
    if category == HandCategory.FOUR_OF_A_KIND:
        return 0.97
    if category == HandCategory.FULL_HOUSE:
        return 0.95
    if category == HandCategory.FLUSH:
        return 0.83
    if category == HandCategory.STRAIGHT:
        return 0.78
    if category == HandCategory.THREE_OF_A_KIND:
        return 0.68
    if category == HandCategory.TWO_PAIR:
        return 0.58
    if category == HandCategory.ONE_PAIR:
        return 0.44 if _is_top_pair_or_better(scenario) else 0.30
    return 0.11


def _is_top_pair_or_better(scenario: DomainScenario) -> bool:
    board_ranks = sorted((card.rank.value for card in scenario.board_cards), reverse=True)
    hero_ranks = {card.rank.value for card in scenario.hero_cards}
    if len({card.rank for card in scenario.hero_cards}) == 1 and scenario.hero_cards[0].rank.value > board_ranks[0]:
        return True
    return bool(hero_ranks.intersection(board_ranks[:1]))


def _draw_equity(scenario: DomainScenario, draw_summary: DrawSummary) -> float:
    outs = draw_summary.straight_draw_outs
    if draw_summary.flush_draw:
        outs += 9
        if draw_summary.straight_draw_outs:
            outs -= 2
    if outs <= 0:
        return 0.0
    if scenario.street == Street.FLOP:
        return 1 - ((47 - outs) / 47) * ((46 - outs) / 46)
    if scenario.street == Street.TURN:
        return outs / 46
    return 0.0


def _select_action(
    scenario: DomainScenario,
    hand_evaluation: HandEvaluation,
    draw_summary: DrawSummary,
    equity_margin: float,
) -> tuple[Action, tuple[Action, ...], tuple[str, ...]]:
    if hand_evaluation.category >= HandCategory.FULL_HOUSE:
        return Action.RAISE_LARGE, (Action.RAISE_SMALL, Action.RAISE_LARGE), ("VALUE_EDGE", "NUT_ADVANTAGE")
    if hand_evaluation.category >= HandCategory.STRAIGHT or hand_evaluation.category == HandCategory.THREE_OF_A_KIND:
        return Action.RAISE_SMALL, (Action.CALL, Action.RAISE_SMALL), ("VALUE_EDGE",)
    if equity_margin >= 0.12:
        return Action.RAISE_SMALL, (Action.CALL, Action.RAISE_SMALL), ("VALUE_EDGE", "PRESSURE")
    if equity_margin >= 0.0:
        if draw_summary.flush_draw or draw_summary.straight_draw_outs:
            return Action.CALL, (Action.CALL,), ("POT_ODDS", "DRAW_CONTINUE")
        return Action.CALL, (Action.CALL,), ("SHOWDOWN_VALUE",)
    return Action.FOLD, (Action.FOLD,), ("PRICE_TOO_HIGH",)


def _build_explanation(
    scenario: DomainScenario,
    hand_evaluation: HandEvaluation,
    draw_summary: DrawSummary,
    estimated_equity: float,
    break_even_equity: float,
    correct_action: Action,
) -> str:
    draw_text = "no major draw"
    if draw_summary.combo_draw:
        draw_text = "combo draw"
    elif draw_summary.flush_draw:
        draw_text = "flush draw"
    elif draw_summary.straight_draw_outs:
        draw_text = str(draw_summary.straight_draw).replace("_", " ")

    return (
        f"{str(correct_action).replace('_', ' ').title()} is best because your hand is {hand_evaluation.label.lower()} "
        f"with {draw_text}. Estimated equity is about {estimated_equity:.0%} against a required {break_even_equity:.0%}. "
        f"The app uses simple pot-odds and hand-strength heuristics for training spots, not full GTO ranges."
    )


def _difficulty_label(equity_margin: float) -> str:
    absolute_margin = abs(equity_margin)
    if absolute_margin >= 0.20:
        return "Easy"
    if absolute_margin >= 0.10:
        return "Medium"
    return "Hard"
