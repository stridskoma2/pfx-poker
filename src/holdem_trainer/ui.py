from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Sequence

import dearpygui.dearpygui as dpg

from .models import Action
from .scenario_generator import ScenarioEngine
from .theme import CORRECT_COLOR, INCORRECT_COLOR, MUTED_TEXT_COLOR, create_app_theme, create_status_text_theme


WINDOW_TAG = "holdem_trainer.window"
SCENARIO_TEXT_TAG = "holdem_trainer.scenario_text"
ANSWER_TAG = "holdem_trainer.answer"
SUBMIT_BUTTON_TAG = "holdem_trainer.submit"
NEXT_BUTTON_TAG = "holdem_trainer.next"
EXPLANATION_TAG = "holdem_trainer.explanation"
RESULT_TAG = "holdem_trainer.result"
SCORE_TAG = "holdem_trainer.score"
PROGRESS_TAG = "holdem_trainer.progress"
DIFFICULTY_TAG = "holdem_trainer.difficulty"
QUESTION_TAG = "holdem_trainer.question"

VIEWPORT_TITLE = "Texas Hold'em Trainer"
VIEWPORT_WIDTH = 1360
VIEWPORT_HEIGHT = 880
ACTION_LABELS = {
    Action.FOLD: "Fold",
    Action.CHECK: "Check",
    Action.CALL: "Call",
    Action.BET_SMALL: "Bet Small",
    Action.BET_LARGE: "Bet Large",
    Action.RAISE_SMALL: "Raise Small",
    Action.RAISE_LARGE: "Raise Large",
}
FACING_BET_ACTIONS = (
    Action.FOLD,
    Action.CALL,
    Action.RAISE_SMALL,
    Action.RAISE_LARGE,
)
CHECKED_TO_ACTIONS = (
    Action.CHECK,
    Action.BET_SMALL,
    Action.BET_LARGE,
)
STREET_LABELS = {
    "preflop": "Preflop",
    "flop": "Flop",
    "turn": "Turn",
    "river": "River",
}
POSITION_LABELS = {
    "utg": "UTG",
    "hj": "HJ",
    "co": "CO",
    "btn": "Button",
    "sb": "Small Blind",
    "bb": "Big Blind",
}
UNAVAILABLE_TEXT = "Not provided"
DEFAULT_EXPLANATION = "Select the best action, then submit to reveal the training explanation."


def launch_app() -> None:
    application = HoldemTrainerUi(ScenarioEngine())
    application.run()


@dataclass(slots=True)
class QuizSession:
    scenario: Any | None = None
    analysis: Any | None = None
    question_number: int = 0
    correct_answers: int = 0
    total_answered: int = 0
    awaiting_submission: bool = True
    selected_action: Action | None = None

    @property
    def score_text(self) -> str:
        if self.total_answered == 0:
            return "Score: 0/0 (0%)"
        percentage = round((self.correct_answers / self.total_answered) * 100)
        return f"Score: {self.correct_answers}/{self.total_answered} ({percentage}%)"


class HoldemTrainerUi:
    def __init__(self, scenario_engine: ScenarioEngine) -> None:
        self._scenario_engine = scenario_engine
        self._session = QuizSession()
        self._app_theme_id: int | None = None
        self._correct_text_theme_id: int | None = None
        self._incorrect_text_theme_id: int | None = None
        self._neutral_text_theme_id: int | None = None

    def run(self) -> None:
        dpg.create_context()
        try:
            self._create_themes()
            dpg.create_viewport(title=VIEWPORT_TITLE, width=VIEWPORT_WIDTH, height=VIEWPORT_HEIGHT)
            self._build_interface()
            self._load_next_scenario()
            dpg.setup_dearpygui()
            dpg.show_viewport()
            dpg.set_primary_window(WINDOW_TAG, True)
            dpg.start_dearpygui()
        finally:
            dpg.destroy_context()

    def _create_themes(self) -> None:
        self._app_theme_id = create_app_theme()
        self._correct_text_theme_id = create_status_text_theme(CORRECT_COLOR)
        self._incorrect_text_theme_id = create_status_text_theme(INCORRECT_COLOR)
        self._neutral_text_theme_id = create_status_text_theme(MUTED_TEXT_COLOR)

    def _build_interface(self) -> None:
        with dpg.window(tag=WINDOW_TAG, label=VIEWPORT_TITLE):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=760, autosize_y=True, border=False):
                    dpg.add_text("Spot")
                    dpg.add_separator()
                    dpg.add_text("", tag=QUESTION_TAG)
                    dpg.add_spacer(height=4)
                    dpg.add_text("", tag=SCENARIO_TEXT_TAG, wrap=720)
                    dpg.add_spacer(height=12)
                    dpg.add_text("Choose the best action")
                    dpg.add_radio_button(
                        items=[],
                        horizontal=False,
                        tag=ANSWER_TAG,
                        callback=self._on_answer_selected,
                    )
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Submit", tag=SUBMIT_BUTTON_TAG, callback=self._on_submit_pressed, width=130)
                        dpg.add_button(
                            label="Next Scenario",
                            tag=NEXT_BUTTON_TAG,
                            callback=self._on_next_pressed,
                            width=150,
                            enabled=False,
                        )
                with dpg.child_window(autosize_x=True, autosize_y=True, border=False):
                    dpg.add_text("Session")
                    dpg.add_separator()
                    dpg.add_text("", tag=SCORE_TAG)
                    dpg.add_text("", tag=PROGRESS_TAG)
                    dpg.add_text("", tag=DIFFICULTY_TAG)
                    dpg.add_spacer(height=12)
                    dpg.add_text("Result")
                    dpg.add_separator()
                    dpg.add_text("", tag=RESULT_TAG, wrap=420)
                    dpg.add_spacer(height=12)
                    dpg.add_text("Explanation")
                    dpg.add_separator()
                    dpg.add_text(DEFAULT_EXPLANATION, tag=EXPLANATION_TAG, wrap=420)
        if self._app_theme_id is not None:
            dpg.bind_theme(self._app_theme_id)

    def _load_next_scenario(self) -> None:
        scenario = self._scenario_engine.next_scenario()
        analysis = getattr(scenario, "analysis", None)
        self._session.scenario = scenario
        self._session.analysis = analysis
        self._session.question_number += 1
        self._session.awaiting_submission = True
        self._session.selected_action = None
        dpg.configure_item(ANSWER_TAG, items=self._action_labels_for_scenario(scenario))
        dpg.set_value(ANSWER_TAG, "")
        dpg.set_value(QUESTION_TAG, f"Question {self._session.question_number}")
        dpg.set_value(SCENARIO_TEXT_TAG, self._format_scenario(scenario))
        dpg.set_value(RESULT_TAG, "Submit your answer to reveal the evaluation.")
        dpg.set_value(EXPLANATION_TAG, DEFAULT_EXPLANATION)
        dpg.set_value(DIFFICULTY_TAG, self._difficulty_text(analysis))
        dpg.configure_item(SUBMIT_BUTTON_TAG, enabled=False)
        dpg.configure_item(NEXT_BUTTON_TAG, enabled=False)
        self._bind_result_theme(self._neutral_text_theme_id)
        self._refresh_score()

    def _on_answer_selected(self, sender: int, app_data: str, user_data: Any) -> None:
        del sender, user_data
        self._session.selected_action = self._label_to_action(app_data)
        dpg.configure_item(SUBMIT_BUTTON_TAG, enabled=self._session.awaiting_submission and self._session.selected_action is not None)

    def _on_submit_pressed(self, sender: int, app_data: Any, user_data: Any) -> None:
        del sender, app_data, user_data
        if not self._session.awaiting_submission or self._session.selected_action is None or self._session.analysis is None:
            return

        self._session.awaiting_submission = False
        self._session.total_answered += 1
        selected_action = self._session.selected_action
        accepted_actions = self._accepted_actions()
        is_correct = selected_action in accepted_actions
        if is_correct:
            self._session.correct_answers += 1

        dpg.set_value(RESULT_TAG, self._result_text(selected_action, is_correct))
        dpg.set_value(EXPLANATION_TAG, self._explanation_text())
        dpg.configure_item(SUBMIT_BUTTON_TAG, enabled=False)
        dpg.configure_item(NEXT_BUTTON_TAG, enabled=True)
        self._bind_result_theme(self._correct_text_theme_id if is_correct else self._incorrect_text_theme_id)
        self._refresh_score()

    def _on_next_pressed(self, sender: int, app_data: Any, user_data: Any) -> None:
        del sender, app_data, user_data
        self._load_next_scenario()

    def _refresh_score(self) -> None:
        dpg.set_value(SCORE_TAG, self._session.score_text)
        dpg.set_value(PROGRESS_TAG, f"Answered: {self._session.total_answered}")

    def _accepted_actions(self) -> set[Action]:
        correct_action = self._analysis_action("correct_action")
        accepted_actions = {correct_action} if correct_action is not None else set()
        extra_actions = self._iterable_attribute(self._analysis_attribute("accepted_actions", ()))
        accepted_actions.update(self._coerce_actions(extra_actions))
        return accepted_actions

    def _result_text(self, selected_action: Action, is_correct: bool) -> str:
        correct_action = self._analysis_action("correct_action")
        selected_label = self._action_label(selected_action)
        correct_label = self._action_label(correct_action)
        if is_correct:
            return f"Correct. {selected_label} is accepted for this spot."
        return f"Not quite. You chose {selected_label}; the best training answer is {correct_label}."

    def _explanation_text(self) -> str:
        analysis = self._session.analysis
        if analysis is None:
            return DEFAULT_EXPLANATION
        explanation = self._analysis_attribute("explanation", "")
        reason_codes = list(self._iterable_attribute(self._analysis_attribute("reason_codes", ())))
        if not reason_codes:
            return str(explanation) if explanation else DEFAULT_EXPLANATION
        reason_text = ", ".join(str(code) for code in reason_codes)
        if explanation:
            return f"{explanation}\n\nReason codes: {reason_text}"
        return f"Reason codes: {reason_text}"

    def _analysis_action(self, attribute_name: str) -> Action | None:
        attribute_value = self._analysis_attribute(attribute_name, None)
        return self._coerce_action(attribute_value)

    def _analysis_attribute(self, attribute_name: str, default_value: Any) -> Any:
        analysis = self._session.analysis
        if analysis is None:
            return default_value
        return getattr(analysis, attribute_name, default_value)

    def _difficulty_text(self, analysis: Any) -> str:
        difficulty = getattr(analysis, "difficulty", None)
        if difficulty is None:
            return "Difficulty: Not rated"
        return f"Difficulty: {difficulty}"

    def _iterable_attribute(self, value: Any) -> Iterable[Any]:
        if value is None:
            return ()
        if isinstance(value, str):
            return (value,)
        return value

    def _format_scenario(self, scenario: Any) -> str:
        lines = [
            self._format_line("Street", self._label_from_mapping(STREET_LABELS, getattr(scenario, "street", None))),
            self._format_line("Hero Hand", self._format_cards(getattr(scenario, "hero_hand", ()))),
            self._format_line("Board", self._format_cards(getattr(scenario, "board", ()))),
            self._format_line("Table", self._table_text(scenario)),
            self._format_line("Position", self._label_from_mapping(POSITION_LABELS, getattr(scenario, "position", None))),
            self._format_line("Pot Size", self._format_amount(getattr(scenario, "pot_size", None))),
            self._format_line("Facing Bet", self._format_amount(getattr(scenario, "facing_bet", None))),
            self._format_line("Effective Stack", self._format_amount(getattr(scenario, "effective_stack", None))),
            self._format_line("Tags", self._format_tags(getattr(scenario, "seed_tags", ()))),
        ]
        return "\n".join(lines)

    def _table_text(self, scenario: Any) -> str:
        players_at_table = getattr(scenario, "players_at_table", None)
        players_in_hand = getattr(scenario, "players_in_hand", None)
        if players_at_table is None and players_in_hand is None:
            return UNAVAILABLE_TEXT
        if players_at_table is None:
            return f"{players_in_hand} still in hand"
        if players_in_hand is None:
            return f"{players_at_table} players at table"
        return f"{players_at_table} players at table, {players_in_hand} still in hand"

    def _format_cards(self, cards: Iterable[Any]) -> str:
        rendered_cards = [str(card) for card in cards]
        if not rendered_cards:
            return UNAVAILABLE_TEXT
        return " ".join(rendered_cards)

    def _format_tags(self, tags: Iterable[Any]) -> str:
        rendered_tags = [str(tag) for tag in tags]
        if not rendered_tags:
            return "None"
        return ", ".join(rendered_tags)

    def _format_amount(self, value: Any) -> str:
        if value is None:
            return UNAVAILABLE_TEXT
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def _format_line(self, label: str, value: str) -> str:
        return f"{label}: {value}"

    def _label_from_mapping(self, labels: dict[str, str], key: Any) -> str:
        if key is None:
            return UNAVAILABLE_TEXT
        normalized_key = str(key).lower()
        return labels.get(normalized_key, str(key))

    def _action_labels_for_scenario(self, scenario: Any) -> Sequence[str]:
        return [self._action_label(action) for action in self._available_actions_for_scenario(scenario)]

    def _available_actions_for_scenario(self, scenario: Any) -> Sequence[Action]:
        facing_bet = getattr(scenario, "facing_bet", None)
        if facing_bet is None:
            return tuple(Action)
        if self._is_checked_to(facing_bet):
            return CHECKED_TO_ACTIONS
        return FACING_BET_ACTIONS

    def _is_checked_to(self, facing_bet: Any) -> bool:
        if isinstance(facing_bet, (int, float)):
            return facing_bet <= 0
        try:
            return float(str(facing_bet).strip()) <= 0
        except ValueError:
            return False

    def _action_label(self, action: Action | None) -> str:
        if action is None:
            return UNAVAILABLE_TEXT
        return ACTION_LABELS.get(action, str(action))

    def _label_to_action(self, label: str) -> Action | None:
        for action, action_label in ACTION_LABELS.items():
            if action_label == label:
                return action
        return None

    def _coerce_actions(self, values: Iterable[Any]) -> set[Action]:
        return {action for action in (self._coerce_action(value) for value in values) if action is not None}

    def _coerce_action(self, value: Any) -> Action | None:
        if isinstance(value, Action):
            return value
        if isinstance(value, Enum):
            return self._coerce_action(value.value)
        if isinstance(value, str):
            normalized_value = value.strip().lower()
            for action in Action:
                if normalized_value == action.name.lower():
                    return action
                if normalized_value == str(action.value).lower():
                    return action
        return None

    def _bind_result_theme(self, theme_id: int | None) -> None:
        if theme_id is not None:
            dpg.bind_item_theme(RESULT_TAG, theme_id)
