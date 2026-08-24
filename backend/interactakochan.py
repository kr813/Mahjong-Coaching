from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RESULT_DIR = Path(__file__).resolve().parent / "result"
SOURCE_DIR = Path(__file__).resolve().parent / "source"

DEFAULT_ENDPOINT = os.environ.get("MJAI_REVIEWER_ENDPOINT", "http://localhost:8000/report")


def resolve_json_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (SOURCE_DIR / candidate).resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call the Flask report endpoint with curl")
    parser.add_argument("--file", help="Local JSON file to upload")
    parser.add_argument("--json", help="JSON body file path")
    parser.add_argument("--url", help="Tenhou log URL")
    parser.add_argument("--seat", type=int, default=0, choices=range(0, 4), help="Seat number 0..3")
    parser.add_argument("--endpoint", default="http://localhost:8000/report", help="Flask report endpoint")
    return parser


def _run_command(command: list[str]) -> str:
    print("Running:", " ".join(command))
    completed = subprocess.run(command, capture_output=True)
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}\n"
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )
    return stdout


def _build_curl_command(source_type: str, source: str | None, seat: int, endpoint: str) -> list[str]:
    endpoint_with_seat = f"{endpoint}?seat={seat}"
    command = ["curl", "-X", "POST", endpoint_with_seat]
    if source_type == "url":
        command.extend(["-G", "--data-urlencode", "source_type=url", "--data-urlencode", f"url={source}"])
    elif source_type == "file":
        command.extend(["-F", f"file=@{source}"])
    elif source_type == "json":
        command.extend(["-H", "Content-Type: application/json", "--data-binary", f"@{source}"])
    else:
        raise ValueError("source_type must be one of url, file, json")
    return command


def call_report(
    source_type: str,
    file_path: str | None = None,
    json_path: str | None = None,
    url: str | None = None,
    seat: int = 0,
    endpoint: str | None = None,
) -> str:
    endpoint = endpoint or DEFAULT_ENDPOINT
    if not endpoint:
        raise ValueError("endpoint is required (or set MJAI_REVIEWER_ENDPOINT)")

    source = None
    if source_type == "url":
        if not url:
            raise ValueError("url is required for source_type=url")
        source = url
    elif source_type == "file":
        if not file_path:
            raise ValueError("file_path is required for source_type=file")
        source = file_path
    elif source_type == "json":
        if not json_path:
            raise ValueError("json_path is required for source_type=json")
        source = json_path
    else:
        raise ValueError("source_type must be one of url, file, json")

    command = _build_curl_command(source_type, source, seat, endpoint)
    return _run_command(command)


def run_curl(args: argparse.Namespace) -> int:
    if not any([args.file, args.json, args.url]):
        print("Error: one of --file, --json, or --url is required", file=sys.stderr)
        return 1

    if args.file and not os.path.exists(args.file):
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        return 1

    if args.json:
        resolved_json_path = resolve_json_path(args.json)
        if not resolved_json_path.exists():
            print(f"Error: JSON file not found: {args.json}", file=sys.stderr)
            return 1
    else:
        resolved_json_path = None

    source_kind = "url" if args.url else "json" if args.json else "file"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = RESULT_DIR / f"{source_kind}-{timestamp}.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    endpoint = f"{args.endpoint}?seat={args.seat}"
    cmd = ["curl", "-X", "POST", endpoint]

    if args.url:
        cmd.extend(["-G", "--data-urlencode", f"source_type=url", "--data-urlencode", f"url={args.url}"])
    elif args.file:
        cmd.extend(["-F", f"file=@{args.file}"])
    else:
        cmd.extend(["-H", "Content-Type: application/json", "--data-binary", f"@{resolved_json_path}"])

    cmd.extend(["-o", str(output_path)])

    print("Running:", " ".join(cmd))
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0:
        if completed.stderr:
            print(completed.stderr, file=sys.stderr)
        return completed.returncode

    print(f"Saved output to {output_path}")
    return 0
