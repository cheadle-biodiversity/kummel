#!/usr/bin/env python3
"""Validate the DwC-A files after the spider-only order-level update."""

from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET


ARCHIVE = Path("/Users/seltmann/Documents/kummel/dwca_kummel_2026")
OCCURRENCE = ARCHIVE / "occurrence.tsv"
MEDIA = ARCHIVE / "associatedMedia.tsv"
META = ARCHIVE / "meta.xml"

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

EXPECTED_OCCURRENCE_HEADER = [
    "occurrenceID",
    "basisOfRecord",
    "datasetID",
    "datasetName",
    "references",
    "institutionCode",
    "collectionCode",
    "accessRights",
    "license",
    "scientificName",
    "vernacularName",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "specificEpithet",
    "infraspecificEpithet",
    "taxonRank",
    "associatedTaxa",
    "eventDate",
    "country",
    "stateProvince",
    "county",
    "locality",
    "decimalLatitude",
    "decimalLongitude",
    "coordinateUncertaintyInMeters",
    "occurrenceRemarks",
    "associatedMedia",
]

EXPECTED_MEDIA_HEADER = [
    "occurrenceID",
    "identifier",
    "Credit",
    "creator",
    "licenseLogoURL",
    "UsageTerms",
    "description",
    "providerLiteral",
    "provider",
    "locationCreated",
    "captureDevice",
    "createDate",
    "format",
    "collectionID",
    "scientificName",
    "vernacularName",
]


def read_tsv(path):
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    rows = [line.split("\t") for line in lines if line != ""]
    return raw, rows


def table_stats(path, expected_header):
    raw, rows = read_tsv(path)
    header = rows[0]
    width = len(header)
    bad_widths = [
        (line_number, len(row))
        for line_number, row in enumerate(rows[1:], start=2)
        if len(row) != width
    ]
    return {
        "path": path,
        "rows": rows,
        "header": header,
        "data_rows": len(rows) - 1,
        "columns": width,
        "expected_header_match": header == expected_header,
        "bad_width_count": len(bad_widths),
        "bad_width_examples": bad_widths[:5],
        "quote_count": raw.count(b'"'),
        "nul_count": raw.count(b"\x00"),
        "crlf_only": raw.count(b"\n") == raw.count(b"\r\n") and b"\r\r\n" not in raw,
        "ends_with_single_newline": raw.endswith(b"\r\n") and not raw.endswith(b"\r\n\r\n"),
        "blank_physical_lines": sum(1 for line in raw.splitlines() if line == b""),
    }


def blank_count(rows, column_name):
    header = rows[0]
    idx = header.index(column_name)
    return sum(1 for row in rows[1:] if row[idx] == "")


def duplicate_count(rows, column_name):
    header = rows[0]
    idx = header.index(column_name)
    counts = Counter(row[idx] for row in rows[1:])
    duplicates = {key: value for key, value in counts.items() if value > 1}
    return len(duplicates), list(duplicates.items())[:5]


def validate_targets(occurrence_rows, media_rows):
    occurrence_header = occurrence_rows[0]
    occurrence_idx = {name: pos for pos, name in enumerate(occurrence_header)}
    media_header = media_rows[0]
    media_idx = {name: pos for pos, name in enumerate(media_header)}

    errors = []
    for row in occurrence_rows[1:]:
        occurrence_id = row[occurrence_idx["occurrenceID"]]
        if occurrence_id not in SPIDER_OCCURRENCE_IDS:
            continue
        expected = {
            "scientificName": "Araneae",
            "kingdom": "Animalia",
            "phylum": "Arthropoda",
            "class": "Arachnida",
            "order": "Araneae",
            "family": "",
            "genus": "",
            "specificEpithet": "",
            "infraspecificEpithet": "",
            "taxonRank": "order",
        }
        for column, value in expected.items():
            observed = row[occurrence_idx[column]]
            if observed != value:
                errors.append((occurrence_id, "occurrence.tsv", column, observed, value))

    for row in media_rows[1:]:
        occurrence_id = row[media_idx["occurrenceID"]]
        if occurrence_id not in SPIDER_OCCURRENCE_IDS:
            continue
        observed = row[media_idx["scientificName"]]
        if observed != "Araneae":
            errors.append((occurrence_id, "associatedMedia.tsv", "scientificName", observed, "Araneae"))

    return errors


def validate_meta():
    ns = {"dwctext": "http://rs.tdwg.org/dwc/text/"}
    tree = ET.parse(META)
    root = tree.getroot()
    checks = []
    for section_name, path, expected_header, id_tag in [
        ("core", OCCURRENCE, EXPECTED_OCCURRENCE_HEADER, "id"),
        ("extension", MEDIA, EXPECTED_MEDIA_HEADER, "coreid"),
    ]:
        section = root.find(f"dwctext:{section_name}", ns)
        if section is None:
            checks.append((section_name, "missing section", False))
            continue
        raw, rows = read_tsv(path)
        header = rows[0]
        location = section.find("dwctext:files/dwctext:location", ns).text
        terminators_ok = (
            section.attrib.get("fieldsTerminatedBy") == "\\t"
            and section.attrib.get("linesTerminatedBy") == "\\r\\n"
            and section.attrib.get("fieldsEnclosedBy") == ""
            and section.attrib.get("ignoreHeaderLines") == "1"
        )
        id_node = section.find(f"dwctext:{id_tag}", ns)
        id_ok = id_node is not None and int(id_node.attrib["index"]) == 0 and header[0] == "occurrenceID"
        field_indexes = [
            int(field.attrib["index"])
            for field in section.findall("dwctext:field", ns)
        ]
        index_ok = field_indexes == list(range(1, len(header)))
        checks.append((section_name, f"location={location}", location == path.name))
        checks.append((section_name, "delimiter/header attributes", terminators_ok))
        checks.append((section_name, f"{id_tag} index 0 -> occurrenceID", id_ok))
        checks.append((section_name, "field indexes match header positions", index_ok))
        checks.append((section_name, "header order matches expected", header == expected_header))
    return checks


def main():
    occurrence = table_stats(OCCURRENCE, EXPECTED_OCCURRENCE_HEADER)
    media = table_stats(MEDIA, EXPECTED_MEDIA_HEADER)
    occurrence_rows = occurrence["rows"]
    media_rows = media["rows"]

    occurrence_ids = [row[0] for row in occurrence_rows[1:]]
    media_ids = [row[0] for row in media_rows[1:]]
    occurrence_id_set = set(occurrence_ids)
    media_id_set = set(media_ids)

    target_errors = validate_targets(occurrence_rows, media_rows)
    meta_checks = validate_meta()

    print("table\tdata_rows\tcolumns\tbad_widths\tblank_scientificName\tquotes\tnuls\tcrlf_only\tno_trailing_blank_rows\theader_expected")
    for name, stats in [("occurrence.tsv", occurrence), ("associatedMedia.tsv", media)]:
        print(
            f"{name}\t{stats['data_rows']}\t{stats['columns']}\t{stats['bad_width_count']}"
            f"\t{blank_count(stats['rows'], 'scientificName')}\t{stats['quote_count']}\t{stats['nul_count']}"
            f"\t{stats['crlf_only']}\t{stats['ends_with_single_newline'] and stats['blank_physical_lines'] == 0}"
            f"\t{stats['expected_header_match']}"
        )

    occurrence_dupes = duplicate_count(occurrence_rows, "occurrenceID")
    media_dupes = duplicate_count(media_rows, "occurrenceID")
    print(f"occurrence_duplicate_ids\t{occurrence_dupes[0]}\t{occurrence_dupes[1]}")
    print(f"associatedMedia_duplicate_ids\t{media_dupes[0]}\t{media_dupes[1]}")
    print(f"media_ids_missing_in_occurrence\t{len(media_id_set - occurrence_id_set)}")
    print(f"occurrence_ids_missing_in_media\t{len(occurrence_id_set - media_id_set)}")
    print(f"target_taxonomy_errors\t{len(target_errors)}\t{target_errors[:5]}")
    for section, check, ok in meta_checks:
        print(f"meta_{section}\t{check}\t{ok}")

    if (
        occurrence["data_rows"] != 18896
        or media["data_rows"] != 18896
        or occurrence["columns"] != 31
        or media["columns"] != 16
        or occurrence["bad_width_count"]
        or media["bad_width_count"]
        or blank_count(occurrence_rows, "scientificName")
        or blank_count(media_rows, "scientificName")
        or occurrence["quote_count"]
        or media["quote_count"]
        or occurrence["nul_count"]
        or media["nul_count"]
        or not occurrence["crlf_only"]
        or not media["crlf_only"]
        or occurrence_dupes[0]
        or media_dupes[0]
        or media_id_set != occurrence_id_set
        or target_errors
        or not all(ok for _, _, ok in meta_checks)
    ):
        raise SystemExit("Validation failed")


if __name__ == "__main__":
    main()
