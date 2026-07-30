#!/usr/bin/env python3
"""Download recovered Flickr images using the expected Symbiota JPG filenames."""

from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


LOOKUP = Path("/Users/seltmann/Documents/kummel/work/flickr_lookup_failed_media_found_20260730_150615.tsv")
WORK = Path("/Users/seltmann/Documents/kummel/work")
DOWNLOAD_DIR = WORK / f"flickr_recovered_missing_media_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
MANIFEST = DOWNLOAD_DIR / "download_manifest.tsv"
FAILURES = DOWNLOAD_DIR / "download_failures.tsv"

MAX_WORKERS = 8
TIMEOUT_SECONDS = 60
RETRIES = 2


def read_rows():
    with LOOKUP.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"line", "occurrenceID", "filename", "static_flickr_url", "flickr_page", "title"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"lookup TSV missing columns: {sorted(missing)}")
        rows = []
        for row in reader:
            if row.get("found_on_flickr") != "yes":
                continue
            rows.append(row)
        return rows


def is_jpeg(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            start = handle.read(3)
            if start != b"\xff\xd8\xff":
                return False
            handle.seek(-2, 2)
            return handle.read(2) == b"\xff\xd9"
    except OSError:
        return False


def download_one(row):
    output_path = DOWNLOAD_DIR / row["filename"]
    url = row["static_flickr_url"]
    for attempt in range(RETRIES + 1):
        started = time.monotonic()
        try:
            request = Request(url, headers={"User-Agent": "Codex DwC-A Flickr image downloader"})
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "")
                data = response.read()
            elapsed_ms = round((time.monotonic() - started) * 1000)
            if status != 200 or "image/jpeg" not in content_type.lower():
                error = f"unexpected response status={status} content_type={content_type}"
                if attempt < RETRIES:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return {**row, "output_path": str(output_path), "status": status, "bytes": 0, "ok": "no", "elapsed_ms": elapsed_ms, "error": error}
            output_path.write_bytes(data)
            jpeg_ok = is_jpeg(output_path)
            return {
                **row,
                "output_path": str(output_path),
                "status": status,
                "bytes": len(data),
                "ok": "yes" if jpeg_ok else "no",
                "elapsed_ms": elapsed_ms,
                "error": "" if jpeg_ok else "downloaded file is not a valid complete JPEG",
            }
        except (HTTPError, URLError, TimeoutError, socket.timeout, OSError) as error:
            elapsed_ms = round((time.monotonic() - started) * 1000)
            if attempt < RETRIES:
                time.sleep(0.5 * (attempt + 1))
                continue
            return {
                **row,
                "output_path": str(output_path),
                "status": getattr(error, "code", ""),
                "bytes": 0,
                "ok": "no",
                "elapsed_ms": elapsed_ms,
                "error": f"{type(error).__name__}: {error}",
            }


def main():
    rows = read_rows()
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=False)
    print(f"Downloading {len(rows)} Flickr images with {MAX_WORKERS} workers...")
    print(f"Download directory: {DOWNLOAD_DIR}")
    sys.stdout.flush()

    results = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(download_one, row) for row in rows]
        for completed, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            if completed % 100 == 0 or completed == len(rows):
                elapsed = time.monotonic() - started
                rate = completed / elapsed if elapsed else 0
                print(f"progress\t{completed}/{len(rows)}\t{rate:.1f} images/sec")
                sys.stdout.flush()

    results.sort(key=lambda item: int(item["line"]))
    fieldnames = [
        "line",
        "occurrenceID",
        "filename",
        "output_path",
        "ok",
        "status",
        "bytes",
        "static_flickr_url",
        "flickr_page",
        "title",
        "elapsed_ms",
        "error",
    ]
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    failures = [row for row in results if row["ok"] != "yes"]
    with FAILURES.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(failures)

    ok = [row for row in results if row["ok"] == "yes"]
    total_bytes = sum(int(row["bytes"]) for row in ok)
    print("SUMMARY")
    print(f"requested\t{len(rows)}")
    print(f"downloaded_ok\t{len(ok)}")
    print(f"failed\t{len(failures)}")
    print(f"total_bytes\t{total_bytes}")
    print(f"manifest\t{MANIFEST}")
    print(f"failures\t{FAILURES}")
    if failures:
        print("FAILURE_EXAMPLES")
        for row in failures[:20]:
            print(f"{row['line']}\t{row['filename']}\t{row['status']}\t{row['error']}\t{row['static_flickr_url']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
