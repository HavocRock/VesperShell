"""VesperShell visual tokens. Every note selects its own independent theme.

The five original color identifiers remain valid, so v0.1.x notes don't lose
an existing preference on upgrade. All shipped assets are drawn with Qt.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    background: str
    surface: str
    border: str
    accent: str
    hover: str
    text: str
    muted: str
    decoration: str
    radius: int = 15


SIGNATURE_THEMES = {
    "moon_violet": Theme("Moon Violet", "#F3ECFF", "#E7D8FA", "#CBB2EE", "#7952C4", "#DCC8F6", "#302243", "#594675", "#9D7ED2", 17),
    "amber_ember": Theme("Amber Ember", "#FFF2E8", "#FFDABD", "#F0B37D", "#BC601A", "#FFCDA6", "#4B2B12", "#77502D", "#E9A05B", 17),
    "turtle_grove": Theme("Turtle Grove", "#EAF8EE", "#CFECD8", "#9FD0AE", "#337D4C", "#BFE3CA", "#1E3928", "#446653", "#79AD89", 17),
}

# Legacy colors are usable in the new engine and may be applied intentionally.
CLASSIC_THEMES = {
    "sand": Theme("Classic Sand", "#FFF0BF", "#F7E5A9", "#E9D49B", "#80622B", "#F2DDA2", "#463C2D", "#655734", "#C6A46C", 11),
    "mint": Theme("Classic Mint", "#DCF3E6", "#C9E9D9", "#B3DBCA", "#337755", "#CAE9D8", "#264C3B", "#486C58", "#8ABB9D", 11),
    "sky": Theme("Classic Sky", "#DDEFF9", "#C8E3F2", "#B6D4E9", "#417A9F", "#C7E3F4", "#2A4254", "#36556B", "#7BB4D5", 11),
    "lavender": Theme("Classic Lavender", "#EAE1F8", "#DACBF0", "#CEC0E9", "#7952B3", "#DACCF1", "#443654", "#5B476E", "#AD91D4", 11),
    "charcoal": Theme("Classic Charcoal", "#293443", "#303E50", "#435265", "#A2C6F4", "#3A4A60", "#F2F6FC", "#C4D1E2", "#607C9D", 11),
}

THEMES: dict[str, Theme] = {**SIGNATURE_THEMES, **CLASSIC_THEMES}
DEFAULT_THEME = "turtle_grove"


def get_theme(theme_id: str) -> Theme:
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME])


def text_contrast(hex_a: str, hex_b: str) -> float:
    """WCAG contrast ratio for the two given opaque RGB colors."""
    def luminance(value: str) -> float:
        values = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        corrected = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
        return 0.2126 * corrected[0] + 0.7152 * corrected[1] + 0.0722 * corrected[2]
    a, b = sorted((luminance(hex_a), luminance(hex_b)), reverse=True)
    return (a + 0.05) / (b + 0.05)
