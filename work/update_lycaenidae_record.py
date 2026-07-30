#!/usr/bin/env python3
"""Correct one Copper butterfly record to family-level Lycaenidae."""

from pathlib import Path


ARCHIVE = Path("/Users/seltmann/Documents/kummel/dwca_kummel_2026")
OCCURRENCE = ARCHIVE / "occurrence.tsv"
MEDIA = ARCHIVE / "associatedMedia.tsv"
TARGET_ID = "e4b13531-3bf4-4f61-b9ad-a578c7bdf9e6"


def read_tsv(path):
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    rows = [line.split("\t") for line in raw.decode("utf-8-sig").splitlines() if line != ""]
    return rows, newline


def write_tsv(path, rows, newline):
    path.write_text(newline.join("\t".join(row) for row in rows) + newline, encoding="utf-8", newline="")


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

    touched = 0
    width = len(header)
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise SystemExit(f"occurrence.tsv row {line_number} has {len(row)} columns, expected {width}")
        if row[idx["occurrenceID"]] != TARGET_ID:
            continue
        row[idx["scientificName"]] = "Lycaenidae"
        row[idx["kingdom"]] = "Animalia"
        row[idx["phylum"]] = "Arthropoda"
        row[idx["class"]] = "Insecta"
        row[idx["order"]] = "Lepidoptera"
        row[idx["family"]] = "Lycaenidae"
        row[idx["genus"]] = ""
        row[idx["specificEpithet"]] = ""
        row[idx["infraspecificEpithet"]] = ""
        row[idx["taxonRank"]] = "family"
        touched += 1

    if touched != 1:
        raise SystemExit(f"Expected to update 1 occurrence row, updated {touched}")
    write_tsv(OCCURRENCE, rows, newline)


def update_media():
    rows, newline = read_tsv(MEDIA)
    header = rows[0]
    idx = {name: pos for pos, name in enumerate(header)}
    for column in ["occurrenceID", "scientificName"]:
        if column not in idx:
            raise SystemExit(f"associatedMedia.tsv missing column: {column}")

    touched = 0
    width = len(header)
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise SystemExit(f"associatedMedia.tsv row {line_number} has {len(row)} columns, expected {width}")
        if row[idx["occurrenceID"]] != TARGET_ID:
            continue
        row[idx["scientificName"]] = "Lycaenidae"
        touched += 1

    if touched != 1:
        raise SystemExit(f"Expected to update 1 associatedMedia row, updated {touched}")
    write_tsv(MEDIA, rows, newline)


def main():
    update_occurrence()
    update_media()
    print(f"Updated {TARGET_ID} to Lycaenidae in occurrence.tsv and associatedMedia.tsv")


if __name__ == "__main__":
    main()
