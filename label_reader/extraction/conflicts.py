# -*- coding: utf-8 -*-
"""تشخیص تناقض میان نواحی OCR — علامت‌گذاری، نه انتخاب بی‌دلیل."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Candidate:
    value_norm: str            # مقدار نرمال (ارقام لاتین)
    unit: str | None = None    # واحد به‌صورت متعارف (mg, mcg, mL, ...)
    raw_text: str = ""
    source_ids: list[str] = field(default_factory=list)
    confidence: float | None = None
    line_index: int = -1
    x: int = 0
    y: int = 0


def _conf(c: Candidate) -> float:
    return c.confidence if c.confidence is not None else 0.5


def resolve_candidates(
    candidates: list[Candidate],
    low_confidence_threshold: float,
) -> tuple[Candidate | None, str, list[str]]:
    """حل جمع نامزدها با سیاست محافظه‌کارانه.

    بازگشت: (بهترین نامزد یا None، وضعیت، همه مقادیر متمایز)
    وضعیت‌ها: missing | extracted | uncertain | conflicting
    - چند مقدار متمایز → conflicting (هیچ‌کدام حذف نمی‌شوند؛ بهترین فقط «نمایش» است)
    - یک مقدار با اطمینان پایین → uncertain
    """
    if not candidates:
        return None, "missing", []
    distinct: list[Candidate] = []
    seen: set[tuple[str, str | None]] = set()
    for c in sorted(candidates, key=_conf, reverse=True):
        key = (c.value_norm, c.unit)
        if key not in seen:
            seen.add(key)
            distinct.append(c)
    if len(distinct) > 1:
        return distinct[0], "conflicting", [c.value_norm for c in distinct]
    best = distinct[0]
    conf = _conf(best)
    if conf < low_confidence_threshold:
        return best, "uncertain", [best.value_norm]
    return best, "extracted", [best.value_norm]
