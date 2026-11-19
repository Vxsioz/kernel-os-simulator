"""Fixed and variable partition allocation with fragmentation summaries."""

from __future__ import annotations

from dataclasses import dataclass

from .validation import require_positive


@dataclass(frozen=True)
class Allocation:
    process_id: str
    process_size: int
    block_index: int
    block_size: int
    internal_waste: int


@dataclass(frozen=True)
class FragmentationResult:
    mode: str
    strategy: str
    allocations: tuple[Allocation, ...]
    unallocated: tuple[str, ...]
    free_blocks: tuple[int, ...]
    total_free: int
    largest_hole: int
    external_fragmentation: int
    internal_fragmentation: int


def allocate(
    blocks: list[int], processes: list[tuple[str, int]], mode: str = "Fixed partitions", strategy: str = "First fit"
) -> FragmentationResult:
    if not blocks:
        raise ValueError("Enter at least one memory block.")
    if not processes:
        raise ValueError("Enter at least one process.")
    if mode not in {"Fixed partitions", "Variable partitions"}:
        raise ValueError("Choose fixed or variable partitions.")
    if strategy not in {"First fit", "Best fit", "Worst fit", "Next fit"}:
        raise ValueError("Choose First fit, Best fit, Worst fit, or Next fit.")
    for size in blocks:
        require_positive(size, "Memory block size")
    ids = [pid for pid, _ in processes]
    if len(set(ids)) != len(ids) or any(not pid.strip() for pid in ids):
        raise ValueError("Process IDs must be unique and non-empty.")
    for pid, size in processes:
        require_positive(size, f"Memory required by {pid}")

    free = blocks.copy()
    allocations: list[Allocation] = []
    unallocated: list[str] = []
    internal = 0
    next_start = 0
    for pid, requested in processes:
        candidates = [i for i, available in enumerate(free) if available >= requested]
        if not candidates:
            unallocated.append(pid)
            continue
        if strategy == "Next fit":
            index = None
            for step in range(len(free)):
                candidate = (next_start + step) % len(free)
                if free[candidate] >= requested:
                    index = candidate
                    break
            if index is None:
                unallocated.append(pid)
                continue
        elif strategy == "First fit":
            index = candidates[0]
        elif strategy == "Best fit":
            index = min(candidates, key=lambda i: (free[i], i))
        else:
            index = max(candidates, key=lambda i: (free[i], -i))
        block_size = free[index]
        if mode == "Fixed partitions":
            waste = block_size - requested
            internal += waste
            free[index] = 0
        else:
            waste = 0
            free[index] -= requested
        if strategy == "Next fit":
            next_start = (index + 1) % len(free)
        allocations.append(Allocation(pid, requested, index + 1, block_size, waste))
    holes = tuple(size for size in free if size > 0)
    total_free = sum(holes)
    largest = max(holes, default=0)
    return FragmentationResult(
        mode, strategy, tuple(allocations), tuple(unallocated), holes,
        total_free, largest, total_free - largest if mode == "Variable partitions" else 0, internal
    )
