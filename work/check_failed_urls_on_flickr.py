#!/usr/bin/env python3
"""Look up failed Symbiota JPG identifiers on Flickr using photo IDs."""

from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
from pathlib import Path
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


FAILURES = Path("/Users/seltmann/Documents/kummel/work/associated_media_url_check_failures_20260730_135756.tsv")
WORK = Path("/Users/seltmann/Documents/kummel/work")
MAX_WORKERS = 6
TIMEOUT_SECONDS = 20
RETRIES = 1


def read_failed_rows():
    with FAILURES.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = []
        for row in reader:
            filename = Path(urlparse(row["identifier"]).path).name
            photo_id = Path(filename).stem
            rows.append({**row, "filename": filename, "photo_id": photo_id})
        return rows


def fetch_oembed(photo_id: str):
    flickr_page = f"https://www.flickr.com/photos/treebeard/{photo_id}/"
    endpoint = "https://www.flickr.com/services/oembed/?" + urlencode(
        {"format": "json", "url": flickr_page}
    )
    request = Request(endpoint, headers={"User-Agent": "Codex DwC-A Flickr lookup"})
    started = time.monotonic()
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            elapsed_ms = round((time.monotonic() - started) * 1000)
            data = json.loads(body)
            return {
                "lookup_status": response.status,
                "found_on_flickr": "yes" if data.get("type") == "photo" and data.get("url") else "no",
                "flickr_page": data.get("web_page") or flickr_page,
                "static_flickr_url": data.get("url", ""),
                "thumbnail_url": data.get("thumbnail_url", ""),
                "title": data.get("title", ""),
                "author_name": data.get("author_name", ""),
                "license": data.get("license", ""),
                "error": "",
                "elapsed_ms": elapsed_ms,
            }
    except HTTPError as error:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        return {
            "lookup_status": error.code,
            "found_on_flickr": "no",
            "flickr_page": flickr_page,
            "static_flickr_url": "",
            "thumbnail_url": "",
            "title": "",
            "author_name": "",
            "license": "",
            "error": f"HTTPError: {error.reason}",
            "elapsed_ms": elapsed_ms,
        }
    except (json.JSONDecodeError, URLError, TimeoutError, socket.timeout) as error:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        return {
            "lookup_status": "",
            "found_on_flickr": "no",
            "flickr_page": flickr_page,
            "static_flickr_url": "",
            "thumbnail_url": "",
            "title": "",
            "author_name": "",
            "license": "",
            "error": f"{type(error).__name__}: {error}",
            "elapsed_ms": elapsed_ms,
        }


def check_one(row):
    result = None
    for attempt in range(RETRIES + 1):
        result = fetch_oembed(row["photo_id"])
        if result["found_on_flickr"] == "yes" or attempt == RETRIES:
            break
        time.sleep(0.5)
    return {**row, **result}


def main():
    rows = read_failed_rows()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_path = WORK / f"flickr_lookup_failed_media_{timestamp}.tsv"
    found_path = WORK / f"flickr_lookup_failed_media_found_{timestamp}.tsv"
    not_found_path = WORK / f"flickr_lookup_failed_media_not_found_{timestamp}.tsv"

    print(f"Checking {len(rows)} failed IDs on Flickr with {MAX_WORKERS} workers...")
    print(f"All-results output: {all_path}")
    print(f"Found output: {found_path}")
    print(f"Not-found output: {not_found_path}")
    sys.stdout.flush()

    results = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_one, row) for row in rows]
        for completed, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            if completed % 100 == 0 or completed == len(rows):
                elapsed = time.monotonic() - started
                rate = completed / elapsed if elapsed else 0
                print(f"progress\t{completed}/{len(rows)}\t{rate:.1f} ids/sec")
                sys.stdout.flush()

    results.sort(key=lambda item: int(item["line"]))
    fieldnames = [
        "line",
        "occurrenceID",
        "status",
        "identifier",
        "filename",
        "photo_id",
        "found_on_flickr",
        "lookup_status",
        "flickr_page",
        "static_flickr_url",
        "thumbnail_url",
        "title",
        "author_name",
        "license",
        "elapsed_ms",
        "error",
    ]
    for path, selected in [
        (all_path, results),
        (found_path, [row for row in results if row["found_on_flickr"] == "yes"]),
        (not_found_path, [row for row in results if row["found_on_flickr"] != "yes"]),
    ]:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
                delimiter="\t",
                lineterminator="\n",
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(selected)

    found = [row for row in results if row["found_on_flickr"] == "yes"]
    not_found = [row for row in results if row["found_on_flickr"] != "yes"]
    print("SUMMARY")
    print(f"checked\t{len(results)}")
    print(f"found_on_flickr\t{len(found)}")
    print(f"not_found_or_lookup_failed\t{len(not_found)}")
    if found:
        print("FOUND_EXAMPLES")
        for row in found[:10]:
            print(f"{row['line']}\t{row['photo_id']}\t{row['flickr_page']}\t{row['static_flickr_url']}")
    if not_found:
        print("NOT_FOUND_EXAMPLES")
        for row in not_found[:10]:
            print(f"{row['line']}\t{row['photo_id']}\t{row['lookup_status']}\t{row['error']}")


if __name__ == "__main__":
    main()
