#!/usr/bin/env python3
"""Read-only internal consistency checks for the current Kummel DwC-A."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import io
from pathlib import Path
import re
import uuid
import zipfile
import xml.etree.ElementTree as ET


BASE = Path("/Users/seltmann/Documents/kummel")
ARCHIVE = BASE / "dwca_kummel_2026"
ZIP = BASE / "dwca_kummel_2026.zip"
WORK = BASE / "work"

EXPECTED_FILES = ["occurrence.tsv", "associatedMedia.tsv", "meta.xml", "eml.xml"]

EXPECTED_OCCURRENCE = [
    ("occurrenceID", None),
    ("basisOfRecord", "http://rs.tdwg.org/dwc/terms/basisOfRecord"),
    ("datasetID", "http://rs.tdwg.org/dwc/terms/datasetID"),
    ("datasetName", "http://rs.tdwg.org/dwc/terms/datasetName"),
    ("references", "http://purl.org/dc/terms/references"),
    ("institutionCode", "http://rs.tdwg.org/dwc/terms/institutionCode"),
    ("collectionCode", "http://rs.tdwg.org/dwc/terms/collectionCode"),
    ("accessRights", "http://purl.org/dc/terms/accessRights"),
    ("license", "http://purl.org/dc/terms/license"),
    ("scientificName", "http://rs.tdwg.org/dwc/terms/scientificName"),
    ("vernacularName", "http://rs.tdwg.org/dwc/terms/vernacularName"),
    ("kingdom", "http://rs.tdwg.org/dwc/terms/kingdom"),
    ("phylum", "http://rs.tdwg.org/dwc/terms/phylum"),
    ("class", "http://rs.tdwg.org/dwc/terms/class"),
    ("order", "http://rs.tdwg.org/dwc/terms/order"),
    ("family", "http://rs.tdwg.org/dwc/terms/family"),
    ("genus", "http://rs.tdwg.org/dwc/terms/genus"),
    ("specificEpithet", "http://rs.tdwg.org/dwc/terms/specificEpithet"),
    ("infraspecificEpithet", "http://rs.tdwg.org/dwc/terms/infraspecificEpithet"),
    ("taxonRank", "http://rs.tdwg.org/dwc/terms/taxonRank"),
    ("associatedTaxa", "http://rs.tdwg.org/dwc/terms/associatedTaxa"),
    ("eventDate", "http://rs.tdwg.org/dwc/terms/eventDate"),
    ("country", "http://rs.tdwg.org/dwc/terms/country"),
    ("stateProvince", "http://rs.tdwg.org/dwc/terms/stateProvince"),
    ("county", "http://rs.tdwg.org/dwc/terms/county"),
    ("locality", "http://rs.tdwg.org/dwc/terms/locality"),
    ("decimalLatitude", "http://rs.tdwg.org/dwc/terms/decimalLatitude"),
    ("decimalLongitude", "http://rs.tdwg.org/dwc/terms/decimalLongitude"),
    ("coordinateUncertaintyInMeters", "http://rs.tdwg.org/dwc/terms/coordinateUncertaintyInMeters"),
    ("occurrenceRemarks", "http://rs.tdwg.org/dwc/terms/occurrenceRemarks"),
    ("associatedMedia", "http://rs.tdwg.org/dwc/terms/associatedMedia"),
]

EXPECTED_MEDIA = [
    ("occurrenceID", None),
    ("identifier", "http://purl.org/dc/terms/identifier"),
    ("Credit", "http://ns.adobe.com/photoshop/1.0/Credit"),
    ("creator", "http://purl.org/dc/elements/1.1/creator"),
    ("licenseLogoURL", "http://rs.tdwg.org/ac/terms/licenseLogoURL"),
    ("UsageTerms", "http://ns.adobe.com/xap/1.0/rights/UsageTerms"),
    ("description", "http://purl.org/dc/terms/description"),
    ("providerLiteral", "http://rs.tdwg.org/ac/terms/providerLiteral"),
    ("provider", "http://rs.tdwg.org/ac/terms/provider"),
    ("locationCreated", "http://iptc.org/std/Iptc4xmpExt/2008-02-29/LocationCreated"),
    ("captureDevice", "http://rs.tdwg.org/ac/terms/captureDevice"),
    ("createDate", "http://ns.adobe.com/xap/1.0/CreateDate"),
    ("format", "http://purl.org/dc/terms/format"),
    ("collectionID", "http://rs.tdwg.org/ac/terms/IDofContainingCollection"),
    ("scientificName", "http://rs.tdwg.org/dwc/terms/scientificName"),
    ("vernacularName", "http://rs.tdwg.org/dwc/terms/vernacularName"),
]

RANK_LOWER_FIELDS = {
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


class Reporter:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    def ok(self, message):
        self.info.append(("OK", message))

    def error(self, message):
        self.errors.append(message)

    def warning(self, message):
        self.warnings.append(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_tsv(path: Path):
    raw = path.read_bytes()
    rows = [line.split("\t") for line in raw.decode("utf-8-sig").splitlines() if line != ""]
    return raw, rows


def parse_tsv_dict(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def table_shape(reporter, path: Path, expected_header: list[tuple[str, str | None]]):
    raw, rows = read_tsv(path)
    expected_names = [name for name, _ in expected_header]
    if not rows:
        reporter.error(f"{path.name}: file has no rows")
        return raw, [], {}
    header = rows[0]
    idx = {name: i for i, name in enumerate(header)}
    width = len(header)
    bad_widths = [(line, len(row)) for line, row in enumerate(rows[1:], start=2) if len(row) != width]
    duplicate_headers = [name for name, count in Counter(header).items() if count > 1]
    blank_physical_lines = sum(1 for line in raw.splitlines() if line == b"")

    if header != expected_names:
        reporter.error(f"{path.name}: header order differs from expected/meta shape")
    else:
        reporter.ok(f"{path.name}: header order matches expected")
    if bad_widths:
        reporter.error(f"{path.name}: {len(bad_widths)} rows have wrong field counts, first examples {bad_widths[:5]}")
    else:
        reporter.ok(f"{path.name}: every row has {width} columns")
    if duplicate_headers:
        reporter.error(f"{path.name}: duplicate header names {duplicate_headers}")
    if b"\x00" in raw:
        reporter.error(f"{path.name}: contains NUL bytes")
    if b'"' in raw:
        reporter.error(f'{path.name}: contains double quote characters despite fieldsEnclosedBy=""')
    if raw.count(b"\n") != raw.count(b"\r\n"):
        reporter.error(f"{path.name}: not all line endings are CRLF")
    if not raw.endswith(b"\r\n") or raw.endswith(b"\r\n\r\n"):
        reporter.error(f"{path.name}: missing final CRLF or has trailing blank rows")
    if blank_physical_lines:
        reporter.error(f"{path.name}: {blank_physical_lines} blank physical lines")
    if not any(x in raw for x in [b"\x00", b'"']) and raw.count(b"\n") == raw.count(b"\r\n") and raw.endswith(b"\r\n") and not raw.endswith(b"\r\n\r\n") and not blank_physical_lines:
        reporter.ok(f"{path.name}: TSV hygiene clean (CRLF, no quotes/NULs/trailing blanks)")

    return raw, rows, idx


def validate_meta(reporter, occurrence_header, media_header):
    meta_path = ARCHIVE / "meta.xml"
    ns = {"dwctext": "http://rs.tdwg.org/dwc/text/"}
    try:
        tree = ET.parse(meta_path)
        root = tree.getroot()
    except ET.ParseError as error:
        reporter.error(f"meta.xml: XML parse error {error}")
        return

    expected = {
        "core": {
            "header": occurrence_header,
            "location": "occurrence.tsv",
            "id_tag": "id",
            "rowType": "http://rs.tdwg.org/dwc/terms/Occurrence",
            "fields": EXPECTED_OCCURRENCE,
        },
        "extension": {
            "header": media_header,
            "location": "associatedMedia.tsv",
            "id_tag": "coreid",
            "rowType": "http://rs.tdwg.org/ac/terms/Multimedia",
            "fields": EXPECTED_MEDIA,
        },
    }
    for section_name, spec in expected.items():
        section = root.find(f"dwctext:{section_name}", ns)
        if section is None:
            reporter.error(f"meta.xml: missing {section_name}")
            continue
        attrs = section.attrib
        wanted_attrs = {
            "encoding": "UTF-8",
            "linesTerminatedBy": "\\r\\n",
            "fieldsTerminatedBy": "\\t",
            "fieldsEnclosedBy": "",
            "ignoreHeaderLines": "1",
            "rowType": spec["rowType"],
        }
        bad_attrs = {key: (attrs.get(key), value) for key, value in wanted_attrs.items() if attrs.get(key) != value}
        if bad_attrs:
            reporter.error(f"meta.xml {section_name}: unexpected attributes {bad_attrs}")
        else:
            reporter.ok(f"meta.xml {section_name}: delimiter/header/rowType attributes match")

        location = section.find("dwctext:files/dwctext:location", ns)
        if location is None or location.text != spec["location"]:
            reporter.error(f"meta.xml {section_name}: location is {location.text if location is not None else None}, expected {spec['location']}")
        else:
            reporter.ok(f"meta.xml {section_name}: file location matches")

        id_node = section.find(f"dwctext:{spec['id_tag']}", ns)
        if id_node is None or id_node.attrib.get("index") != "0" or spec["header"][0] != "occurrenceID":
            reporter.error(f"meta.xml {section_name}: {spec['id_tag']} does not map index 0 to occurrenceID")
        else:
            reporter.ok(f"meta.xml {section_name}: {spec['id_tag']} maps index 0 to occurrenceID")

        field_nodes = section.findall("dwctext:field", ns)
        expected_field_terms = [term for _, term in spec["fields"][1:]]
        observed = sorted((int(node.attrib["index"]), node.attrib.get("term")) for node in field_nodes)
        expected_observed = list(zip(range(1, len(spec["header"])), expected_field_terms))
        if observed != expected_observed:
            reporter.error(f"meta.xml {section_name}: field indexes/terms do not match header order")
        else:
            reporter.ok(f"meta.xml {section_name}: field indexes/terms match header order")


def validate_ids_and_joins(reporter, occurrence_rows, media_rows):
    occ_ids = [row["occurrenceID"] for row in occurrence_rows]
    media_ids = [row["occurrenceID"] for row in media_rows]
    for name, ids in [("occurrence.tsv", occ_ids), ("associatedMedia.tsv", media_ids)]:
        blank = [i for i in ids if not i]
        invalid = []
        for value in ids:
            if not value:
                continue
            try:
                uuid.UUID(value)
            except ValueError:
                invalid.append(value)
        dupes = [value for value, count in Counter(ids).items() if count > 1]
        if blank:
            reporter.error(f"{name}: {len(blank)} blank occurrenceID values")
        if invalid:
            reporter.error(f"{name}: {len(invalid)} invalid UUID occurrenceID values, examples {invalid[:5]}")
        if dupes:
            reporter.error(f"{name}: {len(dupes)} duplicate occurrenceID values, examples {dupes[:5]}")
        if not blank and not invalid and not dupes:
            reporter.ok(f"{name}: occurrenceID values are nonblank, unique UUIDs")

    occ_set = set(occ_ids)
    media_set = set(media_ids)
    if occ_set != media_set:
        reporter.error(f"core/extension join: media-only IDs={len(media_set - occ_set)}, occurrence-only IDs={len(occ_set - media_set)}")
    else:
        reporter.ok("core/extension join: occurrenceID sets are identical")


def validate_urls(reporter, occurrence_rows, media_rows):
    occ = {row["occurrenceID"]: row["associatedMedia"] for row in occurrence_rows}
    media = {row["occurrenceID"]: row["identifier"] for row in media_rows}
    shared = sorted(set(occ) & set(media))
    mismatches = [(oid, occ[oid], media[oid]) for oid in shared if occ[oid] != media[oid]]
    if mismatches:
        reporter.error(f"media paths: {len(mismatches)} occurrence.associatedMedia vs media.identifier mismatches, examples {mismatches[:5]}")
    else:
        reporter.ok("media paths: occurrence.associatedMedia and associatedMedia.identifier match by occurrenceID")

    urls = list(media.values())
    blank = [url for url in urls if not url]
    old = [url for url in urls if "/kummel/2025/" in url]
    new = [url for url in urls if "/kummel/2026/" in url]
    not_jpg = [url for url in urls if not url.lower().endswith(".jpg")]
    whitespace = [url for url in urls if url != url.strip() or re.search(r"\s", url)]
    dupes = [url for url, count in Counter(urls).items() if count > 1]
    if blank:
        reporter.error(f"media paths: {len(blank)} blank identifier URLs")
    if old:
        reporter.error(f"media paths: {len(old)} URLs still contain /kummel/2025/")
    if len(new) != len(urls):
        reporter.error(f"media paths: {len(urls) - len(new)} URLs do not contain /kummel/2026/")
    if not_jpg:
        reporter.error(f"media paths: {len(not_jpg)} URLs do not end in .jpg, examples {not_jpg[:5]}")
    if whitespace:
        reporter.error(f"media paths: {len(whitespace)} URLs contain whitespace")
    if dupes:
        reporter.error(f"media paths: {len(dupes)} duplicate URLs, examples {dupes[:5]}")
    if not any([blank, old, len(new) != len(urls), not_jpg, whitespace, dupes]):
        reporter.ok("media paths: all identifiers are unique /2026/ .jpg URLs with no whitespace")


def parse_event_date(value):
    return datetime.fromisoformat(value)


def validate_content_basics(reporter, occurrence_rows, media_rows):
    dataset_names = Counter(row["datasetName"] for row in occurrence_rows)
    dataset_ids = Counter(row["datasetID"] for row in occurrence_rows)
    basis_values = Counter(row["basisOfRecord"] for row in occurrence_rows)
    licenses = Counter(row["license"] for row in occurrence_rows)
    formats = Counter(row["format"] for row in media_rows)
    media_sci_mismatches = []
    media_vern_mismatches = []
    occ_by_id = {row["occurrenceID"]: row for row in occurrence_rows}
    for row in media_rows:
        occ = occ_by_id[row["occurrenceID"]]
        if row["scientificName"] != occ["scientificName"]:
            media_sci_mismatches.append((row["occurrenceID"], occ["scientificName"], row["scientificName"]))
        if row["vernacularName"] != occ["vernacularName"]:
            media_vern_mismatches.append((row["occurrenceID"], occ["vernacularName"], row["vernacularName"]))

    if dataset_names == Counter({"Marc Kummel Photography": len(occurrence_rows)}):
        reporter.ok("datasetName: all occurrence rows use Marc Kummel Photography")
    else:
        reporter.error(f"datasetName: unexpected values {dict(dataset_names)}")
    if len(dataset_ids) == 1:
        reporter.ok(f"datasetID: one value across occurrence rows ({next(iter(dataset_ids))})")
    else:
        reporter.error(f"datasetID: multiple values {dict(dataset_ids)}")
    if basis_values == Counter({"HumanObservation": len(occurrence_rows)}):
        reporter.ok("basisOfRecord: all rows use HumanObservation")
    else:
        reporter.error(f"basisOfRecord: unexpected values {dict(basis_values)}")
    if len(licenses) == 1 and "creativecommons.org/licenses/by/4.0" in next(iter(licenses)):
        reporter.ok("license: one CC BY 4.0 URL across occurrence rows")
    else:
        reporter.error(f"license: unexpected values {dict(licenses)}")
    if formats == Counter({"image/jpeg": len(media_rows)}):
        reporter.ok("associatedMedia format: all rows are image/jpeg")
    else:
        reporter.error(f"associatedMedia format: unexpected values {dict(formats)}")
    if media_sci_mismatches:
        reporter.error(f"associatedMedia scientificName: {len(media_sci_mismatches)} mismatches with occurrence, examples {media_sci_mismatches[:5]}")
    else:
        reporter.ok("associatedMedia scientificName mirrors occurrence scientificName by occurrenceID")
    if media_vern_mismatches:
        reporter.error(f"associatedMedia vernacularName: {len(media_vern_mismatches)} mismatches with occurrence, examples {media_vern_mismatches[:5]}")
    else:
        reporter.ok("associatedMedia vernacularName mirrors occurrence vernacularName by occurrenceID")

    blank_sci = [(row["occurrenceID"], row["vernacularName"]) for row in occurrence_rows if not row["scientificName"]]
    if blank_sci:
        reporter.error(f"scientificName: {len(blank_sci)} blank values, examples {blank_sci[:5]}")
    else:
        reporter.ok("scientificName: no blanks")

    accepted_ranks = set(RANK_LOWER_FIELDS)
    ranks = Counter(row["taxonRank"] for row in occurrence_rows)
    unexpected_ranks = {rank: count for rank, count in ranks.items() if rank not in accepted_ranks}
    if unexpected_ranks:
        reporter.error(f"taxonRank: unexpected values {unexpected_ranks}")
    else:
        reporter.ok(f"taxonRank: all values are in expected set {sorted(accepted_ranks)}")

    lower_rank_conflicts = []
    species_epithet_missing = []
    for row in occurrence_rows:
        rank = row["taxonRank"]
        if rank in RANK_LOWER_FIELDS:
            populated_lower = [field for field in RANK_LOWER_FIELDS[rank] if row[field]]
            if populated_lower:
                lower_rank_conflicts.append((row["occurrenceID"], row["scientificName"], rank, populated_lower))
        if rank == "species" and (not row["genus"] or not row["specificEpithet"]):
            species_epithet_missing.append((row["occurrenceID"], row["scientificName"], row["genus"], row["specificEpithet"]))
        if rank in {"subspecies", "variety"} and (not row["genus"] or not row["specificEpithet"] or not row["infraspecificEpithet"]):
            species_epithet_missing.append((row["occurrenceID"], row["scientificName"], row["genus"], row["specificEpithet"], row["infraspecificEpithet"]))
    if lower_rank_conflicts:
        reporter.warning(f"taxonomy rank consistency: {len(lower_rank_conflicts)} rows have lower-rank fields populated below taxonRank, examples {lower_rank_conflicts[:10]}")
    else:
        reporter.ok("taxonomy rank consistency: no lower-rank fields populated below taxonRank")
    if species_epithet_missing:
        reporter.warning(f"species/subspecies epithet consistency: {len(species_epithet_missing)} rows missing expected genus/specific/infraspecific fields, examples {species_epithet_missing[:10]}")
    else:
        reporter.ok("species/subspecies epithet consistency: expected epithet fields are populated")

    event_errors = []
    event_dates = []
    future_dates = []
    today = datetime.now().replace(tzinfo=None)
    for row in occurrence_rows:
        try:
            parsed = parse_event_date(row["eventDate"])
            event_dates.append(parsed)
            if parsed > today:
                future_dates.append((row["occurrenceID"], row["eventDate"]))
        except ValueError:
            event_errors.append((row["occurrenceID"], row["eventDate"]))
    if event_errors:
        reporter.error(f"eventDate: {len(event_errors)} parse errors, examples {event_errors[:5]}")
    else:
        reporter.ok(f"eventDate: all parse as ISO datetimes; range {min(event_dates).date()} to {max(event_dates).date()}")
    if future_dates:
        reporter.error(f"eventDate: {len(future_dates)} future dates, examples {future_dates[:5]}")

    coord_errors = []
    uncertainty_errors = []
    for row in occurrence_rows:
        try:
            lat = float(row["decimalLatitude"])
            lon = float(row["decimalLongitude"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                coord_errors.append((row["occurrenceID"], row["decimalLatitude"], row["decimalLongitude"]))
        except ValueError:
            coord_errors.append((row["occurrenceID"], row["decimalLatitude"], row["decimalLongitude"]))
        try:
            uncertainty = float(row["coordinateUncertaintyInMeters"])
            if uncertainty < 0:
                uncertainty_errors.append((row["occurrenceID"], row["coordinateUncertaintyInMeters"]))
        except ValueError:
            uncertainty_errors.append((row["occurrenceID"], row["coordinateUncertaintyInMeters"]))
    if coord_errors:
        reporter.error(f"coordinates: {len(coord_errors)} invalid decimalLatitude/decimalLongitude values, examples {coord_errors[:5]}")
    else:
        reporter.ok("coordinates: all decimalLatitude/decimalLongitude values are numeric and in range")
    if uncertainty_errors:
        reporter.error(f"coordinateUncertaintyInMeters: {len(uncertainty_errors)} invalid values, examples {uncertainty_errors[:5]}")
    else:
        reporter.ok("coordinateUncertaintyInMeters: all values are numeric and nonnegative")

    country_values = Counter(row["country"] for row in occurrence_rows)
    state_values = Counter(row["stateProvince"] for row in occurrence_rows)
    reporter.ok(f"geography values: country={dict(country_values)}, stateProvince={dict(state_values)}")


def find_text(root, local_name):
    for elem in root.iter():
        if elem.tag.split("}")[-1] == local_name:
            if elem.text and elem.text.strip():
                return elem.text.strip()
    return ""


def validate_eml(reporter, occurrence_rows):
    eml_path = ARCHIVE / "eml.xml"
    try:
        tree = ET.parse(eml_path)
        root = tree.getroot()
    except ET.ParseError as error:
        reporter.error(f"eml.xml: XML parse error {error}")
        return
    title = find_text(root, "title")
    pub_date = find_text(root, "pubDate")
    if title == "Marc Kummel Photography":
        reporter.ok("eml.xml: title matches datasetName")
    else:
        reporter.error(f"eml.xml: title {title!r} does not match datasetName")
    if pub_date:
        reporter.ok(f"eml.xml: pubDate present ({pub_date})")
    else:
        reporter.warning("eml.xml: pubDate is blank or not found")

    text = eml_path.read_text(encoding="utf-8", errors="replace")
    if "creativecommons.org/licenses/by/4.0" in text:
        reporter.ok("eml.xml: CC BY 4.0 license URL present")
    else:
        reporter.warning("eml.xml: CC BY 4.0 license URL not found")

    # Check temporal coverage only if begin/end dates are present.
    begin_dates = [elem.text.strip() for elem in root.iter() if elem.tag.split("}")[-1] == "beginDate" and elem.text and elem.text.strip()]
    end_dates = [elem.text.strip() for elem in root.iter() if elem.tag.split("}")[-1] == "endDate" and elem.text and elem.text.strip()]
    event_dates = [parse_event_date(row["eventDate"]).date() for row in occurrence_rows if row["eventDate"]]
    if begin_dates and end_dates and event_dates:
        data_min = min(event_dates).isoformat()
        data_max = max(event_dates).isoformat()
        if begin_dates[0] != data_min or end_dates[0] != data_max:
            reporter.warning(
                f"eml.xml temporalCoverage differs from data eventDate range: "
                f"EML {begin_dates[0]} to {end_dates[0]}, data {data_min} to {data_max}"
            )
        else:
            reporter.ok("eml.xml: temporalCoverage matches eventDate range")


def validate_zip(reporter):
    if not ZIP.exists():
        reporter.error(f"zip: {ZIP} does not exist")
        return
    with zipfile.ZipFile(ZIP) as archive:
        names = archive.namelist()
        if names != EXPECTED_FILES:
            reporter.error(f"zip: entries are {names}, expected {EXPECTED_FILES}")
        else:
            reporter.ok("zip: contains exactly the expected four root files")
        for name in EXPECTED_FILES:
            if name not in names:
                continue
            folder_bytes = (ARCHIVE / name).read_bytes()
            zip_bytes = archive.read(name)
            if sha256_bytes(folder_bytes) != sha256_bytes(zip_bytes):
                reporter.error(f"zip: {name} differs from folder copy")
            else:
                reporter.ok(f"zip: {name} matches folder copy")


def main():
    reporter = Reporter()
    missing_files = [name for name in EXPECTED_FILES if not (ARCHIVE / name).exists()]
    extra_files = sorted(path.name for path in ARCHIVE.iterdir() if path.is_file() and path.name not in EXPECTED_FILES)
    if missing_files:
        reporter.error(f"archive folder: missing files {missing_files}")
    else:
        reporter.ok("archive folder: all expected files are present")
    if extra_files:
        reporter.error(f"archive folder: unexpected extra files {extra_files}")
    else:
        reporter.ok("archive folder: no unexpected extra files")

    occurrence_raw, occurrence_lines, occurrence_idx = table_shape(reporter, ARCHIVE / "occurrence.tsv", EXPECTED_OCCURRENCE)
    media_raw, media_lines, media_idx = table_shape(reporter, ARCHIVE / "associatedMedia.tsv", EXPECTED_MEDIA)
    occurrence_rows = parse_tsv_dict(ARCHIVE / "occurrence.tsv")
    media_rows = parse_tsv_dict(ARCHIVE / "associatedMedia.tsv")

    if len(occurrence_rows) != len(media_rows):
        reporter.error(f"row counts: occurrence={len(occurrence_rows)}, associatedMedia={len(media_rows)}")
    else:
        reporter.ok(f"row counts: occurrence and associatedMedia both have {len(occurrence_rows)} data rows")

    validate_meta(reporter, occurrence_lines[0], media_lines[0])
    validate_ids_and_joins(reporter, occurrence_rows, media_rows)
    validate_urls(reporter, occurrence_rows, media_rows)
    validate_content_basics(reporter, occurrence_rows, media_rows)
    validate_eml(reporter, occurrence_rows)
    validate_zip(reporter)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = WORK / f"dwca_internal_consistency_report_{timestamp}.txt"
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("DwC-A Internal Consistency Report\n")
        handle.write(f"Archive: {ARCHIVE}\n")
        handle.write(f"Zip: {ZIP}\n")
        handle.write(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")
        handle.write(f"ERRORS: {len(reporter.errors)}\n")
        for item in reporter.errors:
            handle.write(f"- {item}\n")
        handle.write(f"\nWARNINGS: {len(reporter.warnings)}\n")
        for item in reporter.warnings:
            handle.write(f"- {item}\n")
        handle.write(f"\nOK CHECKS: {len(reporter.info)}\n")
        for status, item in reporter.info:
            handle.write(f"- {item}\n")

    print(f"report\t{report_path}")
    print(f"errors\t{len(reporter.errors)}")
    for item in reporter.errors:
        print(f"ERROR\t{item}")
    print(f"warnings\t{len(reporter.warnings)}")
    for item in reporter.warnings:
        print(f"WARNING\t{item}")
    print(f"ok_checks\t{len(reporter.info)}")

    if reporter.errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
