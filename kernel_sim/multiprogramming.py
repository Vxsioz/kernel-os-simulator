"""Round-robin CPU sharing with a finite shared-memory admission pool."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .validation import require_non_negative, require_positive, require_unique


@dataclass(frozen=True)
class Program:
    pid: str
    arrival: int
    cpu_burst: int
    memory_mb: int


@dataclass(frozen=True)
class ProgramSummary:
    pid: str
    state: str
    arrival: int
    completion: int | None
    memory_mb: int
    waiting: int | None


@dataclass(frozen=True)
class MultiprogrammingResult:
    summaries: tuple[ProgramSummary, ...]
    timeline: tuple[tuple[int, int, str], ...]
    cpu_utilization: float
    memory_utilization_peak: float
    throughput: float
    context_switches: int
    elapsed: int


def simulate(programs: list[Program], memory_capacity: int, quantum: int = 2) -> MultiprogrammingResult:
    if not programs:
        raise ValueError("Enter at least one program.")
    require_positive(memory_capacity, "Available memory")
    require_positive(quantum, "Time quantum")
    require_unique((p.pid for p in programs), "Program ID")
    for p in programs:
        if not p.pid.strip():
            raise ValueError("Program IDs cannot be blank.")
        require_non_negative(p.arrival, f"Arrival time for {p.pid}")
        require_positive(p.cpu_burst, f"CPU burst for {p.pid}")
        require_positive(p.memory_mb, f"Memory requirement for {p.pid}")
        if p.memory_mb > memory_capacity:
            raise ValueError(f"{p.pid} needs more memory than the system has available.")

    ordered = sorted(enumerate(programs), key=lambda item: (item[1].arrival, item[0]))
    remaining = {p.pid: p.cpu_burst for p in programs}
    completion: dict[str, int] = {}
    admitted: set[str] = set()
    finished: set[str] = set()
    waiting_memory: deque[Program] = deque()
    ready: deque[Program] = deque()
    active_memory = 0
    peak_memory = 0
    index = 0
    now = 0
    busy = 0
    switches = 0
    previous: str | None = None
    timeline: list[tuple[int, int, str]] = []
    first_start: dict[str, int] = {}

    def admit_available() -> None:
        nonlocal active_memory, peak_memory
        while waiting_memory and active_memory + waiting_memory[0].memory_mb <= memory_capacity:
            p = waiting_memory.popleft()
            active_memory += p.memory_mb
            peak_memory = max(peak_memory, active_memory)
            admitted.add(p.pid)
            ready.append(p)

    while len(finished) < len(programs):
        while index < len(ordered) and ordered[index][1].arrival <= now:
            p = ordered[index][1]
            waiting_memory.append(p)
            index += 1
        admit_available()
        if not ready:
            if index < len(ordered):
                now = max(now, ordered[index][1].arrival)
                continue
            if waiting_memory:
                raise ValueError("No program can be admitted with the available memory.")
            break
        p = ready.popleft()
        start = now
        first_start.setdefault(p.pid, start)
        run_for = min(quantum, remaining[p.pid])
        now += run_for
        busy += run_for
        remaining[p.pid] -= run_for
        timeline.append((start, now, p.pid))
        if previous is not None and previous != p.pid:
            switches += 1
        previous = p.pid
        while index < len(ordered) and ordered[index][1].arrival <= now:
            arrived = ordered[index][1]
            waiting_memory.append(arrived)
            index += 1
        if remaining[p.pid] == 0:
            finished.add(p.pid)
            completion[p.pid] = now
            active_memory -= p.memory_mb
            admitted.remove(p.pid)
            admit_available()
        else:
            ready.append(p)

    elapsed = now
    summaries = tuple(
        ProgramSummary(
            p.pid,
            "Completed" if p.pid in finished else "Waiting for memory",
            p.arrival,
            completion.get(p.pid),
            p.memory_mb,
            (completion[p.pid] - p.arrival - p.cpu_burst) if p.pid in completion else None,
        )
        for p in programs
    )
    utilization = 100.0 * busy / elapsed if elapsed else 0.0
    peak_utilization = 100.0 * peak_memory / memory_capacity if memory_capacity else 0.0
    throughput = len(finished) / elapsed if elapsed else 0.0
    return MultiprogrammingResult(
        summaries, tuple(timeline), utilization, peak_utilization, throughput, switches, elapsed
    )
