# Document Provenance and AI Assistance Statement

Dataset package: **Marc Kummel Photography**

Darwin Core Archive: `/Users/seltmann/Documents/kummel/dwca_kummel_2026.zip`

Prepared: 2026-07-31

## Provenance

This Darwin Core Archive was prepared from component data files supplied by the dataset preparer for the Marc Kummel Photography dataset. The working archive folder is:

`/Users/seltmann/Documents/kummel/dwca_kummel_2026`

The final archive contains four root-level files:

- `occurrence.tsv`
- `associatedMedia.tsv`
- `meta.xml`
- `eml.xml`

The final package contains 18,896 occurrence records and 18,896 associated media records. The final ZIP checksum is:

`a7292970052fea7eb2e943e6445dbd74ff0ca60283f7b60a99833a7ba214ac3b`

## AI Assistance

OpenAI Codex was used as an AI-assisted data curation and validation tool during preparation of this archive. AI assistance was limited to file inspection, scripted data transformation, quality-control checks, report generation, and implementation of curator-directed corrections.

AI-assisted work included:

- checking `meta.xml` field mappings, delimiters, row types, file locations, and header alignment;
- checking TSV row widths, blank rows, quoting artifacts, line endings, duplicate identifiers, and UUID syntax;
- validating core-extension joins between `occurrence.tsv` and `associatedMedia.tsv`;
- comparing media URL fields between occurrence and associated media records;
- updating image path year segments from `/kummel/2025/` to `/kummel/2026/` when directed;
- checking online resolution of image URLs and locating previously missing images on Flickr;
- applying curator-directed taxonomic cleanup to selected records;
- removing redundant `associatedTaxa` entries that exactly duplicated the record `scientificName`;
- rebuilding and validating the final Darwin Core Archive ZIP.

AI assistance did not create the original observations, photographs, captions, collection events, or field evidence. Taxonomic changes were based on curator direction, record text, existing captions/remarks, and targeted name checks; they were not the result of independent specimen examination by the AI system.

## Human Review and Responsibility

The dataset preparer directed the curation decisions and reviewed the major correction steps. The AI-generated scripts and validation reports should be treated as aids to human review, not as a substitute for expert taxonomic determination or institutional data approval.

The final internal consistency check reported:

- errors: 0
- warnings: 0
- successful checks: 45

The final validation report is:

`/Users/seltmann/Documents/kummel/work/dwca_internal_consistency_report_20260730_154457.txt`

## Change Traceability

Timestamped backups were created before major edit steps. Supporting scripts and reports are stored in:

`/Users/seltmann/Documents/kummel/work`

These files provide an audit trail for the transformations and quality checks performed during this AI-assisted curation session.
