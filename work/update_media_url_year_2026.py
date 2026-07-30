#!/usr/bin/env python3
"""Change image URL path segment from /kummel/2025/ to /kummel/2026/."""

from pathlib import Path


ARCHIVE = Path("/Users/seltmann/Documents/kummel/dwca_kummel_2026")
TARGETS = [
    (ARCHIVE / "occurrence.tsv", "associatedMedia"),
    (ARCHIVE / "associatedMedia.tsv", "identifier"),
]

OLD = "/kummel/2025/"
NEW = "/kummel/2026/"


def read_tsv(path):
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    rows = [line.split("\t") for line in raw.decode("utf-8-sig").splitlines() if line != ""]
    return rows, newline


def write_tsv(path, rows, newline):
    path.write_text(newline.join("\t".join(row) for row in rows) + newline, encoding="utf-8", newline="")


def update_file(path, column):
    rows, newline = read_tsv(path)
    header = rows[0]
    if column not in header:
        raise SystemExit(f"{path.name} missing column: {column}")
    idx = header.index(column)
    width = len(header)
    changed = 0
    unchanged_with_old = 0
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise SystemExit(f"{path.name} row {line_number} has {len(row)} columns, expected {width}")
        before = row[idx]
        after = before.replace(OLD, NEW)
        if before != after:
            changed += 1
            row[idx] = after
        if OLD in row[idx]:
            unchanged_with_old += 1
    write_tsv(path, rows, newline)
    return changed, unchanged_with_old


def main():
    for path, column in TARGETS:
        changed, old_remaining = update_file(path, column)
        print(f"{path.name}\t{column}\tchanged={changed}\told_remaining={old_remaining}")


if __name__ == "__main__":
    main()
