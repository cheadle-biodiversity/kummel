#!/usr/bin/env python3
"""Recheck only the associated media URLs that failed in the prior URL pass."""

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


PREVIOUS_FAILURES = Path(
    "/Users/seltmann/Documents/kummel/work/associated_media_url_check_failures_20260730_135756.tsv"
)
WORK = Path("/Users/seltmann/Documents/kummel/work")
TIMEOUT_SECONDS = 20
MAX_WORKERS = 8
RETRIES = 1


def read_rows():
    with PREVIOUS_FAILURES.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"line", "occurrenceID", "identifier"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"previous failures TSV missing columns: {sorted(missing)}")
        return [
            {
                "line": row["line"],
                "occurrenceID": row["occurrenceID"],
                "identifier": row["identifier"],
                "previous_status": row.get("status", ""),
            }
            for row in reader
        ]


def request_url(url: str, method: str):
    headers = {"User-Agent": "Codex DwC-A targeted URL rechecker"}
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
    last = None
    for attempt in range(RETRIES + 1):
        last = request_url(row["identifier"], "HEAD")
        if last["status"] == 200:
            break
        range_result = request_url(row["identifier"], "GET")
        if range_result["status"] in (200, 206):
            last = range_result
            break
        if range_result["status"] and range_result["status"] != last["status"]:
            last = range_result
        if attempt < RETRIES:
            time.sleep(0.5)

    content_type = last["content_type"].lower()
    ok = last["status"] in (200, 206) and "image/jpeg" in content_type
    return {
        **row,
        **last,
        "ok": "yes" if ok else "no",
        "is_500_error": "yes" if last["status"] in (500, 501, 502, 503, 504) else "no",
    }


def main():
    rows = read_rows()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = WORK / f"previously_failed_media_url_recheck_{timestamp}.tsv"
    failures_path = WORK / f"previously_failed_media_url_recheck_failures_{timestamp}.tsv"

    print(f"Rechecking {len(rows)} previously failed identifier URLs with {MAX_WORKERS} workers...")
    print(f"All-results output: {result_path}")
    print(f"Failures output: {failures_path}")
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
                print(f"progress\t{completed}/{len(rows)}\t{rate:.1f} urls/sec")
                sys.stdout.flush()

    results.sort(key=lambda item: int(item["line"]))
    fieldnames = [
        "line",
        "occurrenceID",
        "identifier",
        "previous_status",
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
    failures = [item for item in results if item["ok"] != "yes"]
    for path, selected in [(result_path, results), (failures_path, failures)]:
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

    status_counts = {}
    for item in results:
        status_counts[str(item["status"])] = status_counts.get(str(item["status"]), 0) + 1
    errors_500 = [item for item in results if item["is_500_error"] == "yes"]

    print("SUMMARY")
    print(f"checked\t{len(results)}")
    print(f"resolved_now\t{len(results) - len(failures)}")
    print(f"still_failing\t{len(failures)}")
    print(f"http_500_family_errors\t{len(errors_500)}")
    print(f"status_counts\t{status_counts}")
    if failures:
        print("FAILURE_EXAMPLES")
        for item in failures[:20]:
            print(
                f"{item['line']}\t{item['occurrenceID']}\t{item['status']}\t"
                f"{item['method']}\t{item['error']}\t{item['identifier']}"
            )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
