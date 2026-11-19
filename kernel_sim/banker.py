"""Banker's safety check for arbitrary process and resource counts."""

from __future__ import annotations

from dataclasses import dataclass

from .validation import require_non_negative


@dataclass(frozen=True)
class BankerResult:
    safe: bool
    available: tuple[int, ...]
    need: tuple[tuple[int, ...], ...]
    safe_sequence: tuple[str, ...]
    blocked: tuple[str, ...]


def check_safety(
    process_ids: list[str], allocation: list[list[int]], maximum: list[list[int]], total: list[int]
) -> BankerResult:
    if not process_ids:
        raise ValueError("Enter at least one process.")
    if len(set(process_ids)) != len(process_ids):
        raise ValueError("Process IDs must be unique.")
    resource_count = len(total)
    if resource_count == 0:
        raise ValueError("Enter at least one resource type.")
    if len(allocation) != len(process_ids) or len(maximum) != len(process_ids):
        raise ValueError("Allocation and maximum matrices need one row for each process.")
    for label, matrix in (("Allocation", allocation), ("Maximum", maximum)):
        for i, row in enumerate(matrix):
            if len(row) != resource_count:
                raise ValueError(f"{label} row for {process_ids[i]} needs {resource_count} values.")
            for value in row:
                require_non_negative(value, label)
    for value in total:
        require_non_negative(value, "Total resources")
    for i in range(len(process_ids)):
        for j in range(resource_count):
            if maximum[i][j] < allocation[i][j]:
                raise ValueError(f"Maximum demand for {process_ids[i]} cannot be below its allocation.")
    allocated = [sum(allocation[i][j] for i in range(len(process_ids))) for j in range(resource_count)]
    if any(allocated[j] > total[j] for j in range(resource_count)):
        raise ValueError("Allocated resources cannot exceed the total instances available.")
    available = [total[j] - allocated[j] for j in range(resource_count)]
    need = [[maximum[i][j] - allocation[i][j] for j in range(resource_count)] for i in range(len(process_ids))]
    work = available.copy()
    finished = [False] * len(process_ids)
    sequence: list[str] = []
    changed = True
    while changed:
        changed = False
        for i, pid in enumerate(process_ids):
            if not finished[i] and all(need[i][j] <= work[j] for j in range(resource_count)):
                work = [work[j] + allocation[i][j] for j in range(resource_count)]
                finished[i] = True
                sequence.append(pid)
                changed = True
    blocked = tuple(process_ids[i] for i, done in enumerate(finished) if not done)
    return BankerResult(not blocked, tuple(available), tuple(tuple(row) for row in need), tuple(sequence), blocked)
