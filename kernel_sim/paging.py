"""Page-table mapping and logical-to-physical address translation."""

from __future__ import annotations

from .validation import require_non_negative, require_positive, require_unique


def translate(page_size: int, page_table: list[tuple[int, int]], logical_address: int) -> dict[str, int]:
    require_positive(page_size, "Page size")
    require_non_negative(logical_address, "Logical address")
    pages = [page for page, _ in page_table]
    frames = [frame for _, frame in page_table]
    require_unique((str(value) for value in pages), "Page number")
    require_unique((str(value) for value in frames), "Frame number")
    for page, frame in page_table:
        require_non_negative(page, "Page number")
        require_non_negative(frame, "Frame number")
    page_number, offset = divmod(logical_address, page_size)
    table = dict(page_table)
    if page_number not in table:
        raise ValueError(f"Page {page_number} is not mapped. The address causes a page fault.")
    frame = table[page_number]
    return {
        "logical_address": logical_address,
        "page_size": page_size,
        "page": page_number,
        "offset": offset,
        "frame": frame,
        "physical_address": frame * page_size + offset,
    }
