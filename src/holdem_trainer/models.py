from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum


class Suit(str, Enum):
    CLUBS = "c"
    DIAMONDS = "d"
    HEARTS = "h"
    SPADES = "s"

    @property
    def short_name(self) -> str:
        return self.value.upper()

    def __str__(self) -> str:
        return self.value


class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @property
    def short_name(self) -> str:
        labels = {
            Rank.TEN: "T",
            Rank.JACK: "J",
            Rank.QUEEN: "Q",
            Rank.KING: "K",
            Rank.ACE: "A",
        }
        return labels.get(self, str(int(self)))

    def __str__(self) -> str:
        return self.short_name


class Street(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"

    def __str__(self) -> str:
        return self.value


class Position(str, Enum):
    UTG = "utg"
    HJ = "hj"
    CO = "co"
    BTN = "btn"
    SB = "sb"
    BB = "bb"

    def __str__(self) -> str:
        return self.value


class Action(str, Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET_SMALL = "bet_small"
    BET_LARGE = "bet_large"
    RAISE_SMALL = "raise_small"
    RAISE_LARGE = "raise_large"

    def __str__(self) -> str:
        return self.value


class HandCategory(IntEnum):
    HIGH_CARD = 0
    ONE_PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()

    def __str__(self) -> str:
        return self.label


class StraightDrawType(str, Enum):
    NONE = "none"
    GUTSHOT = "gutshot"
    OPEN_ENDED = "open_ended"
    DOUBLE_GUTSHOT = "double_gutshot"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    def __post_init__(self) -> None:
        if not isinstance(self.rank, Rank):
            raise TypeError("Card.rank must be a Rank value.")
        if not isinstance(self.suit, Suit):
            raise TypeError("Card.suit must be a Suit value.")

    def __str__(self) -> str:
        return f"{self.rank.short_name}{self.suit.short_name}"


@dataclass(frozen=True)
class HandEvaluation:
    category: HandCategory
    best_five_cards: tuple[Card, Card, Card, Card, Card]
    rank_key: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.category, HandCategory):
            raise TypeError("HandEvaluation.category must be a HandCategory value.")
        if len(self.best_five_cards) != 5:
            raise ValueError("HandEvaluation.best_five_cards must contain exactly five cards.")
        if len(set(self.best_five_cards)) != 5:
            raise ValueError("HandEvaluation.best_five_cards must be unique.")

    @property
    def comparison_key(self) -> tuple[int, ...]:
        return (int(self.category), *self.rank_key)

    @property
    def label(self) -> str:
        return self.category.label

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, HandEvaluation):
            return NotImplemented
        return self.comparison_key < other.comparison_key


@dataclass(frozen=True)
class DrawSummary:
    flush_draw: bool
    backdoor_flush_draw: bool
    straight_draw: StraightDrawType
    straight_draw_outs: int
    overcard_count: int
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def combo_draw(self) -> bool:
        return self.flush_draw and self.straight_draw != StraightDrawType.NONE

    @property
    def gutshot(self) -> bool:
        return self.straight_draw == StraightDrawType.GUTSHOT

    @property
    def open_ended(self) -> bool:
        return self.straight_draw == StraightDrawType.OPEN_ENDED

    @property
    def double_gutshot(self) -> bool:
        return self.straight_draw == StraightDrawType.DOUBLE_GUTSHOT


@dataclass(frozen=True)
class Scenario:
    street: Street
    hero_cards: tuple[Card, Card]
    board_cards: tuple[Card, ...]
    players_at_table: int
    players_in_hand: int
    position: Position
    pot_size: float
    call_amount: float
    effective_stack: float
    seed_tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.street, Street):
            raise TypeError("Scenario.street must be a Street value.")
        if not isinstance(self.position, Position):
            raise TypeError("Scenario.position must be a Position value.")
        if len(self.hero_cards) != 2:
            raise ValueError("Scenario.hero_cards must contain exactly two cards.")
        _validate_card_collection(self.hero_cards + self.board_cards, "Scenario cards")
        _validate_board_length(self.street, len(self.board_cards))
        _validate_minimum_integer(self.players_at_table, "players_at_table", minimum=2)
        _validate_minimum_integer(self.players_in_hand, "players_in_hand", minimum=2)
        if self.players_in_hand > self.players_at_table:
            raise ValueError("players_in_hand cannot exceed players_at_table.")
        _validate_non_negative_number(self.pot_size, "pot_size")
        _validate_non_negative_number(self.call_amount, "call_amount")
        _validate_non_negative_number(self.effective_stack, "effective_stack")

    @property
    def hero_hand(self) -> tuple[Card, Card]:
        return self.hero_cards

    @property
    def board(self) -> tuple[Card, ...]:
        return self.board_cards

    @property
    def facing_bet(self) -> float:
        return self.call_amount


@dataclass(frozen=True)
class ScenarioAnalysis:
    scenario: Scenario
    hand_evaluation: HandEvaluation | None
    draw_summary: DrawSummary
    break_even_equity: float
    pot_odds_ratio: float | None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.break_even_equity <= 1.0:
            raise ValueError("break_even_equity must be between 0.0 and 1.0.")
        if self.pot_odds_ratio is not None and self.pot_odds_ratio < 0.0:
            raise ValueError("pot_odds_ratio cannot be negative.")


def _validate_board_length(street: Street, board_card_count: int) -> None:
    expected_counts = {
        Street.PREFLOP: 0,
        Street.FLOP: 3,
        Street.TURN: 4,
        Street.RIVER: 5,
    }
    expected_count = expected_counts[street]
    if board_card_count != expected_count:
        raise ValueError(
            f"{street.value} scenarios require exactly {expected_count} board cards."
        )


def _validate_card_collection(cards: tuple[Card, ...], name: str) -> None:
    if any(not isinstance(card, Card) for card in cards):
        raise TypeError(f"{name} must contain Card values only.")
    if len(set(cards)) != len(cards):
        raise ValueError(f"{name} cannot contain duplicate cards.")


def _validate_minimum_integer(value: int, name: str, *, minimum: int) -> None:
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")


def _validate_non_negative_number(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
