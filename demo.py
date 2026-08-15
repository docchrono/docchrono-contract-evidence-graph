"""Build and inspect a source-linked contract evidence graph with DocChrono."""

from __future__ import annotations

import argparse
from pathlib import Path

from docchrono import Case
from docchrono.domain import Entity, Event, Relationship

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT / "data"


def _label(node: Entity | Event) -> str:
    return node.canonical_name if isinstance(node, Entity) else node.title


def _source_filename(case: Case, document_id: str) -> str:
    document = next(item for item in case.documents if item.id == document_id)
    reference_by_id = {item.id: item for item in case.source_references}
    return reference_by_id[document.source_reference_ids[0]].filename


def _source_names(case: Case, item: Event | Relationship) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(_source_filename(case, span.document_id) for span in case.evidence(item))
    )


def _event_date(event: Event) -> str:
    starts = sorted(
        temporal.start
        for temporal in event.temporal
        if temporal.resolved and temporal.start is not None
    )
    return starts[0][:10] if starts else "undated"


def _follow_path(
    case: Case,
    start_name: str,
    path: tuple[Relationship, ...],
) -> tuple[tuple[Entity | Event, Relationship, Entity | Event], ...]:
    node_by_id = {node.id: node for node in case.graph.nodes}
    current = next(
        node
        for node in case.entities
        if node.canonical_name == start_name or start_name in node.aliases
    )
    steps: list[tuple[Entity | Event, Relationship, Entity | Event]] = []
    for relationship in path:
        next_id = (
            relationship.target_id
            if relationship.source_id == current.id
            else relationship.source_id
        )
        following = node_by_id[next_id]
        steps.append((current, relationship, following))
        current = following
    return tuple(steps)


def render(case: Case) -> str:
    """Return a stable, human-readable tour of the extracted case."""

    lines = [
        "DocChrono contract evidence graph",
        "=================================",
        f"Build complete: {case.report.complete}",
        f"Documents: {len(case.documents)}",
        f"Entities: {len(case.entities)}",
        f"Events: {len(case.events)}",
        f"Relationships: {len(case.relationships)}",
        "",
        "Dated chronology",
        "-----------------",
    ]
    for event in case.timeline:
        sources = ", ".join(_source_names(case, event))
        lines.append(f"{_event_date(event)} | {event.title} | source: {sources}")

    lines.extend(("", "Neighbors of Robert Williams", "----------------------------"))
    neighbors = case.graph.neighbors("Robert Williams")
    for node in neighbors:
        kind = "entity" if isinstance(node, Entity) else "event"
        lines.append(f"{kind}: {_label(node)}")

    path = case.graph.find_path("Robert Williams", "Payment #932")
    if path is None:
        raise RuntimeError("expected a graph path from Robert Williams to Payment #932")
    steps = _follow_path(case, "Robert Williams", path)
    lines.extend(
        (
            "",
            "Shortest evidence path: Robert Williams to Payment #932",
            "-------------------------------------------------------",
        )
    )
    for index, (left, relationship, right) in enumerate(steps, start=1):
        lines.append(f"{index}. {_label(left)} --[{relationship.type}]-- {_label(right)}")
        spans = case.evidence(relationship)
        sources = ", ".join(
            dict.fromkeys(_source_filename(case, span.document_id) for span in spans)
        )
        quotes = tuple(dict.fromkeys(span.quote for span in spans))
        lines.append(f"   source: {sources}")
        for quote in quotes:
            lines.append(f'   quote: "{quote}"')

    lines.extend(
        (
            "",
            "Interpretation",
            "--------------",
            "The graph shows source-backed connectivity, not verified truth or causation.",
        )
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "data_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing the synthetic documents",
    )
    parser.add_argument(
        "--save",
        type=Path,
        help="optionally save the complete immutable case as JSON",
    )
    args = parser.parse_args()

    case = Case.build(args.data_dir, strict=True)
    if args.save is not None:
        case.save(args.save)
    print(render(case), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
