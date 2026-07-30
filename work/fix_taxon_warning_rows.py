#!/usr/bin/env python3
"""Fix taxonomy-field consistency warnings in the Kummel DwC-A TSVs."""

from pathlib import Path


ARCHIVE = Path("/Users/seltmann/Documents/kummel/dwca_kummel_2026")
OCCURRENCE = ARCHIVE / "occurrence.tsv"
MEDIA = ARCHIVE / "associatedMedia.tsv"

LOWER_FIELDS_BY_RANK = {
    "kingdom": ["phylum", "class", "order", "family", "genus", "specificEpithet", "infraspecificEpithet"],
    "phylum": ["class", "order", "family", "genus", "specificEpithet", "infraspecificEpithet"],
    "class": ["order", "family", "genus", "specificEpithet", "infraspecificEpithet"],
    "order": ["family", "genus", "specificEpithet", "infraspecificEpithet"],
    "family": ["genus", "specificEpithet", "infraspecificEpithet"],
    "genus": ["specificEpithet", "infraspecificEpithet"],
    "species": ["infraspecificEpithet"],
    "subspecies": [],
    "variety": [],
}

ROW_FIXES = {
    # Clear infraspecific epithet warnings where the epithet is explicit.
    "c5f9d3e6-8537-404d-a561-b608d296c271": {
        "infraspecificEpithet": "polifolium",
    },
    "c0db3f70-510e-401b-8fa1-555df5219f8a": {
        "infraspecificEpithet": "taraxacifolia",
    },
    # Bad name parse: keep to a conservative, explicit order-level ID.
    "b68935c4-298f-4f7c-9171-c88a72cbd7b6": {
        "scientificName": "Hemiptera",
        "vernacularName": "Scale Insect",
        "kingdom": "Animalia",
        "phylum": "Arthropoda",
        "class": "Insecta",
        "order": "Hemiptera",
        "family": "",
        "genus": "",
        "specificEpithet": "",
        "infraspecificEpithet": "",
        "taxonRank": "order",
    },
    # Bad name parse: caption is an earthworm, not a Stropharia fungus.
    "31320a2c-a47d-439b-ba4b-1472f476beab": {
        "scientificName": "Clitellata",
        "vernacularName": "earthworm",
        "kingdom": "Animalia",
        "phylum": "Annelida",
        "class": "Clitellata",
        "order": "",
        "family": "",
        "genus": "",
        "specificEpithet": "",
        "infraspecificEpithet": "",
        "taxonRank": "class",
    },
}


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
    required = {"occurrenceID", "taxonRank", *{field for fields in LOWER_FIELDS_BY_RANK.values() for field in fields}}
    required.update({field for fix in ROW_FIXES.values() for field in fix})
    missing = sorted(required - set(header))
    if missing:
        raise SystemExit(f"occurrence.tsv missing columns: {missing}")

    width = len(header)
    row_fix_count = 0
    lower_field_clear_count = 0
    lower_field_rows = []
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise SystemExit(f"occurrence.tsv row {line_number} has {len(row)} columns, expected {width}")

        occurrence_id = row[idx["occurrenceID"]]
        fix = ROW_FIXES.get(occurrence_id)
        if fix:
            for column, value in fix.items():
                row[idx[column]] = value
            row_fix_count += 1

        rank = row[idx["taxonRank"]]
        for field in LOWER_FIELDS_BY_RANK.get(rank, []):
            field_idx = idx[field]
            if row[field_idx]:
                row[field_idx] = ""
                lower_field_clear_count += 1
                lower_field_rows.append((line_number, occurrence_id, field))

    missing_targets = sorted(set(ROW_FIXES) - {row[idx["occurrenceID"]] for row in rows[1:]})
    if missing_targets:
        raise SystemExit(f"occurrence.tsv missing target IDs: {missing_targets}")
    write_tsv(OCCURRENCE, rows, newline)
    return row_fix_count, lower_field_clear_count, lower_field_rows


def update_media():
    rows, newline = read_tsv(MEDIA)
    header = rows[0]
    idx = {name: pos for pos, name in enumerate(header)}
    required = {"occurrenceID", "scientificName", "vernacularName"}
    missing = sorted(required - set(header))
    if missing:
        raise SystemExit(f"associatedMedia.tsv missing columns: {missing}")

    width = len(header)
    updated = 0
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise SystemExit(f"associatedMedia.tsv row {line_number} has {len(row)} columns, expected {width}")
        occurrence_id = row[idx["occurrenceID"]]
        fix = ROW_FIXES.get(occurrence_id)
        if not fix:
            continue
        changed = False
        for column in ["scientificName", "vernacularName"]:
            if column in fix and row[idx[column]] != fix[column]:
                row[idx[column]] = fix[column]
                changed = True
        if changed:
            updated += 1

    write_tsv(MEDIA, rows, newline)
    return updated


def main():
    row_fix_count, lower_field_clear_count, lower_field_rows = update_occurrence()
    media_updated = update_media()
    print(f"occurrence row-specific fixes applied: {row_fix_count}")
    print(f"lower-rank field cells cleared: {lower_field_clear_count}")
    print(f"rows with lower-rank fields cleared: {len(set((line, oid) for line, oid, _ in lower_field_rows))}")
    print(f"associatedMedia rows updated: {media_updated}")
    if lower_field_rows:
        print("first lower-rank field clears:")
        for line_number, occurrence_id, field in lower_field_rows[:20]:
            print(f"{line_number}\t{occurrence_id}\t{field}")


if __name__ == "__main__":
    main()
