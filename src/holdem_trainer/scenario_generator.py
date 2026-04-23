from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from .cards import draw_cards, shuffle_deck
from .models import Card, Position, Street
from .recommendation_engine import TrainingRecommendation, recommend_action

PLAYER_COUNT_CHOICES = (2, 3, 4, 5, 6)
TABLE_COUNT_CHOICES = (6, 6, 6, 9)
POSITIONS = (Position.UTG, Position.HJ, Position.CO, Position.BTN, Position.SB, Position.BB)
STREETS = (Street.FLOP, Street.TURN, Street.RIVER)
POT_SIZES = (30.0, 45.0, 60.0, 75.0, 90.0, 120.0, 150.0)
BET_FRACTIONS = (0.33, 0.5, 0.66, 0.75, 1.0)


@dataclass(frozen=True)
class TrainingScenario:
    street: Street
    hero_hand: tuple[Card, Card]
    board: tuple[Card, ...]
    players_at_table: int
    players_in_hand: int
    position: Position
    pot_size: float
    facing_bet: float
    effective_stack: float
    seed_tags: tuple[str, ...] = field(default_factory=tuple)
    analysis: TrainingRecommendation | None = None


class ScenarioEngine:
    def __init__(self, seed: int | None = None) -> None:
        self._random = Random(seed)

    def next_scenario(self) -> TrainingScenario:
        for _ in range(24):
            scenario = self._build_scenario()
            if scenario.analysis is not None:
                return scenario
        return self._build_scenario()

    def _build_scenario(self) -> TrainingScenario:
        street = self._random.choice(STREETS)
        players_in_hand = self._random.choice(PLAYER_COUNT_CHOICES)
        players_at_table = max(players_in_hand, self._random.choice(TABLE_COUNT_CHOICES))
        position = self._random.choice(POSITIONS)
        pot_size = self._random.choice(POT_SIZES)
        facing_bet = self._rounded_bet(pot_size, self._random.choice(BET_FRACTIONS))
        effective_stack = max(120.0, round((pot_size + facing_bet) * self._random.uniform(3.0, 7.0)))

        deck = shuffle_deck(seed=self._random.randrange(1_000_000_000))
        hero_hand, deck = draw_cards(deck, 2)
        board, _ = draw_cards(deck, _board_size_for_street(street))

        seed_tags = self._seed_tags(street, players_in_hand, facing_bet, pot_size)
        analysis = recommend_action(
            street=street,
            hero_hand=hero_hand,
            board=board,
            players_at_table=players_at_table,
            players_in_hand=players_in_hand,
            position=position,
            pot_size=pot_size,
            facing_bet=facing_bet,
            effective_stack=effective_stack,
            seed_tags=seed_tags,
        )
        return TrainingScenario(
            street=street,
            hero_hand=hero_hand,
            board=board,
            players_at_table=players_at_table,
            players_in_hand=players_in_hand,
            position=position,
            pot_size=pot_size,
            facing_bet=facing_bet,
            effective_stack=effective_stack,
            seed_tags=seed_tags,
            analysis=analysis,
        )

    def _rounded_bet(self, pot_size: float, bet_fraction: float) -> float:
        return round(max(5.0, pot_size * bet_fraction) / 5.0) * 5.0

    def _seed_tags(
        self,
        street: Street,
        players_in_hand: int,
        facing_bet: float,
        pot_size: float,
    ) -> tuple[str, ...]:
        tags = [street.value]
        tags.append("heads_up" if players_in_hand == 2 else "multiway")
        tags.append("small_bet" if facing_bet <= pot_size * 0.5 else "large_bet")
        return tuple(tags)


def _board_size_for_street(street: Street) -> int:
    if street == Street.FLOP:
        return 3
    if street == Street.TURN:
        return 4
    return 5
