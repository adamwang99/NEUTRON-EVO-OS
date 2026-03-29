#!/usr/bin/env python3
"""
NEUTRON-EVO-OS: Evolution Dashboard
Terminal UI with rich library showing real-time CI and [STATUS: DREAMING]
"""
import time
import sys
import threading
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
except ImportError:
    print("ERROR: rich>=13.0.0 required. Run: pip install rich")
    sys.exit(1)

console = Console()

LEDGER_PATH = "PERFORMANCE_LEDGER.md"
SKILLS = ["context", "memory", "workflow", "engine"]


def parse_ledger() -> dict:
    """Parse skills section from PERFORMANCE_LEDGER.md."""
    try:
        content = open(LEDGER_PATH).read()
    except FileNotFoundError:
        return {"skills": {s: {"CI": 50, "tasks": 0, "last_active": "-"} for s in SKILLS}}

    import re
    skills = {}
    for skill in SKILLS:
        match = re.search(
            rf"^\|\s*{re.escape(skill)}\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(.*?)\s*\|",
            content,
            re.MULTILINE,
        )
        if match:
            skills[skill] = {
                "CI": int(match.group(1)),
                "tasks": int(match.group(2)),
                "last_active": match.group(3).strip(),
            }
        else:
            skills[skill] = {"CI": 50, "tasks": 0, "last_active": "-"}
    return {"skills": skills}


def ci_style(ci: int) -> str:
    if ci >= 70:
        return "bold green"
    elif ci >= 40:
        return "bold yellow"
    else:
        return "bold red"


def render_dashboard(status: str = "AWAKE", cycle_count: int = 0) -> Table:
    ledger = parse_ledger()

    table = Table(
        title="NEUTRON-EVO-OS // Evolution Dashboard",
        box=box.ROUNDED,
        show_lines=True,
        pad_edge=False,
    )
    table.add_column("Skill", style="cyan bold", width=16)
    table.add_column("CI", justify="right", width=6)
    table.add_column("Tasks", justify="right", width=8)
    table.add_column("Last Active", style="dim", width=14)
    table.add_column("Status", width=20)

    for skill, data in ledger.get("skills", {}).items():
        ci = data.get("CI", 50)
        ci_str = f"[{ci_style(ci)}]{ci}[/]"
        if ci >= 70:
            skill_status = "[green]● TRUSTED[/]"
        elif ci >= 40:
            skill_status = "[yellow]● NORMAL[/]"
        elif ci >= 30:
            skill_status = "[red]● RESTRICTED[/]"
        else:
            skill_status = "[red bold]■ BLOCKED[/]"

        table.add_row(
            skill,
            ci_str,
            str(data.get("tasks", 0)),
            data.get("last_active", "-"),
            skill_status,
        )

    return table


def render_header(status: str, cycle_count: int) -> Panel:
    status_color = "green" if status == "AWAKE" else "magenta"
    uptime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header_text = Text.assemble(
        f"[bold magenta]NEUTRON-EVO-OS[/bold magenta]  ",
        f"[dim]//[/dim]  ",
        f"[{status_color} bold]{status}[/{status_color}]  ",
        f"[dim]//[/dim]  ",
        f"[dim]Up: {uptime}[/dim]  ",
        f"[dim]//[/dim]  ",
        f"[dim]Dreams: {cycle_count}[/dim]",
    )
    return Panel(
        header_text,
        border_style="dim",
        box=box.SQUARE,
        padding=(0, 1),
    )


def start_dashboard(refresh_seconds: int = 10):
    """Start the live dashboard loop."""
    cycle_count = 0
    status = "AWAKE"

    console.print(
        "\n[bold magenta]\n"
        "  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗\n"
        "  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝\n"
        "  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗\n"
        "  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║\n"
        "  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║\n"
        "  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝\n"
        "  EVO-OS v4.0.0 // ∫f(t)dt // Functional Credibility Over Institutional Inertia"
        "[/bold magenta]\n"
    )

    console.print("[dim]Evolution Dashboard — press Ctrl+C to exit[/dim]\n")

    try:
        with Live(
            console=console,
            refresh_per_second=0.5,
            transient=False,
        ) as live:
            while True:
                table = render_dashboard(status=status, cycle_count=cycle_count)
                header = render_header(status=status, cycle_count=cycle_count)
                live.update(
                    Table.from_markdown(f"\n{header}\n") if False else table,
                    refresh=True,
                )
                time.sleep(refresh_seconds)
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard stopped.[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    refresh = 10
    if len(sys.argv) > 1:
        try:
            refresh = int(sys.argv[1])
        except ValueError:
            pass

    start_dashboard(refresh_seconds=refresh)
