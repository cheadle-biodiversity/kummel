#!/usr/bin/env python3
"""Set the eight spider-only records to order-level Araneae taxonomy."""

from pathlib import Path


ARCHIVE = Path("/Users/seltmann/Documents/kummel/dwca_kummel_2026")
OCCURRENCE = ARCHIVE / "occurrence.tsv"
MEDIA = ARCHIVE / "associatedMedia.tsv"

SPIDER_OCCURRENCE_IDS = {
    "9dac46a6-7794-4076-bda0-19c74961389f",
    "66147c44-dd16-4d1b-b973-d669708edc4d",
    "9f65d1a0-ca33-44c3-b193-06f2fb27d41b",
    "c238fd1b-03c6-499d-acee-31e8053620fd",
    "a3502d2c-f592-4555-8c86-8ef1dcddcd39",
    "78749ff7-ec99-4f18-8841-d5898899ac4b",
    "047f0194-8c81-4a4a-b6b2-2f3d3597c372",
    "5c6aac7e-04e5-4288-8a98-315d335e8165",
}


def read_tsv(path):
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    rows = [line.split("\t") for line in lines if line != ""]
    return rows, newline


def write_tsv(path, rows, newline):
    text = newline.join("\t".join(row) for row in rows) + newline
    path.write_text(text, encoding="utf-8", newline="")


def update_occurrence():
    rows, newline = read_tsv(OCCURRENCE)
    header = rows[0]
    idx = {name: pos for pos, name in enumerate(header)}
    required = [
        "occurrenceID",
        "scientificName",
        "kingdom",
        "phylum",
        "class",
        "order",
        "family",
        "genus",
        "specificEpithet",
        "infraspecificEpithet",
        "taxonRank",
    ]
    missing = [name for name in required if name not in idx]
    if missing:
        raise SystemExit(f"occurrence.tsv missing columns: {missing}")

    touched = []
    width = len(header)
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise SystemExit(
                f"occurrence.tsv row {line_number} has {len(row)} columns, expected {width}"
            )
        occurrence_id = row[idx["occurrenceID"]]
        if occurrence_id not in SPIDER_OCCURRENCE_IDS:
            continue
        row[idx["scientificName"]] = "Araneae"
        row[idx["kingdom"]] = "Animalia"
        row[idx["phylum"]] = "Arthropoda"
        row[idx["class"]] = "Arachnida"
        row[idx["order"]] = "Araneae"
        row[idx["family"]] = ""
        row[idx["genus"]] = ""
        row[idx["specificEpithet"]] = ""
        row[idx["infraspecificEpithet"]] = ""
        row[idx["taxonRank"]] = "order"
        touched.append(occurrence_id)

    missing_ids = sorted(SPIDER_OCCURRENCE_IDS - set(touched))
    if missing_ids:
        raise SystemExit(f"occurrence.tsv missing target IDs: {missing_ids}")

    write_tsv(OCCURRENCE, rows, newline)
    return touched


def update_media():
    rows, newline = read_tsv(MEDIA)
    header = rows[0]
    idx = {name: pos for pos, name in enumerate(header)}
    required = ["occurrenceID", "scientificName"]
    missing = [name for name in required if name not in idx]
    if missing:
        raise SystemExit(f"associatedMedia.tsv missing columns: {missing}")

    touched = []
    width = len(header)
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise SystemExit(
                f"associatedMedia.tsv row {line_number} has {len(row)} columns, expected {width}"
            )
        occurrence_id = row[idx["occurrenceID"]]
        if occurrence_id not in SPIDER_OCCURRENCE_IDS:
            continue
        row[idx["scientificName"]] = "Araneae"
        touched.append(occurrence_id)

    missing_ids = sorted(SPIDER_OCCURRENCE_IDS - set(touched))
    if missing_ids:
        raise SystemExit(f"associatedMedia.tsv missing target IDs: {missing_ids}")

    write_tsv(MEDIA, rows, newline)
    return touched


def main():
    occurrence_touched = update_occurrence()
    media_touched = update_media()
    print(f"Updated occurrence.tsv records: {len(occurrence_touched)}")
    print(f"Updated associatedMedia.tsv records: {len(media_touched)}")


if __name__ == "__main__":
    main()
