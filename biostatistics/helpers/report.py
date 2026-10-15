"""Number formatting and table styling for the notebook.

Tables set no text colours of their own, so they stay readable in light and
dark editor themes. Emphasis uses weight and style instead of colour.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MINUS = "−"  # a real minus sign, not a hyphen


def _no_negative_zero(x: float, digits: int) -> float:
    """0.0 for anything that rounds to zero, so −0.004 never prints as '−0.00'."""
    return 0.0 if round(float(x), digits) == 0 else float(x)


def num(x: float, digits: int = 1) -> str:
    """Fixed-point number with a typographic minus sign."""
    return f"{_no_negative_zero(x, digits):.{digits}f}".replace("-", MINUS)


def signed(x: float, digits: int = 1) -> str:
    """Like ``num`` but always shows the sign, e.g. +3.2 or −3.2."""
    return f"{_no_negative_zero(x, digits):+.{digits}f}".replace("-", MINUS)


def fmt_p(p: float) -> str:
    """p-value as reported in the text: '< 0.001' or three decimals."""
    if not np.isfinite(p):
        return ""
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def p_label(p: float) -> str:
    """Short p-value label for figures: 'p < 0.001' or 'p = 0.011'."""
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def est_ci(est: float, low: float, high: float, digits: int = 1) -> str:
    """Estimate with its interval, e.g. '−15.9 [−20.5, −11.3]'."""
    return f"{signed(est, digits)} [{num(low, digits)}, {num(high, digits)}]"


def ci(low: float, high: float, digits: int = 2) -> str:
    """An interval on its own, e.g. '[0.28, 0.59]'."""
    return f"[{num(low, digits)}, {num(high, digits)}]"


_TABLE_STYLES = [
    {"selector": "caption",
     "props": "caption-side: top; text-align: left; font-weight: 600; font-size: 1.05em; padding: 0 0 6px 0;"},
    {"selector": "th",
     "props": "text-align: left; font-weight: 600; padding: 5px 12px; "
              "border-bottom: 1px solid rgba(128,128,128,0.55);"},
    {"selector": "td",
     "props": "padding: 4px 12px; font-variant-numeric: tabular-nums; "
              "border-bottom: 1px solid rgba(128,128,128,0.2);"},
    {"selector": "", "props": "border-collapse: collapse; margin: 4px 0 10px 0;"},
]

_VERDICT_CSS = {
    "clear": "font-weight: 700;",
    "suggestive": "font-style: italic;",
    "not significant": "",
    "pass": "",
    "FAIL": "font-weight: 700; text-decoration: underline;",
}


def table(df: pd.DataFrame, caption: str | None = None, right: list[str] | None = None,
          emphasis: str | None = None):
    """Styled, index-free HTML table.

    Args:
        df: Already formatted (strings) or plain values.
        caption: Title shown above the table.
        right: Columns to right-align (numbers).
        emphasis: Column whose value ('clear', 'suggestive', 'not significant',
            'pass', 'FAIL') sets the weight of the whole row.
    """
    df = df.reset_index(drop=True)  # the index is hidden anyway; styling needs it unique
    styler = df.style.hide(axis="index").set_table_styles(_TABLE_STYLES)
    if caption:
        styler = styler.set_caption(caption)
    if right:
        styler = styler.set_properties(subset=right, **{"text-align": "right"})
    if emphasis:
        css = df[emphasis].map(lambda v: _VERDICT_CSS.get(str(v), ""))
        styler = styler.apply(lambda row: [css.loc[row.name]] * len(row), axis=1)
    return styler
