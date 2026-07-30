#!/usr/bin/env python3
"""Remove associatedTaxa tokens that duplicate scientificName for known rows."""

from pathlib import Path
import csv


ARCHIVE = Path("/Users/seltmann/Documents/kummel/dwca_kummel_2026")
OCCURRENCE = ARCHIVE / "occurrence.tsv"
MATCH_LIST = Path("/Users/seltmann/Documents/kummel/work/associated_taxa_matches_scientific_name.tsv")


def normalized(value):
    return " ".join((value or "").strip().split()).casefold()


def read_target_ids():
    with MATCH_LIST.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return {row["occurrenceID"] for row in reader}


def read_tsv(path):
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    rows = [line.split("\t") for line in raw.decode("utf-8-sig").splitlines() if line != ""]
    return rows, newline


def write_tsv(path, rows, newline):
    path.write_text(newline.join("\t".join(row) for row in rows) + newline, encoding="utf-8", newline="")


def main():
    target_ids = read_target_ids()
    if len(target_ids) != 12:
        raise SystemExit(f"Expected 12 target occurrenceIDs, found {len(target_ids)}")

    rows, newline = read_tsv(OCCURRENCE)
    header = rows[0]
    idx = {name: pos for pos, name in enumerate(header)}
    required = {"occurrenceID", "scientificName", "associatedTaxa"}
    missing = sorted(required - set(header))
    if missing:
        raise SystemExit(f"occurrence.tsv missing columns: {missing}")

    changed = []
    width = len(header)
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise SystemExit(f"occurrence.tsv row {line_number} has {len(row)} columns, expected {width}")
        occurrence_id = row[idx["occurrenceID"]]
        if occurrence_id not in target_ids:
            continue

        scientific_name = row[idx["scientificName"]]
        before = row[idx["associatedTaxa"]]
        tokens = [token.strip() for token in before.split(";") if token.strip()]
        kept = [token for token in tokens if normalized(token) != normalized(scientific_name)]
        after = "; ".join(kept)
        if before != after:
            row[idx["associatedTaxa"]] = after
            changed.append((line_number, occurrence_id, scientific_name, before, after))

    changed_ids = {occurrence_id for _, occurrence_id, _, _, _ in changed}
    missing_changes = sorted(target_ids - changed_ids)
    if missing_changes:
        raise SystemExit(f"No matching associatedTaxa token removed for target IDs: {missing_changes}")

    write_tsv(OCCURRENCE, rows, newline)
    print(f"target rows: {len(target_ids)}")
    print(f"changed rows: {len(changed)}")
    print("line\toccurrenceID\tscientificName\tbefore\tafter")
    for item in changed:
        print("\t".join(str(part) for part in item))


if __name__ == "__main__":
    main()
