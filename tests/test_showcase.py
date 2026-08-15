from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from demo import render

from docchrono import Case
from docchrono.domain import Entity, Event

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def _label(node: Entity | Event) -> str:
    return node.canonical_name if isinstance(node, Entity) else node.title


def _source_filename(case: Case, document_id: str) -> str:
    document_by_id = {document.id: document for document in case.documents}
    reference_by_id = {reference.id: reference for reference in case.source_references}
    document = document_by_id[document_id]
    return reference_by_id[document.source_reference_ids[0]].filename


def test_committed_synthetic_data_is_reproducible() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "generate_data.py"), "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "Synthetic data is up to date.\n"


def test_contract_case_builds_with_mixed_formats_and_exact_provenance() -> None:
    case = Case.build(DATA_DIR, strict=True)

    assert case.report.complete
    assert {reference.filename for reference in case.source_references} == {
        "approval.md",
        "contract_record.docx",
        "payment.eml",
    }
    assert {document.media_type for document in case.documents} == {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "message/rfc822",
        "text/markdown",
    }

    document_by_id = {document.id: document for document in case.documents}
    for span in case.evidence_spans:
        document = document_by_id[span.document_id]
        assert document.raw_text[span.raw_start : span.raw_end] == span.quote
        assert span.normalized_start is not None
        assert span.normalized_end is not None
        assert document.normalized_to_raw[span.normalized_start] == span.raw_start
        assert document.normalized_to_raw[span.normalized_end] == span.raw_end


def test_neighbors_path_quotes_and_saved_case_round_trip(tmp_path: Path) -> None:
    case = Case.build(DATA_DIR, strict=True)

    assert [_label(node) for node in case.graph.neighbors("Robert Williams")] == [
        "Approved: Contract #428"
    ]
    path = case.graph.find_path("Robert Williams", "Payment #932")
    assert path is not None
    assert [relationship.type for relationship in path] == [
        "PARTICIPATED_IN",
        "PARTICIPATED_IN",
        "PARTICIPATED_IN",
        "PARTICIPATED_IN",
    ]
    assert [
        tuple(_source_filename(case, span.document_id) for span in case.evidence(edge))
        for edge in path
    ] == [
        ("approval.md",),
        ("approval.md",),
        ("payment.eml",),
        ("payment.eml",),
    ]
    assert [tuple(span.quote for span in case.evidence(edge)) for edge in path] == [
        ("Robert Williams approved Contract #428",),
        ("Robert Williams approved Contract #428",),
        ("Acme Corporation paid Payment #932 for Contract #428",),
        ("Acme Corporation paid Payment #932 for Contract #428",),
    ]

    saved = case.save(tmp_path / "contract.case.json")
    loaded = Case.load(saved)
    assert loaded.data == case.data
    assert loaded.graph.find_path("Robert Williams", "Payment #932") == path
    for edge in loaded.graph.find_path("Robert Williams", "Payment #932") or ():
        assert loaded.evidence(edge) == case.evidence(edge)


def test_rendered_demo_matches_committed_expected_output() -> None:
    expected = (ROOT / "expected_output.txt").read_text(encoding="utf-8")
    assert render(Case.build(DATA_DIR, strict=True)) == expected
