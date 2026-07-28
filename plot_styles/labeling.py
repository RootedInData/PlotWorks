from __future__ import annotations

import re
import textwrap
from collections.abc import Iterable


def humanize_label(value: object) -> str:
    """Convert a machine-style identifier into a readable axis label."""

    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1].upper() + text[1:] if text else text


def wrap_labels(values: Iterable[object], width: int = 22) -> list[str]:
    return [textwrap.fill(str(value), width=max(width, 8)) for value in values]
