# Contract Evidence Graph with DocChrono

[![CI](https://github.com/docchrono/docchrono-contract-evidence-graph/actions/workflows/ci.yml/badge.svg)](https://github.com/docchrono/docchrono-contract-evidence-graph/actions/workflows/ci.yml)
[![DocChrono 0.1.0](https://img.shields.io/badge/DocChrono-0.1.0-3776ab)](https://pypi.org/project/docchrono/0.1.0/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

This runnable example turns three fictional contract records into a chronology and an
evidence graph with [`docchrono==0.1.0`](https://pypi.org/project/docchrono/0.1.0/).
It demonstrates the two graph questions that are usually most useful at the start of a
document review:

1. What is directly connected to a person or record?
2. Is there a source-backed path between two named items, and which exact quotations support
   every edge?

Everything runs locally. No API key, cloud model, or network service is used while building the
case.

> **Synthetic data only:** Acme Corporation, every person, address, contract, and payment in
> this repository are fictional and were created for this demonstration. They do not describe
> real people or transactions.

## What the example discovers

The committed inputs produce this shortest path:

```text
Robert Williams
    --[PARTICIPATED_IN]-- Approved: Contract #428
    --[PARTICIPATED_IN]-- Contract #428
    --[PARTICIPATED_IN]-- Paid: Payment #932 for Contract #428
    --[PARTICIPATED_IN]-- Payment #932
```

The path is backed by two exact source quotations:

```text
approval.md: "Robert Williams approved Contract #428"
payment.eml: "Acme Corporation paid Payment #932 for Contract #428"
```

See [`expected_output.txt`](expected_output.txt) for the full verified run, including document,
entity, event, and relationship counts and the dated chronology.

## Quick start

DocChrono supports CPython 3.11 through 3.13. From a clone of this repository:

```bash
python -m venv .venv
source .venv/bin/activate          # macOS or Linux
python -m pip install -r requirements.txt
python demo.py
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python demo.py
```

To persist the complete immutable case and inspect it later:

```bash
python demo.py --save contract.case.json
docchrono inspect contract.case.json
docchrono timeline contract.case.json
```

The full case file retains raw extracted text, evidence quotations, and source paths. Treat it as
sensitive when you adapt this example to real records. `case.save_sanitized(...)` removes full
document text for sharing, but retains evidence quotations and cannot provide the same raw-text
round-trip verification.

## The synthetic collection

| File | Format | Source statement demonstrated |
| --- | --- | --- |
| [`contract_record.docx`](data/contract_record.docx) | Word | Acme Corporation signed Contract #428 on January 5 |
| [`approval.md`](data/approval.md) | Markdown | Robert Williams approved Contract #428 on January 12 |
| [`payment.eml`](data/payment.eml) | RFC 822 email | Acme Corporation paid Payment #932 for Contract #428 on January 20 |

The email headers also yield a separate `Email Sent` event. This is why the verified result has
four events even though there are three files.

## API walkthrough

### 1. Build a strict case

```python
from docchrono import Case

case = Case.build("data", strict=True)
assert case.report.complete
```

`strict=True` makes a parse or extraction failure fail the run instead of quietly returning a
partial collection.

### 2. Inspect direct neighbors

```python
for node in case.graph.neighbors("Robert Williams"):
    print(node.title)
```

For these inputs, the direct neighbor is the provisional event
`Approved: Contract #428`.

### 3. Find a path

```python
path = case.graph.find_path("Robert Williams", "Payment #932")
assert path is not None

for relationship in path:
    print(relationship.type, relationship.score)
```

`find_path` traverses graph connectivity in either direction; each returned `Relationship`
retains its original source and target identifiers. A shortest path proves that extracted graph
nodes are connected. It does **not** prove causation, contractual validity, or that a source
statement is true.

### 4. Trace every edge to source text

```python
document_by_id = {document.id: document for document in case.documents}
reference_by_id = {reference.id: reference for reference in case.source_references}

for relationship in path:
    for span in case.evidence(relationship):
        document = document_by_id[span.document_id]
        reference = reference_by_id[document.source_reference_ids[0]]
        assert document.raw_text[span.raw_start : span.raw_end] == span.quote
        print(reference.filename, repr(span.quote))
```

That slice assertion is the important provenance check: the reported quotation is exactly the
text at the retained raw offsets, not a generated summary.

### 5. Read the chronology

```python
for event in case.timeline:
    print(event.title, event.temporal)

for event in case.timeline.undated:
    print("UNDATED", event.title)
```

Timeline iteration intentionally contains dated events only. Undated findings remain available
in the explicit `undated` collection.

## Rebuild and verify the data

The DOCX is generated with fixed document properties, sorted uncompressed ZIP members, a fixed
ZIP timestamp, and pinned `python-docx`/`lxml` versions so its committed bytes are reproducible
across the tested Python versions.

```bash
python generate_data.py          # rebuild all three files
python generate_data.py --check  # compare committed files byte for byte
```

Run the complete verification suite with:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The tests verify mixed-format ingestion, the exact neighbor and path, every source filename and
quote on that path, raw-offset round trips, saved-case load equality, deterministic generated
bytes, and the complete displayed output. GitHub Actions repeats the checks on Python 3.11 and
3.13 with SHA-pinned actions.

## Repository map

```text
.
|-- data/                  # committed synthetic DOCX, Markdown, and EML
|-- tests/test_showcase.py # end-to-end and provenance assertions
|-- demo.py                # readable API demonstration
|-- expected_output.txt    # verified console result
|-- generate_data.py       # deterministic data generator
|-- requirements.txt       # runtime pins
`-- requirements-dev.txt   # test pins
```

## Responsible interpretation

DocChrono 0.1.0 uses conservative, deterministic English rules. Its entities, claims,
relationships, and events are extracted candidates with confidence scores and exact provenance.
Events are provisional. Review the original documents before relying on any finding, especially
in legal, financial, compliance, or investigative work.

This example is intentionally about evidence navigation. It does not claim that DocChrono 0.1.0
performs contract interpretation, validates payments, detects fraud, or establishes facts.

## License

Licensed under the [Apache License 2.0](LICENSE).
