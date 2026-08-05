from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RESULT_DIR = Path(__file__).resolve().parent / "result"
SOURCE_DIR = Path(__file__).resolve().parent / "source"
DEFAULT_IMAGE = os.environ.get("MJAI_REVIEWER_IMAGE", "mjai-reviewer:latest")
DEFAULT_ENGINE = os.environ.get("MJAI_REVIEWER_ENGINE", "akochan")
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
    completed = subprocess.run(command, capture_output=True)
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}\n"
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )
    return stdout


def _build_docker_command(source_type: str, source: str | None, seat: int, engine: str) -> list[str]:
    command = ["sudo", "docker", "run", "--rm", "-e", "OMP_NUM_THREADS=8"]
    command.extend(["-e", "LD_LIBRARY_PATH=/mjai-reviewer/akochan", "-w", "/mjai-reviewer"])

    if source_type in {"file", "json"}:
        if not source:
            raise ValueError("source file path is required for file/json source_type")
        source_path = Path(source).resolve()
        source_dir = source_path.parent
        container_path = "/data"
        command.extend(["-v", f"{source_dir}:{container_path}"])
        source = f"{container_path}/{source_path.name}"

    command.append(DEFAULT_IMAGE)
    command.extend(["-e", engine])
    if source_type == "url":
        command.extend(["-u", source or ""])
    else:
        command.extend(["-i", source or ""])
    command.extend(["-a", str(seat), "-o", "-"])
    return command


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
    engine: str | None = None,
) -> str:
    engine = engine or DEFAULT_ENGINE
    endpoint = endpoint or DEFAULT_ENDPOINT
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

    if endpoint:
        command = _build_curl_command(source_type, source, seat, endpoint)
        return _run_command(command)

    command = _build_docker_command(source_type, source, seat, engine)
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

    try:
        if args.url:
            html = call_report(source_type="url", url=args.url, seat=args.seat, endpoint=args.endpoint)
        elif args.file:
            html = call_report(source_type="file", file_path=args.file, seat=args.seat, endpoint=args.endpoint)
        else:
            html = call_report(source_type="json", json_path=str(resolved_json_path), seat=args.seat, endpoint=args.endpoint)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    output_path.write_text(html, encoding="utf-8")
    print(f"Saved output to {output_path}")
    return 0
