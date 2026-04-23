from __future__ import annotations

from pathlib import Path

import dearpygui.dearpygui as dpg

from .models import Card, Scenario, Suit

TABLE_TEXTURE_TAG = "holdem_trainer.table_texture"
TABLE_DRAWLIST_TAG = "holdem_trainer.table_drawlist"
TABLE_IMAGE_PATH = (
    Path(__file__).resolve().parents[2] / "assets" / "images" / "poker-table-background.png"
)

SCENE_WIDTH = 760
SCENE_HEIGHT = 430
CARD_WIDTH = 82
CARD_HEIGHT = 116
SMALL_CARD_WIDTH = 38
SMALL_CARD_HEIGHT = 54
CARD_CORNER_RADIUS = 10
TABLE_FALLBACK_COLOR = (18, 72, 44, 255)
TABLE_FALLBACK_EDGE = (44, 22, 10, 255)
CARD_FRONT_COLOR = (248, 245, 239, 255)
CARD_BACK_COLOR = (41, 57, 86, 255)
CARD_EDGE_COLOR = (35, 35, 35, 255)
CARD_TEXT_DARK = (30, 30, 30, 255)
CARD_TEXT_RED = (191, 48, 48, 255)
BADGE_COLOR = (15, 27, 39, 220)
BADGE_TEXT_COLOR = (241, 236, 226, 255)
CHIP_FILL_COLOR = (181, 45, 63, 235)
CHIP_EDGE_COLOR = (245, 225, 180, 255)
PLAYER_SEAT_COLOR = (24, 33, 43, 220)
PLAYER_ACTIVE_COLOR = (211, 169, 88, 235)

SUIT_COLORS = {
    Suit.CLUBS: CARD_TEXT_DARK,
    Suit.SPADES: CARD_TEXT_DARK,
    Suit.DIAMONDS: CARD_TEXT_RED,
    Suit.HEARTS: CARD_TEXT_RED,
}
SUIT_DISPLAY_TEXT = {
    Suit.CLUBS: "♣",
    Suit.SPADES: "♠",
    Suit.DIAMONDS: "♦",
    Suit.HEARTS: "♥",
}


class TableSceneRenderer:
    def __init__(self) -> None:
        self._texture_ready = False
        self._table_image_bounds = ((18, 18), (SCENE_WIDTH - 18, SCENE_HEIGHT - 18))

    def register_assets(self) -> None:
        if self._texture_ready or not TABLE_IMAGE_PATH.exists():
            return
        width, height, channels, data = dpg.load_image(str(TABLE_IMAGE_PATH))
        del channels
        with dpg.texture_registry(show=False):
            dpg.add_static_texture(width=width, height=height, default_value=data, tag=TABLE_TEXTURE_TAG)
        self._texture_ready = True

    def build(self, parent: int | str) -> None:
        dpg.add_drawlist(width=SCENE_WIDTH, height=SCENE_HEIGHT, parent=parent, tag=TABLE_DRAWLIST_TAG)

    def render(self, scenario: Scenario) -> None:
        if not dpg.does_item_exist(TABLE_DRAWLIST_TAG):
            return

        dpg.delete_item(TABLE_DRAWLIST_TAG, children_only=True)
        self._draw_table_surface()
        self._draw_player_seats(scenario)
        self._draw_board_cards(scenario)
        self._draw_hero_cards(scenario)
        self._draw_pot_badges(scenario)

    def _draw_table_surface(self) -> None:
        if self._texture_ready and dpg.does_item_exist(TABLE_TEXTURE_TAG):
            start, end = self._table_image_bounds
            dpg.draw_image(TABLE_TEXTURE_TAG, pmin=start, pmax=end, parent=TABLE_DRAWLIST_TAG)
            return

        dpg.draw_rectangle(
            (16, 16),
            (SCENE_WIDTH - 16, SCENE_HEIGHT - 16),
            color=TABLE_FALLBACK_EDGE,
            fill=TABLE_FALLBACK_EDGE,
            rounding=22,
            parent=TABLE_DRAWLIST_TAG,
        )
        dpg.draw_rectangle(
            (40, 40),
            (SCENE_WIDTH - 40, SCENE_HEIGHT - 40),
            color=(60, 116, 75, 255),
            fill=TABLE_FALLBACK_COLOR,
            rounding=180,
            parent=TABLE_DRAWLIST_TAG,
        )

    def _draw_player_seats(self, scenario: Scenario) -> None:
        seat_positions = (
            (105, 82),
            (246, 54),
            (515, 54),
            (655, 82),
            (605, 320),
            (152, 320),
        )
        active_count = max(0, min(len(seat_positions), scenario.players_in_hand - 1))
        for seat_index, seat_position in enumerate(seat_positions):
            is_active = seat_index < active_count
            seat_color = PLAYER_ACTIVE_COLOR if is_active else PLAYER_SEAT_COLOR
            dpg.draw_circle(
                seat_position,
                19,
                color=(240, 223, 194, 190),
                fill=seat_color,
                thickness=2,
                parent=TABLE_DRAWLIST_TAG,
            )
            if is_active:
                self._draw_facedown_cards(seat_position)

    def _draw_facedown_cards(self, seat_center: tuple[int, int]) -> None:
        x_center, y_center = seat_center
        left_origin = (x_center - 30, y_center + 16)
        right_origin = (x_center - 4, y_center + 10)
        self._draw_card_back(left_origin)
        self._draw_card_back(right_origin)

    def _draw_card_back(self, origin: tuple[int, int]) -> None:
        x_origin, y_origin = origin
        bottom_right = (x_origin + SMALL_CARD_WIDTH, y_origin + SMALL_CARD_HEIGHT)
        dpg.draw_rectangle(
            origin,
            bottom_right,
            color=CARD_EDGE_COLOR,
            fill=CARD_BACK_COLOR,
            rounding=7,
            thickness=2,
            parent=TABLE_DRAWLIST_TAG,
        )
        dpg.draw_rectangle(
            (x_origin + 7, y_origin + 7),
            (bottom_right[0] - 7, bottom_right[1] - 7),
            color=(214, 190, 126, 230),
            fill=(60, 88, 130, 235),
            rounding=5,
            thickness=1,
            parent=TABLE_DRAWLIST_TAG,
        )

    def _draw_board_cards(self, scenario: Scenario) -> None:
        if not scenario.board:
            return

        total_width = len(scenario.board) * CARD_WIDTH + (len(scenario.board) - 1) * 10
        start_x = int((SCENE_WIDTH - total_width) / 2)
        for index, card in enumerate(scenario.board):
            origin = (start_x + index * (CARD_WIDTH + 10), 134)
            self._draw_card_front(card, origin)

    def _draw_hero_cards(self, scenario: Scenario) -> None:
        hero_origins = ((286, 284), (392, 284))
        for origin, card in zip(hero_origins, scenario.hero_hand):
            self._draw_card_front(card, origin)
        self._draw_badge((255, 246), (505, 274), "Hero")

    def _draw_card_front(self, card: Card, origin: tuple[int, int]) -> None:
        x_origin, y_origin = origin
        bottom_right = (x_origin + CARD_WIDTH, y_origin + CARD_HEIGHT)
        text_color = SUIT_COLORS[card.suit]
        rank_text = card.rank.short_name
        suit_text = SUIT_DISPLAY_TEXT[card.suit]

        dpg.draw_rectangle(
            origin,
            bottom_right,
            color=CARD_EDGE_COLOR,
            fill=CARD_FRONT_COLOR,
            rounding=CARD_CORNER_RADIUS,
            thickness=2,
            parent=TABLE_DRAWLIST_TAG,
        )
        dpg.draw_text(
            (x_origin + 10, y_origin + 8),
            rank_text,
            color=text_color,
            size=20,
            parent=TABLE_DRAWLIST_TAG,
        )
        dpg.draw_text(
            (x_origin + 10, y_origin + 32),
            suit_text,
            color=text_color,
            size=18,
            parent=TABLE_DRAWLIST_TAG,
        )
        dpg.draw_text(
            (x_origin + 26, y_origin + 42),
            suit_text,
            color=text_color,
            size=34,
            parent=TABLE_DRAWLIST_TAG,
        )

    def _draw_pot_badges(self, scenario: Scenario) -> None:
        pot_text = f"Pot {scenario.pot_size:.0f}"
        bet_text = f"To Call {scenario.facing_bet:.0f}"
        players_text = f"{scenario.players_in_hand}/{scenario.players_at_table} players"
        position_text = f"Position {str(scenario.position).upper()}"

        self._draw_chip((SCENE_WIDTH / 2 - 62, 100), pot_text)
        self._draw_badge((274, 98), (486, 125), players_text)
        self._draw_badge((274, 68), (486, 95), position_text)
        self._draw_badge((297, 241), (463, 268), bet_text)

    def _draw_chip(self, center: tuple[float, float], label: str) -> None:
        x_center, y_center = center
        dpg.draw_circle(
            center,
            30,
            color=CHIP_EDGE_COLOR,
            fill=CHIP_FILL_COLOR,
            thickness=3,
            parent=TABLE_DRAWLIST_TAG,
        )
        dpg.draw_circle(
            center,
            21,
            color=CHIP_EDGE_COLOR,
            fill=(134, 22, 41, 220),
            thickness=2,
            parent=TABLE_DRAWLIST_TAG,
        )
        dpg.draw_text(
            (x_center + 38, y_center - 9),
            label,
            color=BADGE_TEXT_COLOR,
            size=18,
            parent=TABLE_DRAWLIST_TAG,
        )

    def _draw_badge(
        self,
        top_left: tuple[float, float],
        bottom_right: tuple[float, float],
        label: str,
    ) -> None:
        dpg.draw_rectangle(
            top_left,
            bottom_right,
            color=(214, 190, 126, 210),
            fill=BADGE_COLOR,
            rounding=10,
            thickness=1,
            parent=TABLE_DRAWLIST_TAG,
        )
        dpg.draw_text(
            (top_left[0] + 12, top_left[1] + 5),
            label,
            color=BADGE_TEXT_COLOR,
            size=16,
            parent=TABLE_DRAWLIST_TAG,
        )
