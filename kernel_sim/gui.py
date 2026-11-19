"""Tkinter interface for the KERNEL OS Simulator."""

from __future__ import annotations

import csv
import io
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable

from . import banker, disk_scheduling, fragmentation, multiprogramming, page_replacement, paging, scheduling, segmentation
from .models import Process


BG = "#0e1013"
SIDEBAR = "#14171b"
SURFACE = "#171b20"
RAISED = "#222730"
BORDER = "#2a3039"
FG = "#e6e8eb"
MUTED = "#98a0ab"
ACCENT = "#f5a524"
GREEN = "#5bd69c"
RED = "#ff6b6b"
BLUE = "#6fa8ff"


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    default: str
    multiline: bool = False
    height: int = 6
    hint: str = ""   # dropdown choices, separated by "·"
    help: str = ""   # plain-language explanation shown under the label


@dataclass(frozen=True)
class ModuleSpec:
    title: str
    subtitle: str
    fields: tuple[FieldSpec, ...]
    run: Callable[[dict[str, str]], str]


def _int(value: str, label: str) -> int:
    try:
        return int(value.strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a whole number.") from exc


def _rows(value: str, label: str, columns: int | None = None) -> list[list[str]]:
    parsed: list[list[str]] = []
    try:
        for row in csv.reader(io.StringIO(value)):
            if not row or not any(cell.strip() for cell in row):
                continue
            cleaned = [cell.strip() for cell in row]
            if columns is not None and len(cleaned) != columns:
                raise ValueError(f"{label}: each row needs exactly {columns} comma-separated values.")
            parsed.append(cleaned)
    except csv.Error as exc:
        raise ValueError(f"{label} contains invalid CSV formatting.") from exc
    return parsed


def _number_rows(value: str, label: str, columns: int | None = None) -> list[list[int]]:
    return [[_int(v, label) for v in row] for row in _rows(value, label, columns)]


def _format_table(headers: list[str], rows: list[list[object]]) -> str:
    values = [[str(value) for value in headers], *[[str(value) for value in row] for row in rows]]
    if not values:
        return ""
    widths = [max(len(row[i]) for row in values) for i in range(len(headers))]
    divider = "-+-".join("-" * width for width in widths)
    lines = [" | ".join(value.ljust(widths[i]) for i, value in enumerate(values[0])), divider]
    lines.extend(" | ".join(value.ljust(widths[i]) for i, value in enumerate(row)) for row in values[1:])
    return "\n".join(lines)


def _vector(values: tuple[int, ...] | list[int]) -> str:
    return "[" + ", ".join(map(str, values)) + "]"


def _run_scheduling(data: dict[str, str]) -> str:
    processes = [Process(row[0], _int(row[1], "Arrival time"), _int(row[2], "Burst time"), _int(row[3], "Priority"))
                 for row in _rows(data["processes"], "Processes", 4)]
    result = scheduling.run(data["algorithm"], processes, _int(data["quantum"], "Time quantum"))
    lines = [result.algorithm, "Priority convention: lower number means higher priority.", "",
             _format_table(["Process", "AT", "BT", "Priority", "CT", "TAT", "WT", "RT"],
                           [[r.pid, r.arrival, r.burst, r.priority, r.completion, r.turnaround, r.waiting, r.response] for r in result.rows]), "",
             "GANTT CHART · see time-scaled blocks below"]
    lines.extend(["", f"Average waiting time:    {result.average_waiting:.2f}",
                  f"Average turnaround time: {result.average_turnaround:.2f}",
                  f"Average response time:   {result.average_response:.2f}",
                  f"CPU utilization:         {result.cpu_utilization:.2f}%",
                  f"Total elapsed time:      {result.makespan}"])
    return "\n".join(lines)


def _run_banker(data: dict[str, str]) -> str:
    ids = [cell.strip() for cell in data["process_ids"].split(",") if cell.strip()]
    total = [_int(cell, "Total resource count") for cell in data["total"].split(",") if cell.strip()]
    allocation = _number_rows(data["allocation"], "Allocation matrix", len(total))
    maximum = _number_rows(data["maximum"], "Maximum matrix", len(total))
    request_pid = data["request_pid"].strip()
    request_values = data["request"].strip()
    if bool(request_pid) != bool(request_values):
        raise ValueError("Enter both a request process ID and its resource vector, or leave both blank.")
    request_status = ""
    trace = ()
    if request_pid:
        request = [_int(cell, "Requested resource count") for cell in request_values.split(",") if cell.strip()]
        evaluated = banker.request_resources(ids, allocation, maximum, total, request_pid, request)
        result = evaluated.safety
        request_status = evaluated.message
        trace = evaluated.trace
    else:
        result = banker.check_safety(ids, allocation, maximum, total)
        trace = result.trace
    resources = [f"R{i + 1}" for i in range(len(total))]
    rows = [[pid, *result.need[i]] for i, pid in enumerate(ids)]
    status = "SAFE STATE" if result.safe else "UNSAFE STATE"
    sequence = " → ".join(result.safe_sequence) if result.safe else "No complete safe sequence exists."
    blocked = f"\nProcesses that could not finish: {', '.join(result.blocked)}" if result.blocked else ""
    heading = f"BANKER'S ALGORITHM — {status}"
    if request_pid:
        heading = f"{request_status}\n\n{heading} ({'state after request' if request_status.startswith('REQUEST GRANTED') else 'unchanged current state'})"
    return (heading + f"\n\nTotal resources:     {_vector(total)}"
            f"\nAvailable resources: {_vector(result.available)}\n\nNEED MATRIX\n"
            + _format_table(["Process", *resources], rows)
            + f"\n\nSafe sequence: {sequence}{blocked}"
            + "\n\n" + ("REQUEST + SAFETY TRACE" if request_pid else "SAFETY TRACE")
            + "\n" + "\n".join(trace))


def _run_paging(data: dict[str, str]) -> str:
    page_size = _int(data["page_size"], "Page size")
    table = [tuple(row) for row in _number_rows(data["page_table"], "Page table", 2)]
    result = paging.translate(page_size, table, _int(data["logical_address"], "Logical address"))
    mapping = _format_table(["Page", "Frame"], [[p, f] for p, f in table])
    return (f"PAGE TABLE\n{mapping}\n\nLogical address {result['logical_address']}"
            f" = page {result['page']} × page size {result['page_size']} + offset {result['offset']}\n"
            f"Page {result['page']} maps to frame {result['frame']}.\n"
            f"Physical address = frame × page size + offset\n"
            f"                 = {result['frame']} × {result['page_size']} + {result['offset']}\n"
            f"                 = {result['physical_address']}")


def _run_page_replacement(data: dict[str, str]) -> str:
    refs = [_int(x, "Page reference") for x in data["references"].replace("\n", ",").split(",") if x.strip()]
    result = page_replacement.simulate(refs, _int(data["frames"], "Frame count"), data["algorithm"])
    headers = ["Step", "Reference", *[f"Frame {i + 1}" for i in range(_int(data["frames"], "Frame count"))], "Result", "Replaced"]
    rows = [[s.index, s.page, *["—" if f is None else f for f in s.frames], s.result,
             "—" if s.replaced is None else s.replaced] for s in result.steps]
    return (f"{result.algorithm} · {len(result.steps)} references\n\n"
            + _format_table(headers, rows)
            + f"\n\nHits: {result.hits}    Page faults: {result.faults}    Fault rate: {result.fault_rate:.1%}")


def _run_segmentation(data: dict[str, str]) -> str:
    segments = [tuple(row) for row in _number_rows(data["segments"], "Segment table", 3)]
    result = segmentation.translate(segments, _int(data["segment"], "Segment number"), _int(data["offset"], "Offset"))
    table = _format_table(["Segment", "Base", "Limit"], [[n, base, limit] for n, base, limit in segments])
    return (f"SEGMENT TABLE\n{table}\n\nLogical address = (segment {result['segment']}, offset {result['offset']})\n"
            f"Bounds check: {result['offset']} < {result['limit']} ✓\n"
            f"Physical address = base + offset = {result['base']} + {result['offset']} = {result['physical_address']}")


def _run_fragmentation(data: dict[str, str]) -> str:
    blocks = [_int(x, "Block size") for x in data["blocks"].replace("\n", ",").split(",") if x.strip()]
    processes = [(row[0], _int(row[1], "Process size")) for row in _rows(data["processes"], "Processes", 2)]
    result = fragmentation.allocate(blocks, processes, data["mode"], data["strategy"])
    rows = [[a.process_id, a.process_size, a.block_index, a.block_size,
             a.internal_waste if result.mode == "Fixed partitions" else 0] for a in result.allocations]
    lines = [f"{result.mode} · {result.strategy}", "",
             _format_table(["Process", "Requested", "Block", "Block size", "Internal waste"], rows)]
    lines.append("\nUnallocated: " + (", ".join(result.unallocated) if result.unallocated else "none"))
    if result.mode == "Fixed partitions":
        lines.append(f"Total internal fragmentation: {result.internal_fragmentation}")
    else:
        lines.extend([f"Remaining free holes: {_vector(result.free_blocks)}",
                      f"Total free memory: {result.total_free}", f"Largest contiguous hole: {result.largest_hole}",
                      f"External fragmentation (free space outside largest hole): {result.external_fragmentation}"])
    return "\n".join(lines)


def _run_disk(data: dict[str, str]) -> str:
    requests = [_int(x, "Disk request") for x in data["requests"].replace("\n", ",").split(",") if x.strip()]
    result = disk_scheduling.schedule(requests, _int(data["head"], "Head position"), data["algorithm"],
                                     _int(data["low"], "Lower cylinder"), _int(data["high"], "Upper cylinder"), data["direction"])
    legs = " → ".join(map(str, result.path))
    movements = " + ".join(str(abs(result.path[i] - result.path[i - 1])) for i in range(1, len(result.path)))
    return (f"{result.algorithm} · direction {data['direction']}\n\nService order: "
            + " → ".join(map(str, result.service_order))
            + f"\nHead path: {legs}\n\nMovement: {movements} = {result.total_movement} cylinders")


def _run_multiprogramming(data: dict[str, str]) -> str:
    programs = [multiprogramming.Program(row[0], _int(row[1], "Arrival time"),
                                         _int(row[2], "CPU burst"), _int(row[3], "Memory requirement"))
                for row in _rows(data["programs"], "Programs", 4)]
    result = multiprogramming.simulate(programs, _int(data["memory"], "Memory capacity"), _int(data["quantum"], "Time quantum"))
    rows = [[p.pid, p.arrival, p.cpu_burst, p.memory_mb] for p in programs]
    states = [[p.pid, p.state, p.memory_mb, p.completion if p.completion is not None else "—",
               p.waiting if p.waiting is not None else "—"] for p in result.summaries]
    timeline = "  ".join(f"{start}–{end}: {pid}" for start, end, pid in result.timeline)
    return ("ROUND-ROBIN MULTIPROGRAMMING SIMULATION\n\nINPUT PROGRAMS\n"
            + _format_table(["Program", "Arrival", "CPU burst", "Memory MB"], rows)
            + "\n\nFINAL STATUS\n"
            + _format_table(["Program", "State", "Memory MB", "Completion", "Waiting"], states)
            + f"\n\nCPU timeline: {timeline}"
            + f"\nPeak memory use: {result.memory_utilization_peak:.1f}% of {data['memory']} MB"
            + f"\nCPU utilization: {result.cpu_utilization:.1f}%"
            + f"\nThroughput: {result.throughput:.3f} completed programs per time unit"
            + f"\nContext switches: {result.context_switches}"
            + f"\nElapsed time: {result.elapsed}")


MODULES: dict[str, ModuleSpec] = {
    "CPU Scheduling": ModuleSpec(
        "CPU Scheduling",
        "Choose a policy, enter any number of processes, and compare their timing results.",
        (
            FieldSpec("algorithm", "Algorithm", "FCFS",
                      hint="FCFS · SJF · SRTF (preemptive) · Priority · Round Robin"),
            FieldSpec("quantum", "Time quantum (Round Robin)", "2"),
            FieldSpec("processes", "Processes", "P1,0,4,2\nP2,1,2,1\nP3,2,3,3\nP4,3,5,2\nP5,4,6,1\nP6,5,1,2",
                      True, 8,
                      help="One per line: ID, arrival, burst, priority."),
        ),
        _run_scheduling,
    ),
    "Banker's Algorithm": ModuleSpec(
        "Banker's Algorithm",
        "Check whether the current allocation has a safe completion sequence.",
        (
            FieldSpec("process_ids", "Process IDs (comma-separated)", "P0,P1,P2,P3,P4"),
            FieldSpec("total", "Total resources (one per type)", "10,5,7"),
            FieldSpec("allocation", "Allocation matrix", "0,1,0\n2,0,0\n3,0,2\n2,1,1\n0,0,2", True, 6,
                      help="One row per process; one value per resource."),
            FieldSpec("maximum", "Maximum demand matrix", "7,5,3\n3,2,2\n9,0,2\n2,2,2\n4,3,3", True, 6,
                      help="Use the same process and resource order as Allocation."),
            FieldSpec("request_pid", "Optional request process ID", "", help="Leave blank to run only the safety check."),
            FieldSpec("request", "Optional resource request", "", help="Comma-separated amount per resource, e.g. 1,0,2."),
        ),
        _run_banker,
    ),
    "Paging": ModuleSpec(
        "Paging",
        "Map logical pages to physical frames and translate a logical address.",
        (
            FieldSpec("page_size", "Page size", "4"),
            FieldSpec("logical_address", "Logical address", "3"),
            FieldSpec("page_table", "Page table", "0,5\n1,6\n2,3\n3,2", True, 7,
                      help="One mapping per line: page, frame."),
        ),
        _run_paging,
    ),
    "Page Replacement": ModuleSpec(
        "Page Replacement",
        "Follow each page reference through memory frames and compare hits with faults.",
        (
            FieldSpec("algorithm", "Algorithm", "FIFO", hint="FIFO · LRU · Optimal"),
            FieldSpec("frames", "Number of frames", "3"),
            FieldSpec("references", "Page reference string", "7,0,1,2,0,3,0,4,2,3,0,3,2", True, 7,
                      help="Comma-separated or one page per line."),
        ),
        _run_page_replacement,
    ),
    "Segmentation": ModuleSpec(
        "Segmentation",
        "Validate a segment and offset against its base and limit.",
        (
            FieldSpec("segment", "Segment number", "1"),
            FieldSpec("offset", "Offset within segment", "399"),
            FieldSpec("segments", "Segment table", "0,1400,1000\n1,6300,400\n2,4300,400\n3,3200,1100\n4,4700,1000", True, 7,
                      help="One per line: segment, base, limit."),
        ),
        _run_segmentation,
    ),
    "Fragmentation": ModuleSpec(
        "Fragmentation",
        "Allocate processes into memory and inspect the space that remains unused.",
        (
            FieldSpec("mode", "Partition mode", "Variable partitions", hint="Fixed partitions · Variable partitions"),
            FieldSpec("strategy", "Allocation strategy", "First fit", hint="First fit · Best fit · Next fit · Worst fit"),
            FieldSpec("blocks", "Memory blocks (comma-separated)", "100,500,200,300,600"),
            FieldSpec("processes", "Processes", "P1,212\nP2,417\nP3,112\nP4,426", True, 7,
                      help="One per line: ID, size."),
        ),
        _run_fragmentation,
    ),
    "Disk Scheduling": ModuleSpec(
        "Disk Scheduling",
        "Compare head movement for common disk request ordering algorithms.",
        (
            FieldSpec("algorithm", "Algorithm", "SCAN", hint="FCFS · SSTF · SCAN · C-SCAN · LOOK · C-LOOK"),
            FieldSpec("direction", "Initial direction", "Right", hint="Left · Right"),
            FieldSpec("head", "Starting head position", "53"),
            FieldSpec("low", "Lowest cylinder", "0"),
            FieldSpec("high", "Highest cylinder", "199"),
            FieldSpec("requests", "Requests", "98,183,37,122,14,124,65,67", True, 7,
                      help="Comma-separated or one cylinder per line."),
        ),
        _run_disk,
    ),
    "Multiprogramming": ModuleSpec(
        "Multiprogramming",
        "Share CPU time and a finite memory pool across programs with flexible input.",
        (
            FieldSpec("memory", "Available memory (MB)", "1024"),
            FieldSpec("quantum", "CPU time slice", "2"),
            FieldSpec("programs", "Programs", "A,0,5,400\nB,1,3,300\nC,2,4,500\nD,3,2,256", True, 8,
                      help="One per line: ID, arrival, CPU burst, memory (MB)."),
        ),
        _run_multiprogramming,
    ),
}


PROCESS_COLORS = ("#d99a2b", "#398c82", "#536fc4", "#a45d8a", "#57885d", "#bd684f", "#547f9c")


class OverviewPage(ttk.Frame):
    """Project landing page with the team and a quick module index."""

    def __init__(self, parent: tk.Misc, open_module: Callable[[str], None]):
        super().__init__(parent, style="App.TFrame", padding=(30, 26))
        self._build(open_module)

    def _build(self, open_module: Callable[[str], None]) -> None:
        ttk.Label(self, text="KERNEL", style="PageTitle.TLabel").pack(anchor="w")
        ttk.Label(self, text="Operating System Simulator", style="Subtitle.TLabel").pack(anchor="w", pady=(4, 16))
        hero = tk.Frame(self, bg=SURFACE, padx=22, pady=18)
        hero.pack(fill="x", pady=(0, 16))
        tk.Label(hero, text="Explore core operating system algorithms", bg=SURFACE, fg=FG,
                 font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(hero, text="Run simulations, edit examples, and follow each algorithm's output step by step.",
                 bg=SURFACE, fg=MUTED, font=("Segoe UI", 10), wraplength=900,
                 justify="left").pack(anchor="w", pady=(6, 12))
        ttk.Button(hero, text="Open CPU Scheduling", style="Accent.TButton",
                   command=lambda: open_module("CPU Scheduling")).pack(anchor="w")

        ttk.Label(self, text="PROJECT MODULES", style="PageTitle.TLabel").pack(anchor="w", pady=(2, 10))
        cards = tk.Frame(self, bg=BG)
        cards.pack(fill="x")
        for index, title in enumerate(MODULES):
            row, col = divmod(index, 2)
            cards.grid_columnconfigure(col, weight=1, uniform="module")
            card = tk.Frame(cards, bg=SURFACE, padx=16, pady=12)
            card.grid(row=row, column=col, sticky="ew", padx=(0, 8) if col == 0 else (8, 0), pady=5)
            tk.Label(card, text=title, bg=SURFACE, fg=ACCENT,
                     font=("Segoe UI", 11, "bold")).pack(anchor="w")
            tk.Label(card, text=MODULES[title].subtitle, bg=SURFACE, fg=MUTED,
                     font=("Segoe UI", 9), wraplength=430, justify="left").pack(anchor="w", pady=(4, 8))
            ttk.Button(card, text="Open module", style="Quiet.TButton",
                       command=lambda name=title: open_module(name)).pack(anchor="w")

        ttk.Label(self, text="PROJECT TEAM", style="PageTitle.TLabel").pack(anchor="w", pady=(18, 10))
        team = tk.Frame(self, bg=BG)
        team.pack(fill="x")
        members = (("Amiel Amido", "Group creator"),
                   ("Kevin James Riparip", "Project team"),
                   ("Rafael Carlos III", "Project team"))
        for col, (name, role) in enumerate(members):
            team.grid_columnconfigure(col, weight=1, uniform="team")
            card = tk.Frame(team, bg=SURFACE, padx=16, pady=12)
            card.grid(row=0, column=col, sticky="ew", padx=(0, 6) if col == 0 else (6, 0))
            tk.Label(card, text=name, bg=SURFACE, fg=FG, font=("Segoe UI", 11, "bold")).pack(anchor="w")
            tk.Label(card, text=role, bg=SURFACE, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))


class ModulePage(ttk.Frame):
    def __init__(self, parent: tk.Misc, spec: ModuleSpec):
        super().__init__(parent, style="App.TFrame", padding=(26, 22))
        self.spec = spec
        self.widgets: dict[str, tk.Widget] = {}
        self.gantt_canvas: tk.Canvas | None = None
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text=self.spec.title, style="PageTitle.TLabel").pack(anchor="w")
        ttk.Label(self, text=self.spec.subtitle, style="Subtitle.TLabel", wraplength=900).pack(
            anchor="w", pady=(5, 18))

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)

        input_panel = ttk.Frame(body, style="Panel.TFrame", padding=16, width=480)
        output_panel = ttk.Frame(body, style="Panel.TFrame", padding=16)
        body.add(input_panel, weight=0)
        body.add(output_panel, weight=1)
        input_panel.pack_propagate(False)

        ttk.Label(input_panel, text="INPUTS", style="SectionLabel.TLabel").pack(anchor="w", pady=(0, 10))

        # Run controls live in a fixed footer so they never scroll out of view.
        footer = ttk.Frame(input_panel, style="Panel.TFrame")
        footer.pack(side="bottom", fill="x", pady=(10, 0))
        ttk.Separator(footer, orient="horizontal").pack(fill="x", pady=(0, 10))
        action_row = ttk.Frame(footer, style="Panel.TFrame")
        action_row.pack(fill="x")
        ttk.Button(action_row, text="▶  Run simulation", style="Accent.TButton", command=self.run_simulation).pack(side="left")
        ttk.Button(action_row, text="Load example", style="Quiet.TButton", command=self.reset_sample).pack(side="left", padx=(8, 0))
        self.status = ttk.Label(footer, text="Ready · input is checked when you run", style="Hint.TLabel", wraplength=430)
        self.status.pack(anchor="w", pady=(10, 0))

        form = tk.Frame(input_panel, bg=SURFACE)
        form.pack(fill="both", expand=True)
        form.rowconfigure(0, weight=1)
        form.columnconfigure(0, weight=1)
        canvas = tk.Canvas(form, bg=SURFACE, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(form, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        fields_frame = ttk.Frame(canvas, style="Panel.TFrame", padding=(0, 0, 10, 0))
        fields_window = canvas.create_window((0, 0), window=fields_frame, anchor="nw")

        def update_scroll_region(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def fit_form_width(event: tk.Event) -> None:
            canvas.itemconfigure(fields_window, width=event.width)

        fields_frame.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", fit_form_width)
        canvas.bind("<Enter>", lambda _event: canvas.bind_all(
            "<MouseWheel>", lambda event: canvas.yview_scroll(-1 * (event.delta // 120), "units")))
        canvas.bind("<Leave>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        for field in self.spec.fields:
            group = ttk.Frame(fields_frame, style="Panel.TFrame")
            group.pack(fill="x", pady=(0, 12))
            ttk.Label(group, text=field.label, style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 2))
            if field.multiline and field.help:
                ttk.Label(group, text=field.help, style="Hint.TLabel", wraplength=410,
                          justify="left").pack(anchor="w", pady=(0, 4))
            if field.multiline:
                editor = tk.Frame(group, bg=SURFACE)
                editor.pack(fill="x")
                editor.columnconfigure(0, weight=1)
                widget = tk.Text(editor, height=field.height, wrap="none", undo=True,
                                 font=("Cascadia Mono", 10), bg="#0b0e11", fg=FG,
                                 insertbackground=ACCENT, selectbackground="#3b3323",
                                 relief="flat", padx=9, pady=7, highlightthickness=1,
                                 highlightbackground=BORDER, highlightcolor=ACCENT)
                widget.insert("1.0", field.default)
                widget.grid(row=0, column=0, sticky="nsew")
                y_bar = ttk.Scrollbar(editor, orient="vertical", command=widget.yview)
                x_bar = ttk.Scrollbar(editor, orient="horizontal", command=widget.xview)
                y_bar.grid(row=0, column=1, sticky="ns")
                x_bar.grid(row=1, column=0, sticky="ew")
                widget.configure(yscrollcommand=y_bar.set, xscrollcommand=x_bar.set)
                # Tab moves between fields instead of typing a tab character.
                widget.bind("<Tab>", self._focus_next)
                widget.bind("<Shift-Tab>", self._focus_previous)
            elif field.hint:
                values = [item.strip() for item in field.hint.split("·")]
                widget = ttk.Combobox(group, values=values, state="readonly", style="Kernel.TCombobox")
                widget.set(field.default)
                widget.pack(fill="x")
            else:
                widget = ttk.Entry(group, style="Kernel.TEntry")
                widget.insert(0, field.default)
                widget.pack(fill="x")
            widget.bind("<Control-Return>", self._shortcut_run)
            self.widgets[field.key] = widget

        heading = ttk.Frame(output_panel, style="Panel.TFrame")
        heading.pack(fill="x", pady=(0, 6))
        ttk.Label(heading, text="SIMULATION OUTPUT", style="SectionLabel.TLabel").pack(side="left")
        if self.spec.title == "CPU Scheduling":
            chart_panel = tk.Frame(output_panel, bg=SURFACE)
            chart_panel.pack(fill="x", pady=(0, 10))
            tk.Label(chart_panel, text="GANTT CHART", bg=SURFACE, fg=ACCENT,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
            self.gantt_canvas = tk.Canvas(chart_panel, height=112, bg="#0b0e11",
                                          highlightthickness=1, highlightbackground=BORDER,
                                          borderwidth=0)
            self.gantt_canvas.pack(fill="x")
            gantt_scroll = ttk.Scrollbar(chart_panel, orient="horizontal", command=self.gantt_canvas.xview)
            gantt_scroll.pack(fill="x")
            self.gantt_canvas.configure(xscrollcommand=gantt_scroll.set)

        output_frame = tk.Frame(output_panel, bg=SURFACE)
        output_frame.pack(fill="both", expand=True)
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        self.output = tk.Text(output_frame, wrap="none", state="disabled", font=("Cascadia Mono", 10),
                              bg="#0b0e11", fg=FG, insertbackground=ACCENT, selectbackground="#3b3323",
                              relief="flat", padx=14, pady=12, highlightthickness=1,
                              highlightbackground=BORDER, highlightcolor=ACCENT)
        self.output.tag_configure("error", foreground=RED)
        self.output.tag_configure("success", foreground=GREEN)
        self.output.tag_configure("heading", foreground=ACCENT, font=("Cascadia Mono", 10, "bold"))
        self.output.tag_configure("good", foreground=GREEN, font=("Cascadia Mono", 10, "bold"))
        self.output.tag_configure("bad", foreground=RED, font=("Cascadia Mono", 10, "bold"))
        self.output.grid(row=0, column=0, sticky="nsew")
        ybar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output.yview)
        xbar = ttk.Scrollbar(output_frame, orient="horizontal", command=self.output.xview)
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        self.output.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self._write_output("Choose or edit the inputs, then run the simulation.\n\n"
                           "Add as many input rows as you need.")

    # ----- keyboard helpers -------------------------------------------------
    @staticmethod
    def _focus_next(event: tk.Event) -> str:
        event.widget.tk_focusNext().focus_set()
        return "break"

    @staticmethod
    def _focus_previous(event: tk.Event) -> str:
        event.widget.tk_focusPrev().focus_set()
        return "break"

    def _shortcut_run(self, _event: tk.Event) -> str:
        self.run_simulation()
        return "break"

    # ----- actions ----------------------------------------------------------
    def read_values(self) -> dict[str, str]:
        values: dict[str, str] = {}
        for field in self.spec.fields:
            widget = self.widgets[field.key]
            if isinstance(widget, tk.Text):
                values[field.key] = widget.get("1.0", "end-1c").strip()
            else:
                values[field.key] = widget.get().strip()  # type: ignore[union-attr]
        return values

    def run_simulation(self) -> None:
        try:
            result = self.spec.run(self.read_values())
        except ValueError as exc:
            message = str(exc)
        except (KeyError, IndexError):
            message = "A row is missing a value or has an extra one. Check that every line follows the format shown above its box."
        except Exception as exc:  # keep the window alive whatever the input is
            message = f"Something unexpected happened while running: {exc}"
        else:
            self._write_output(result)
            if self.gantt_canvas is not None:
                try:
                    self._draw_gantt(self.read_values())
                except (ValueError, KeyError, IndexError):
                    self._clear_gantt()
            self.status.configure(text="Simulation complete", foreground=GREEN)
            return
        if self.gantt_canvas is not None:
            self._clear_gantt()
        self._write_output(f"INPUT NEEDS ATTENTION\n\n{message}\n\nCorrect the inputs and try again.", "error")
        self.status.configure(text="Could not run · check the input", foreground=RED)

    def reset_sample(self) -> None:
        for field in self.spec.fields:
            widget = self.widgets[field.key]
            if isinstance(widget, tk.Text):
                widget.delete("1.0", "end")
                widget.insert("1.0", field.default)
            elif isinstance(widget, ttk.Combobox):
                widget.set(field.default)
            else:
                widget.delete(0, "end")  # type: ignore[union-attr]
                widget.insert(0, field.default)  # type: ignore[union-attr]
        self.status.configure(text="Example inputs restored", foreground=MUTED)
        if self.gantt_canvas is not None:
            self._clear_gantt()
        self._write_output("Example inputs restored. Press Run simulation to view the results.")

    def _clear_gantt(self) -> None:
        if self.gantt_canvas is not None:
            self.gantt_canvas.delete("all")
            self.gantt_canvas.configure(scrollregion=(0, 0, 1, 1))

    def _draw_gantt(self, data: dict[str, str]) -> None:
        if self.gantt_canvas is None:
            return
        processes = [Process(row[0], _int(row[1], "Arrival time"), _int(row[2], "Burst time"),
                             _int(row[3], "Priority"))
                     for row in _rows(data["processes"], "Processes", 4)]
        result = scheduling.run(data["algorithm"], processes, _int(data["quantum"], "Time quantum"))
        canvas = self.gantt_canvas
        canvas.delete("all")
        left, right, top, bottom = 28, 20, 24, 66
        unit = 48
        extent = max(1, result.makespan)
        width = left + extent * unit + right
        colors = {process.pid: PROCESS_COLORS[index % len(PROCESS_COLORS)]
                  for index, process in enumerate(processes)}
        canvas.create_text(left, 10, anchor="w", text="CPU time", fill=MUTED,
                           font=("Segoe UI", 8))
        if not result.timeline:
            canvas.create_text(left, 48, anchor="w", text="No scheduled intervals", fill=MUTED)
        for interval in result.timeline:
            x1 = left + interval.start * unit
            x2 = left + interval.end * unit
            color = colors.get(interval.pid, "#353b44") if interval.pid else "#242a32"
            canvas.create_rectangle(x1, top, x2, bottom, fill=color, outline="#0b0e11", width=2)
            label = interval.pid or "IDLE"
            if x2 - x1 >= 32:
                canvas.create_text((x1 + x2) / 2, (top + bottom) / 2, text=label,
                                  fill="#ffffff", font=("Segoe UI", 9, "bold"))
        boundaries = {0, result.makespan}
        for interval in result.timeline:
            boundaries.add(interval.start)
            boundaries.add(interval.end)
        for tick in sorted(boundaries):
            x = left + tick * unit
            canvas.create_line(x, bottom + 2, x, bottom + 8, fill=MUTED)
            canvas.create_text(x, bottom + 13, text=str(tick), fill=FG,
                               font=("Cascadia Mono", 8))
        canvas.configure(scrollregion=(0, 0, width, 92))

    def _write_output(self, content: str, tag: str | None = None) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        if tag:
            self.output.insert("1.0", content, tag)
        else:
            self.output.insert("1.0", content)
            self._highlight()
        self.output.configure(state="disabled")

    def _highlight(self) -> None:
        """Colour section titles and the safe/unsafe verdict so the key lines stand out."""
        for number, line in enumerate(self.output.get("1.0", "end-1c").splitlines(), start=1):
            text = line.strip()
            if not text:
                continue
            if "UNSAFE STATE" in text:
                tag = "bad"
            elif "SAFE STATE" in text:
                tag = "good"
            elif text.isupper() and not any(ch.isdigit() or ch == "|" for ch in text):
                tag = "heading"
            else:
                continue
            self.output.tag_add(tag, f"{number}.0", f"{number}.end")


class KernelApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("KERNEL · Operating System Simulator")
        self.geometry("1440x920")
        self.minsize(1100, 720)
        self.configure(bg=BG)
        self._style()
        self.order = ["Overview", *MODULES]
        self.current = "Overview"
        self.pages: dict[str, ModulePage | OverviewPage] = {}
        self.nav_buttons: dict[str, ttk.Button] = {}
        self._build_shell()
        self._bind_shortcuts()
        self.show_module("Overview")

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background=BG)
        style.configure("Panel.TFrame", background=SURFACE)
        style.configure("Sidebar.TFrame", background=SIDEBAR)
        style.configure("PageTitle.TLabel", background=BG, foreground=FG,
                        font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED,
                        font=("Segoe UI", 11))
        style.configure("SectionLabel.TLabel", background=SURFACE, foreground=ACCENT,
                        font=("Segoe UI", 10, "bold"))
        style.configure("FieldLabel.TLabel", background=SURFACE, foreground=FG,
                        font=("Segoe UI", 10, "bold"))
        style.configure("Hint.TLabel", background=SURFACE, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("Kernel.TEntry", fieldbackground="#0b0e11", foreground=FG,
                        insertcolor=ACCENT, bordercolor=BORDER, lightcolor=ACCENT,
                        darkcolor=BORDER, padding=(8, 7))
        style.configure("Kernel.TCombobox", fieldbackground="#0b0e11", background=RAISED,
                        foreground=FG, arrowcolor=ACCENT, bordercolor=BORDER,
                        lightcolor=ACCENT, darkcolor=BORDER, padding=(8, 7))
        style.map("Kernel.TCombobox", fieldbackground=[("readonly", "#0b0e11")],
                  foreground=[("readonly", FG)])
        style.configure("Accent.TButton", background=ACCENT, foreground="#211706",
                        font=("Segoe UI", 10, "bold"), padding=(12, 8), borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#ffc04d")])
        style.configure("Quiet.TButton", background=RAISED, foreground=FG,
                        font=("Segoe UI", 9), padding=(10, 8), borderwidth=0)
        style.map("Quiet.TButton", background=[("active", "#303742")],
                  foreground=[("disabled", "#5b626c")])
        style.configure("Nav.TButton", background=SIDEBAR, foreground=MUTED,
                        font=("Segoe UI", 10), anchor="w", padding=(12, 10), borderwidth=0)
        style.map("Nav.TButton", background=[("active", RAISED)], foreground=[("active", FG)])
        style.configure("NavSelected.TButton", background="#2a2113", foreground=ACCENT,
                        font=("Segoe UI", 10, "bold"), anchor="w", padding=(12, 10), borderwidth=0)
        style.configure("TSeparator", background=BORDER)

    def _build_shell(self) -> None:
        header = tk.Frame(self, bg=SIDEBAR, height=56, highlightthickness=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="■  KERNEL", bg=SIDEBAR, fg=FG,
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=(20, 10))
        tk.Label(header, text="OPERATING SYSTEM SIMULATOR", bg=SIDEBAR, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(header, text="SIMULATION READY", bg=SIDEBAR, fg=GREEN,
                 font=("Segoe UI", 9, "bold")).pack(side="right", padx=22)
        ttk.Separator(self, orient="horizontal").pack(fill="x")

        workspace = ttk.Frame(self, style="App.TFrame")
        workspace.pack(fill="both", expand=True)
        workspace.columnconfigure(1, weight=1)
        workspace.rowconfigure(0, weight=1)
        sidebar = ttk.Frame(workspace, style="Sidebar.TFrame", width=248, padding=(14, 20))
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        ttk.Label(sidebar, text="PROJECT", style="Hint.TLabel").pack(anchor="w", padx=8, pady=(0, 8))
        for title in self.order:
            button = ttk.Button(sidebar, text=title, style="Nav.TButton",
                                command=lambda name=title: self.show_module(name))
            button.pack(fill="x", pady=2)
            self.nav_buttons[title] = button
            if title == "Overview":
                ttk.Label(sidebar, text="SIMULATOR MODULES", style="Hint.TLabel").pack(
                    anchor="w", padx=8, pady=(14, 8))
        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", pady=(18, 12))
        tk.Label(sidebar, text="Add rows as needed.\nInputs are checked before each run.",
                 bg=SIDEBAR, fg=MUTED, justify="left", font=("Segoe UI", 9),
                 wraplength=200).pack(anchor="w", padx=8)

        self.content = ttk.Frame(workspace, style="App.TFrame")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)
        overview = OverviewPage(self.content, self.show_module)
        overview.grid(row=0, column=0, sticky="nsew")
        self.pages["Overview"] = overview
        for title, spec in MODULES.items():
            page = ModulePage(self.content, spec)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[title] = page

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-Return>", lambda _event: self._run_current_simulation())
        self.bind_all("<F5>", lambda _event: self._run_current_simulation())

    def _run_current_simulation(self) -> None:
        page = self.pages.get(self.current)
        if isinstance(page, ModulePage):
            page.run_simulation()

    def show_module(self, title: str) -> None:
        self.current = title
        page = self.pages[title]
        page.tkraise()
        for name, button in self.nav_buttons.items():
            button.configure(style="NavSelected.TButton" if name == title else "Nav.TButton")


def launch() -> None:
    app = KernelApp()
    app.mainloop()
