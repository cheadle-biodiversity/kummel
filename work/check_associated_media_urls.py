#!/usr/bin/env python3
"""Check every associatedMedia.tsv identifier URL for online resolution."""

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


ARCHIVE = Path("/Users/seltmann/Documents/kummel/dwca_kummel_2026")
MEDIA = ARCHIVE / "associatedMedia.tsv"
WORK = Path("/Users/seltmann/Documents/kummel/work")
TIMEOUT_SECONDS = 20
MAX_WORKERS = 8
RETRIES = 1


def read_media_rows():
    with MEDIA.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"occurrenceID", "identifier"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"associatedMedia.tsv missing columns: {sorted(missing)}")
        return [
            {
                "line": line_number,
                "occurrenceID": row["occurrenceID"],
                "identifier": row["identifier"],
            }
            for line_number, row in enumerate(reader, start=2)
        ]


def request_url(url: str, method: str):
    headers = {"User-Agent": "Codex DwC-A URL checker"}
    if method == "GET":
        headers["Range"] = "bytes=0-0"
    request = Request(url, headers=headers, method=method)
    started = time.monotonic()
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            elapsed_ms = round((time.monotonic() - started) * 1000)
            return {
                "status": response.status,
                "error": "",
                "content_type": response.headers.get("Content-Type", ""),
                "content_length": response.headers.get("Content-Length", ""),
                "effective_url": response.geturl(),
                "method": method,
                "elapsed_ms": elapsed_ms,
            }
    except HTTPError as error:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        return {
            "status": error.code,
            "error": f"HTTPError: {error.reason}",
            "content_type": error.headers.get("Content-Type", "") if error.headers else "",
            "content_length": error.headers.get("Content-Length", "") if error.headers else "",
            "effective_url": error.geturl(),
            "method": method,
            "elapsed_ms": elapsed_ms,
        }
    except (URLError, TimeoutError, socket.timeout) as error:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        return {
            "status": "",
            "error": f"{type(error).__name__}: {error}",
            "content_type": "",
            "content_length": "",
            "effective_url": "",
            "method": method,
            "elapsed_ms": elapsed_ms,
        }


def check_one(row):
    url = row["identifier"]
    last = None
    for _ in range(RETRIES + 1):
        last = request_url(url, "HEAD")
        if last["status"] == 200:
            break
        # Some servers do not treat HEAD like GET. Verify odd responses with
        # a one-byte range request before recording a failure.
        if last["status"] not in (500, 501, 502, 503, 504):
            range_result = request_url(url, "GET")
            if range_result["status"] in (200, 206):
                last = range_result
                break
        time.sleep(0.5)

    status = last["status"]
    content_type = last["content_type"].lower()
    ok = status in (200, 206) and "image/jpeg" in content_type
    return {
        **row,
        **last,
        "ok": "yes" if ok else "no",
        "is_500_error": "yes" if status in (500, 501, 502, 503, 504) else "no",
    }


def main():
    rows = read_media_rows()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = WORK / f"associated_media_url_check_{timestamp}.tsv"
    failures_path = WORK / f"associated_media_url_check_failures_{timestamp}.tsv"

    print(f"Checking {len(rows)} identifier URLs with {MAX_WORKERS} workers...")
    print(f"All-results output: {result_path}")
    print(f"Failures output: {failures_path}")
    sys.stdout.flush()

    results = []
    completed = 0
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_one, row) for row in rows]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            if completed % 500 == 0 or completed == len(rows):
                elapsed = time.monotonic() - started
                rate = completed / elapsed if elapsed else 0
                print(f"progress\t{completed}/{len(rows)}\t{rate:.1f} urls/sec")
                sys.stdout.flush()

    fieldnames = [
        "line",
        "occurrenceID",
        "identifier",
        "ok",
        "is_500_error",
        "status",
        "method",
        "content_type",
        "content_length",
        "effective_url",
        "elapsed_ms",
        "error",
    ]
    results.sort(key=lambda item: item["line"])
    with result_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)

    failures = [item for item in results if item["ok"] != "yes"]
    with failures_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(failures)

    errors_500 = [item for item in results if item["is_500_error"] == "yes"]
    status_counts = {}
    for item in results:
        status_counts[str(item["status"])] = status_counts.get(str(item["status"]), 0) + 1

    print("SUMMARY")
    print(f"checked\t{len(results)}")
    print(f"ok_image_jpeg_200_or_206\t{len(results) - len(failures)}")
    print(f"failures\t{len(failures)}")
    print(f"http_500_family_errors\t{len(errors_500)}")
    print(f"status_counts\t{status_counts}")
    if failures:
        print("FAILURE_EXAMPLES")
        for item in failures[:25]:
            print(
                f"{item['line']}\t{item['occurrenceID']}\t{item['status']}\t"
                f"{item['method']}\t{item['error']}\t{item['identifier']}"
            )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
