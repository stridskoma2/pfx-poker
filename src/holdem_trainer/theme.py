from __future__ import annotations

import dearpygui.dearpygui as dpg


WINDOW_BACKGROUND_COLOR = (21, 26, 34, 255)
PANEL_BACKGROUND_COLOR = (31, 38, 49, 255)
ACCENT_COLOR = (210, 165, 92, 255)
ACCENT_ACTIVE_COLOR = (236, 192, 120, 255)
TEXT_COLOR = (239, 237, 232, 255)
MUTED_TEXT_COLOR = (166, 174, 184, 255)
CORRECT_COLOR = (91, 181, 122, 255)
INCORRECT_COLOR = (204, 94, 94, 255)
FRAME_ROUNDING = 10
WINDOW_ROUNDING = 12


def create_app_theme() -> int:
    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, WINDOW_BACKGROUND_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, PANEL_BACKGROUND_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, PANEL_BACKGROUND_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, PANEL_BACKGROUND_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, ACCENT_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, ACCENT_ACTIVE_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_Button, ACCENT_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, ACCENT_ACTIVE_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, ACCENT_ACTIVE_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_Header, ACCENT_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, ACCENT_ACTIVE_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, ACCENT_ACTIVE_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, MUTED_TEXT_COLOR)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, FRAME_ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, WINDOW_ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 18, 18)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 10)
    return theme_id


def create_status_text_theme(color: tuple[int, int, int, int]) -> int:
    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvText):
            dpg.add_theme_color(dpg.mvThemeCol_Text, color)
    return theme_id
