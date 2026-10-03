from __future__ import annotations

import re
from typing import Dict, Iterable

_EXPLICIT = re.compile(
    r"^[ \t]*(?:(?:q(?:uestion)?|ans(?:wer)?)[ \t]*\.?[ \t]*(?:to[ \t]+)?(?:q(?:uestion)?[ \t]*\.?[ \t]*)?"
    r"(?:no\.?[ \t]*)?(\d{1,3})[ \t]*[\.\):\-]?)",
    re.IGNORECASE | re.MULTILINE,
)
_BARE = re.compile(r"^[ \t]*(\d{1,3})[ \t]*[\.\):]", re.MULTILINE)


def split_answers(text: str, numbers: Iterable[int]) -> Dict[int, str]:
    """Detect question markers (Q1, Ans 2, 3.) and return {question_number: answer_text}."""
    expected = set(numbers)
    markers = _find(_EXPLICIT, text, expected) or _find(_BARE, text, expected)
    result: Dict[int, str] = {}
    for i, (num, _start, body_start) in enumerate(markers):
        end = markers[i + 1][1] if i + 1 < len(markers) else len(text)
        result[num] = text[body_start:end].strip()
    return result


def _find(pattern, text, expected):
    seen, found = set(), []
    for m in pattern.finditer(text):
        n = int(m.group(1))
        if n in expected and n not in seen:
            seen.add(n)
            found.append((n, m.start(), m.end()))
    return found
