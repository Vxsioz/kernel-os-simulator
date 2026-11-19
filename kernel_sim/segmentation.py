"""Segment-table address validation and physical address calculation."""

from __future__ import annotations

from .validation import require_non_negative, require_unique


def translate(segments: list[tuple[int, int, int]], segment_number: int, offset: int) -> dict[str, int]:
    if not segments:
        raise ValueError("Enter at least one segment.")
    require_unique((str(number) for number, _, _ in segments), "Segment number")
    for number, base, limit in segments:
        require_non_negative(number, "Segment number")
        require_non_negative(base, "Segment base")
        if limit <= 0:
            raise ValueError(f"The limit for segment {number} must be greater than zero.")
    require_non_negative(segment_number, "Segment number")
    require_non_negative(offset, "Offset")
    table = {number: (base, limit) for number, base, limit in segments}
    if segment_number not in table:
        raise ValueError(f"Segment {segment_number} does not exist.")
    base, limit = table[segment_number]
    if offset >= limit:
        raise ValueError(f"Address fault: offset {offset} is outside segment {segment_number} (limit {limit}).")
    return {"segment": segment_number, "base": base, "limit": limit, "offset": offset, "physical_address": base + offset}
