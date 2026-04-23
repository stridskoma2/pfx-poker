from __future__ import annotations

from random import Random
from typing import Iterable, Sequence

from .models import Card, Rank, Suit

RANK_ALIASES: dict[str, Rank] = {
    "2": Rank.TWO,
    "3": Rank.THREE,
    "4": Rank.FOUR,
    "5": Rank.FIVE,
    "6": Rank.SIX,
    "7": Rank.SEVEN,
    "8": Rank.EIGHT,
    "9": Rank.NINE,
    "T": Rank.TEN,
    "10": Rank.TEN,
    "J": Rank.JACK,
    "Q": Rank.QUEEN,
    "K": Rank.KING,
    "A": Rank.ACE,
}
SUIT_ALIASES: dict[str, Suit] = {
    "C": Suit.CLUBS,
    "D": Suit.DIAMONDS,
    "H": Suit.HEARTS,
    "S": Suit.SPADES,
}


def parse_card(card_text: str) -> Card:
    normalized_text = card_text.strip().upper()
    if len(normalized_text) not in {2, 3}:
        raise ValueError(f"Invalid card text: {card_text!r}")
    rank_text = normalized_text[:-1]
    suit_text = normalized_text[-1]
    try:
        rank = RANK_ALIASES[rank_text]
        suit = SUIT_ALIASES[suit_text]
    except KeyError as error:
        raise ValueError(f"Invalid card text: {card_text!r}") from error
    return Card(rank=rank, suit=suit)


def parse_cards(card_texts: str | Iterable[str]) -> tuple[Card, ...]:
    if isinstance(card_texts, str):
        tokens = [
            token
            for token in card_texts.replace(",", " ").split()
            if token.strip()
        ]
    else:
        tokens = [token for token in card_texts]
    cards = tuple(parse_card(token) for token in tokens)
    if len(set(cards)) != len(cards):
        raise ValueError("Card collections cannot contain duplicates.")
    return cards


def build_standard_deck() -> tuple[Card, ...]:
    return tuple(Card(rank=rank, suit=suit) for suit in Suit for rank in Rank)


def shuffle_deck(
    deck: Sequence[Card] | None = None,
    *,
    seed: int | None = None,
    rng: Random | None = None,
) -> tuple[Card, ...]:
    source_cards = list(deck if deck is not None else build_standard_deck())
    _validate_deck(source_cards)
    shuffler = rng if rng is not None else Random(seed)
    shuffler.shuffle(source_cards)
    return tuple(source_cards)


def draw_cards(deck: Sequence[Card], count: int) -> tuple[tuple[Card, ...], tuple[Card, ...]]:
    _validate_deck(deck)
    if count < 0:
        raise ValueError("count cannot be negative.")
    if count > len(deck):
        raise ValueError("count cannot exceed the number of cards left in the deck.")
    drawn_cards = tuple(deck[:count])
    remaining_deck = tuple(deck[count:])
    return drawn_cards, remaining_deck


def _validate_deck(deck: Sequence[Card]) -> None:
    if any(not isinstance(card, Card) for card in deck):
        raise TypeError("Decks must contain Card values only.")
    if len(set(deck)) != len(deck):
        raise ValueError("Decks cannot contain duplicate cards.")
