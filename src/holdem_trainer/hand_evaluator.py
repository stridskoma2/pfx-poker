from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Iterable, Sequence, cast

from .cards import parse_card
from .models import (
    Card,
    DrawSummary,
    HandCategory,
    HandEvaluation,
    Rank,
    StraightDrawType,
)

MIN_EVALUATION_CARD_COUNT = 5
MAX_EVALUATION_CARD_COUNT = 7
STRAIGHT_WINDOW_SIZE = 5


def evaluate_best_hand(cards: Iterable[Card]) -> HandEvaluation:
    card_pool = _coerce_cards(cards)
    _validate_unique_cards(card_pool)
    if not MIN_EVALUATION_CARD_COUNT <= len(card_pool) <= MAX_EVALUATION_CARD_COUNT:
        raise ValueError("evaluate_best_hand requires 5, 6, or 7 unique cards.")

    evaluations = (_evaluate_five_card_hand(combo) for combo in combinations(card_pool, 5))
    return max(evaluations, key=lambda evaluation: evaluation.comparison_key)


def summarize_draws(
    hero_cards: Sequence[Card],
    board_cards: Sequence[Card],
) -> DrawSummary:
    hero_card_tuple = _coerce_cards(hero_cards)
    board_card_tuple = _coerce_cards(board_cards)
    if len(hero_card_tuple) != 2:
        raise ValueError("summarize_draws requires exactly two hero cards.")
    if len(board_card_tuple) > 5:
        raise ValueError("board_cards cannot contain more than five cards.")

    combined_cards = hero_card_tuple + board_card_tuple
    _validate_unique_cards(combined_cards)

    flush_draw, backdoor_flush_draw = _summarize_flush_draws(combined_cards, len(board_card_tuple))
    straight_draw, straight_draw_outs = _summarize_straight_draws(combined_cards, len(board_card_tuple))
    overcard_count = _count_overcards(hero_card_tuple, board_card_tuple)
    notes = _build_draw_notes(flush_draw, backdoor_flush_draw, straight_draw, overcard_count)
    return DrawSummary(
        flush_draw=flush_draw,
        backdoor_flush_draw=backdoor_flush_draw,
        straight_draw=straight_draw,
        straight_draw_outs=straight_draw_outs,
        overcard_count=overcard_count,
        notes=notes,
    )


def _evaluate_five_card_hand(cards: Sequence[Card]) -> HandEvaluation:
    if len(cards) != 5:
        raise ValueError("_evaluate_five_card_hand requires exactly five cards.")

    cards_by_rank = Counter(card.rank.value for card in cards)
    is_flush = len({card.suit for card in cards}) == 1
    straight_high = _find_straight_high(cards_by_rank.keys())
    grouped_ranks = _sorted_grouped_ranks(cards_by_rank)

    if is_flush and straight_high is not None:
        rank_key = (straight_high,)
        return HandEvaluation(
            category=HandCategory.STRAIGHT_FLUSH,
            best_five_cards=_order_straight_cards(cards, straight_high),
            rank_key=rank_key,
        )

    if grouped_ranks[0][1] == 4:
        four_kind_rank = grouped_ranks[0][0]
        kicker_rank = grouped_ranks[1][0]
        rank_key = (four_kind_rank, kicker_rank)
        return HandEvaluation(
            category=HandCategory.FOUR_OF_A_KIND,
            best_five_cards=_order_cards_by_rank_sequence(
                cards, [four_kind_rank, four_kind_rank, four_kind_rank, four_kind_rank, kicker_rank]
            ),
            rank_key=rank_key,
        )

    if grouped_ranks[0][1] == 3 and grouped_ranks[1][1] == 2:
        three_kind_rank = grouped_ranks[0][0]
        pair_rank = grouped_ranks[1][0]
        rank_key = (three_kind_rank, pair_rank)
        return HandEvaluation(
            category=HandCategory.FULL_HOUSE,
            best_five_cards=_order_cards_by_rank_sequence(
                cards, [three_kind_rank, three_kind_rank, three_kind_rank, pair_rank, pair_rank]
            ),
            rank_key=rank_key,
        )

    if is_flush:
        ordered_cards = tuple(sorted(cards, key=_card_sort_key, reverse=True))
        rank_key = tuple(card.rank.value for card in ordered_cards)
        return HandEvaluation(
            category=HandCategory.FLUSH,
            best_five_cards=ordered_cards,
            rank_key=rank_key,
        )

    if straight_high is not None:
        rank_key = (straight_high,)
        return HandEvaluation(
            category=HandCategory.STRAIGHT,
            best_five_cards=_order_straight_cards(cards, straight_high),
            rank_key=rank_key,
        )

    if grouped_ranks[0][1] == 3:
        three_kind_rank = grouped_ranks[0][0]
        kicker_ranks = sorted(
            (rank for rank, count in grouped_ranks if count == 1),
            reverse=True,
        )
        rank_key = (three_kind_rank, *kicker_ranks)
        return HandEvaluation(
            category=HandCategory.THREE_OF_A_KIND,
            best_five_cards=_order_cards_by_rank_sequence(
                cards, [three_kind_rank, three_kind_rank, three_kind_rank, *kicker_ranks]
            ),
            rank_key=rank_key,
        )

    pair_ranks = [rank for rank, count in grouped_ranks if count == 2]
    if len(pair_ranks) == 2:
        higher_pair, lower_pair = sorted(pair_ranks, reverse=True)
        kicker_rank = next(rank for rank, count in grouped_ranks if count == 1)
        rank_key = (higher_pair, lower_pair, kicker_rank)
        return HandEvaluation(
            category=HandCategory.TWO_PAIR,
            best_five_cards=_order_cards_by_rank_sequence(
                cards, [higher_pair, higher_pair, lower_pair, lower_pair, kicker_rank]
            ),
            rank_key=rank_key,
        )

    if len(pair_ranks) == 1:
        pair_rank = pair_ranks[0]
        kicker_ranks = sorted(
            (rank for rank, count in grouped_ranks if count == 1),
            reverse=True,
        )
        rank_key = (pair_rank, *kicker_ranks)
        return HandEvaluation(
            category=HandCategory.ONE_PAIR,
            best_five_cards=_order_cards_by_rank_sequence(
                cards, [pair_rank, pair_rank, *kicker_ranks]
            ),
            rank_key=rank_key,
        )

    high_cards = tuple(sorted((card.rank.value for card in cards), reverse=True))
    return HandEvaluation(
        category=HandCategory.HIGH_CARD,
        best_five_cards=tuple(sorted(cards, key=_card_sort_key, reverse=True)),
        rank_key=high_cards,
    )


def _summarize_flush_draws(
    cards: Sequence[Card],
    board_card_count: int,
) -> tuple[bool, bool]:
    suit_counts = Counter(card.suit for card in cards)
    highest_suit_count = max(suit_counts.values(), default=0)
    flush_draw = board_card_count < 5 and highest_suit_count == 4
    backdoor_flush_draw = board_card_count == 3 and highest_suit_count == 3
    return flush_draw, backdoor_flush_draw


def _summarize_straight_draws(
    cards: Sequence[Card],
    board_card_count: int,
) -> tuple[StraightDrawType, int]:
    if board_card_count >= 5:
        return StraightDrawType.NONE, 0

    rank_values = _expand_rank_values({card.rank.value for card in cards})
    if _contains_straight(rank_values):
        return StraightDrawType.NONE, 0

    open_ended_out_ranks = _find_open_ended_out_ranks(rank_values)
    if open_ended_out_ranks:
        return StraightDrawType.OPEN_ENDED, _count_rank_outs(cards, open_ended_out_ranks)

    gutshot_out_ranks = _find_gutshot_out_ranks(rank_values)
    if len(gutshot_out_ranks) >= 2:
        return StraightDrawType.DOUBLE_GUTSHOT, _count_rank_outs(cards, gutshot_out_ranks)
    if len(gutshot_out_ranks) == 1:
        return StraightDrawType.GUTSHOT, _count_rank_outs(cards, gutshot_out_ranks)
    return StraightDrawType.NONE, 0


def _count_overcards(hero_cards: Sequence[Card], board_cards: Sequence[Card]) -> int:
    if not board_cards:
        return 0
    highest_board_rank = max(card.rank.value for card in board_cards)
    return sum(card.rank.value > highest_board_rank for card in hero_cards)


def _build_draw_notes(
    flush_draw: bool,
    backdoor_flush_draw: bool,
    straight_draw: StraightDrawType,
    overcard_count: int,
) -> tuple[str, ...]:
    notes: list[str] = []
    if flush_draw:
        notes.append("Flush draw available.")
    elif backdoor_flush_draw:
        notes.append("Backdoor flush draw available.")
    if straight_draw == StraightDrawType.OPEN_ENDED:
        notes.append("Open-ended straight draw available.")
    elif straight_draw == StraightDrawType.DOUBLE_GUTSHOT:
        notes.append("Double gutshot straight draw available.")
    elif straight_draw == StraightDrawType.GUTSHOT:
        notes.append("Gutshot straight draw available.")
    if overcard_count:
        plural = "s" if overcard_count > 1 else ""
        notes.append(f"{overcard_count} overcard{plural} to the board.")
    return tuple(notes)


def _sorted_grouped_ranks(rank_counts: Counter[int]) -> list[tuple[int, int]]:
    return sorted(rank_counts.items(), key=lambda item: (item[1], item[0]), reverse=True)


def _find_straight_high(rank_values: Iterable[int]) -> int | None:
    expanded_values = _expand_rank_values(set(rank_values))
    for high_rank in range(Rank.ACE, Rank.FIVE - 1, -1):
        straight_window = {high_rank - offset for offset in range(STRAIGHT_WINDOW_SIZE)}
        if straight_window.issubset(expanded_values):
            return 5 if straight_window == {5, 4, 3, 2, 1} else high_rank
    return None


def _contains_straight(rank_values: set[int]) -> bool:
    return _find_straight_high(rank_values) is not None


def _expand_rank_values(rank_values: set[int]) -> set[int]:
    expanded_values = set(rank_values)
    if Rank.ACE in rank_values:
        expanded_values.add(1)
    return expanded_values


def _find_open_ended_out_ranks(rank_values: set[int]) -> set[int]:
    out_ranks: set[int] = set()
    for low_rank in range(1, 11):
        run = {low_rank + offset for offset in range(4)}
        if not run.issubset(rank_values):
            continue
        if run == {1, 2, 3, 4}:
            continue
        candidate_out_ranks = {low_rank - 1, low_rank + 4}
        for candidate_out_rank in candidate_out_ranks:
            normalized_out_rank = _normalize_rank(candidate_out_rank)
            if normalized_out_rank is not None:
                out_ranks.add(normalized_out_rank)
    return out_ranks


def _find_gutshot_out_ranks(rank_values: set[int]) -> set[int]:
    out_ranks: set[int] = set()
    for high_rank in range(Rank.FIVE, Rank.ACE + 1):
        window = {high_rank - offset for offset in range(STRAIGHT_WINDOW_SIZE)}
        missing_ranks = window - rank_values
        if len(missing_ranks) != 1:
            continue
        missing_rank = missing_ranks.pop()
        normalized_out_rank = _normalize_rank(missing_rank)
        if normalized_out_rank is not None:
            out_ranks.add(normalized_out_rank)
    return out_ranks


def _count_rank_outs(cards: Sequence[Card], out_ranks: set[int]) -> int:
    rank_counts = Counter(card.rank.value for card in cards)
    return sum(4 - rank_counts[rank] for rank in out_ranks)


def _normalize_rank(rank_value: int) -> int | None:
    if rank_value == 1:
        return Rank.ACE
    if Rank.TWO <= rank_value <= Rank.ACE:
        return rank_value
    return None


def _order_straight_cards(cards: Sequence[Card], straight_high: int) -> tuple[Card, Card, Card, Card, Card]:
    if straight_high == 5:
        rank_sequence = [5, 4, 3, 2, Rank.ACE]
    else:
        rank_sequence = [straight_high - offset for offset in range(STRAIGHT_WINDOW_SIZE)]
    return _order_cards_by_rank_sequence(cards, rank_sequence)


def _order_cards_by_rank_sequence(
    cards: Sequence[Card],
    rank_sequence: Sequence[int],
) -> tuple[Card, Card, Card, Card, Card]:
    remaining_cards = list(sorted(cards, key=_card_sort_key, reverse=True))
    ordered_cards: list[Card] = []
    for rank_value in rank_sequence:
        for index, card in enumerate(remaining_cards):
            if card.rank.value == rank_value:
                ordered_cards.append(card)
                del remaining_cards[index]
                break
        else:
            raise ValueError(f"Could not order cards for rank sequence {rank_sequence!r}.")
    return cast(tuple[Card, Card, Card, Card, Card], tuple(ordered_cards))


def _card_sort_key(card: Card) -> tuple[int, str]:
    return card.rank.value, card.suit.value


def _validate_unique_cards(cards: Sequence[Card]) -> None:
    if any(not isinstance(card, Card) for card in cards):
        raise TypeError("Card collections must contain Card values only.")
    if len(set(cards)) != len(cards):
        raise ValueError("Card collections cannot contain duplicates.")


def _coerce_cards(cards: Iterable[Card | str]) -> tuple[Card, ...]:
    coerced_cards: list[Card] = []
    for card in cards:
        coerced_cards.append(parse_card(card) if isinstance(card, str) else card)
    return tuple(coerced_cards)
