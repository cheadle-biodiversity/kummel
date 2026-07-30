#!/usr/bin/env python3
"""Apply targeted taxonomy corrections for known DwC-A name-match issues."""

from pathlib import Path


ARCHIVE = Path("/Users/seltmann/Documents/kummel/dwca_kummel_2026")
OCCURRENCE = ARCHIVE / "occurrence.tsv"
MEDIA = ARCHIVE / "associatedMedia.tsv"


def taxon(
    scientific_name,
    vernacular_name,
    kingdom,
    phylum="",
    class_name="",
    order="",
    family="",
    genus="",
    specific_epithet="",
    infraspecific_epithet="",
    taxon_rank="",
):
    return {
        "scientificName": scientific_name,
        "vernacularName": vernacular_name,
        "kingdom": kingdom,
        "phylum": phylum,
        "class": class_name,
        "order": order,
        "family": family,
        "genus": genus,
        "specificEpithet": specific_epithet,
        "infraspecificEpithet": infraspecific_epithet,
        "taxonRank": taxon_rank,
    }


FUNGI_LICHEN = {
    "kingdom": "Fungi",
    "phylum": "",
    "class": "",
    "order": "",
    "family": "",
    "genus": "",
    "specificEpithet": "",
    "infraspecificEpithet": "",
    "taxonRank": "kingdom",
}

HYPOGYMNIA = taxon(
    "Hypogymnia",
    "Tube Lichen",
    "Fungi",
    "Ascomycota",
    "Lecanoromycetes",
    "Lecanorales",
    "Parmeliaceae",
    "Hypogymnia",
    taxon_rank="genus",
)

ARCTIIDAE = taxon(
    "Arctiidae",
    "Lichen Moth",
    "Animalia",
    "Arthropoda",
    "Insecta",
    "Lepidoptera",
    "Arctiidae",
    taxon_rank="family",
)

CHIROPTERA = taxon(
    "Chiroptera",
    "Bats",
    "Animalia",
    "Chordata",
    "Mammalia",
    "Chiroptera",
    taxon_rank="order",
)

CLARKIA_GENUS = taxon(
    "Clarkia",
    "Clarkia",
    "Plantae",
    "Tracheophyta",
    "Magnoliopsida",
    "Myrtales",
    "Onagraceae",
    "Clarkia",
    taxon_rank="genus",
)

CLARKIA_UNGUICULATA = taxon(
    "Clarkia unguiculata",
    "Elegant Clarkia",
    "Plantae",
    "Tracheophyta",
    "Magnoliopsida",
    "Myrtales",
    "Onagraceae",
    "Clarkia",
    "unguiculata",
    taxon_rank="species",
)

CLARKIA_EPILOBIOIDES = taxon(
    "Clarkia epilobioides",
    "Canyon Clarkia",
    "Plantae",
    "Tracheophyta",
    "Magnoliopsida",
    "Myrtales",
    "Onagraceae",
    "Clarkia",
    "epilobioides",
    taxon_rank="species",
)

CLARKIA_CYLINDRICA = taxon(
    "Clarkia cylindrica",
    "Speckled Clarkia",
    "Plantae",
    "Tracheophyta",
    "Magnoliopsida",
    "Myrtales",
    "Onagraceae",
    "Clarkia",
    "cylindrica",
    taxon_rank="species",
)

CLARKIA_PURPUREA_QUADRIVULNERA = taxon(
    "Clarkia purpurea subsp. quadrivulnera",
    "Winecup Clarkia",
    "Plantae",
    "Tracheophyta",
    "Magnoliopsida",
    "Myrtales",
    "Onagraceae",
    "Clarkia",
    "purpurea",
    "quadrivulnera",
    "subspecies",
)

PHYSALIS_PHILADELPHICA_IXOCARPA = taxon(
    "Physalis philadelphica subsp. ixocarpa",
    "Tomatillo",
    "Plantae",
    "Tracheophyta",
    "Magnoliopsida",
    "Solanales",
    "Solanaceae",
    "Physalis",
    "philadelphica",
    "ixocarpa",
    "subspecies",
)


def fungi_lichen(vernacular_name):
    return {
        "scientificName": "Fungi",
        "vernacularName": vernacular_name,
        **FUNGI_LICHEN,
    }


CORRECTIONS = {
    # Lichen common-name false matches to moths/beetles/plants.
    "5f7c43fc-e3b0-4534-a7ab-019deae4500a": fungi_lichen("Lichens"),
    "f3ebaed0-564d-4b36-a135-0f33715c7075": fungi_lichen("lichens"),
    "dd59c468-d18d-4e38-a057-ce371b8c20f4": fungi_lichen("lichens"),
    "de917fe4-8041-4c90-af58-c31a2a01b0ee": fungi_lichen("Lichens"),
    "70e405c4-7424-40a2-a0ca-d4caf4b15bf5": fungi_lichen("crustose lichen"),
    "16d1039a-e27b-44e6-982c-ea864385c9ae": fungi_lichen("Lichen"),
    "84ef345f-bb2f-4180-85fc-c223144b9cef": fungi_lichen("lichens"),
    "9021699e-77a4-4939-a0e1-8862dc6c93e0": HYPOGYMNIA,
    "3fbe687a-cfc5-4cdc-a5ed-036f3717c5a9": HYPOGYMNIA,
    "aae829b5-1e26-47bb-9a32-77991fe48f4b": HYPOGYMNIA,
    "f1ccc929-ec5e-4deb-95d5-082d4b9ee218": HYPOGYMNIA,
    "7bbd6223-119d-4bec-9158-439b799ef832": HYPOGYMNIA,
    "7505aad5-688f-44a0-b202-f3193a6d7e6a": ARCTIIDAE,
    "8b30c36a-5934-4c7a-a254-2351dd4335c1": ARCTIIDAE,
    # Anabat detector / bat poster false match.
    "c7b08f5f-55d8-4db5-b445-ea86aca5256c": CHIROPTERA,
    # Farewell-to-Spring false matches to Farewellia.
    "4dd64363-557b-47d5-aee7-e6480b2e49eb": CLARKIA_UNGUICULATA,
    "c306cbf5-ce28-4baf-8413-525be9b72b7f": CLARKIA_UNGUICULATA,
    "06c8a195-dec9-4e78-9ffc-299ad20d29e8": CLARKIA_UNGUICULATA,
    "1b5e9894-1361-4560-b7ff-65105967099b": CLARKIA_UNGUICULATA,
    "d724b2c5-56f5-4070-9105-6d00cb4162bc": CLARKIA_UNGUICULATA,
    "9b984d45-d5e0-411c-88ac-e38b2a1845dc": CLARKIA_EPILOBIOIDES,
    "f2599e01-aab9-427a-9fb2-f4d194338aac": CLARKIA_EPILOBIOIDES,
    "152514c5-98ae-4a8a-88c2-3cf7482c24ab": CLARKIA_CYLINDRICA,
    "5a191721-167b-4959-9f8c-3f1abf1549a4": CLARKIA_CYLINDRICA,
    "4d93a1c8-2a88-48d3-9338-b9158fcdabf8": CLARKIA_CYLINDRICA,
    "995f1afd-45b2-4ee8-8ce5-c63536b528af": CLARKIA_PURPUREA_QUADRIVULNERA,
    # Clear Clarkia rows previously assigned to Coleoptera.
    "9926ab3c-1dd9-45e2-b194-58afc39e8a26": CLARKIA_GENUS,
    "f9b083b8-2e68-4e20-91d5-59ffaed8acc4": CLARKIA_GENUS,
    # Tomatillo was left at genus from the Physalis ixocarpa synonym.
    "e517f7c4-39be-4110-8cb9-224fd80312df": PHYSALIS_PHILADELPHICA_IXOCARPA,
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
    required = ["occurrenceID", *next(iter(CORRECTIONS.values())).keys()]
    missing = [name for name in required if name not in idx]
    if missing:
        raise SystemExit(f"occurrence.tsv missing columns: {missing}")

    touched = []
    width = len(header)
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise SystemExit(f"occurrence.tsv row {line_number} has {len(row)} columns, expected {width}")
        occurrence_id = row[idx["occurrenceID"]]
        correction = CORRECTIONS.get(occurrence_id)
        if not correction:
            continue
        before = row[idx["scientificName"]]
        for column, value in correction.items():
            row[idx[column]] = value
        touched.append((line_number, occurrence_id, before, correction["scientificName"]))

    missing_ids = sorted(set(CORRECTIONS) - {occurrence_id for _, occurrence_id, _, _ in touched})
    if missing_ids:
        raise SystemExit(f"occurrence.tsv missing target IDs: {missing_ids}")
    write_tsv(OCCURRENCE, rows, newline)
    return touched


def update_media():
    rows, newline = read_tsv(MEDIA)
    header = rows[0]
    idx = {name: pos for pos, name in enumerate(header)}
    for column in ["occurrenceID", "scientificName", "vernacularName"]:
        if column not in idx:
            raise SystemExit(f"associatedMedia.tsv missing column: {column}")

    touched = []
    width = len(header)
    for line_number, row in enumerate(rows[1:], start=2):
        if len(row) != width:
            raise SystemExit(f"associatedMedia.tsv row {line_number} has {len(row)} columns, expected {width}")
        occurrence_id = row[idx["occurrenceID"]]
        correction = CORRECTIONS.get(occurrence_id)
        if not correction:
            continue
        before = row[idx["scientificName"]]
        row[idx["scientificName"]] = correction["scientificName"]
        row[idx["vernacularName"]] = correction["vernacularName"]
        touched.append((line_number, occurrence_id, before, correction["scientificName"]))

    missing_ids = sorted(set(CORRECTIONS) - {occurrence_id for _, occurrence_id, _, _ in touched})
    if missing_ids:
        raise SystemExit(f"associatedMedia.tsv missing target IDs: {missing_ids}")
    write_tsv(MEDIA, rows, newline)
    return touched


def main():
    occurrence_touched = update_occurrence()
    media_touched = update_media()
    print(f"Updated occurrence.tsv records: {len(occurrence_touched)}")
    print(f"Updated associatedMedia.tsv records: {len(media_touched)}")
    for line_number, occurrence_id, before, after in occurrence_touched:
        print(f"{line_number}\t{occurrence_id}\t{before}\t{after}")


if __name__ == "__main__":
    main()
