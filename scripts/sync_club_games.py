#!/usr/bin/env python3
"""Copy new public Google Drive SGF files into static/club_games/.

The folder link or id comes from the GOOGLE_DRIVE_FOLDER environment variable.
The folder must be shared as "Anyone with the link".

Exit 0 when the folder was read and every unambiguous new file was saved.
Exit 1 when the folder cannot be read or a download fails. Nothing is added.
Exit 2 when two Drive files share a file name. Unambiguous new files are still saved.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEST = REPO_ROOT / "static" / "club_games"
FOLDER_ID = re.compile(r"^[-\w]{25,}$")
LIST_ATTEMPTS = 3
DOWNLOAD_RETRIES = 2

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CLASH = 2


@dataclass(frozen=True)
class DriveFile:
    id: str
    path: str

    @property
    def name(self) -> str:
        return Path(self.path).name


@dataclass(frozen=True)
class SyncPlan:
    to_download: list[DriveFile]
    clashes: list[list[DriveFile]]


def _drive_host(netloc: str) -> bool:
    host = netloc.lower().split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host == "drive.google.com"


def folder_id(value: str) -> str:
    """Return a Drive folder id from a sharing link or a bare id."""
    text = value.strip()
    if not text:
        raise ValueError("GOOGLE_DRIVE_FOLDER is empty")
    if "://" not in text and (
        text.startswith("drive.google.com/")
        or text.startswith("drive.google.com?")
        or text.startswith("www.drive.google.com/")
        or text.startswith("www.drive.google.com?")
    ):
        text = "https://" + text
    if "://" not in text:
        if FOLDER_ID.fullmatch(text):
            return text
        raise ValueError(
            "GOOGLE_DRIVE_FOLDER must be a sharing link or a folder id"
        )
    parsed = urllib.parse.urlparse(text)
    if not _drive_host(parsed.netloc):
        raise ValueError(
            "GOOGLE_DRIVE_FOLDER must be a drive.google.com sharing link or a folder id"
        )
    match = re.search(r"/folders/([-\w]{25,})", parsed.path)
    if match:
        return match.group(1)
    ids = urllib.parse.parse_qs(parsed.query).get("id", [])
    if len(ids) == 1 and FOLDER_ID.fullmatch(ids[0]):
        return ids[0]
    raise ValueError(
        "Could not read a Google Drive folder id from GOOGLE_DRIVE_FOLDER"
    )


def existing_sgf_names(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".sgf"
    }


def plan_sync(files: list[DriveFile], existing_names: set[str]) -> SyncPlan:
    """Choose SGF files to add.

    Names are compared case-insensitively. Files in subfolders are saved by
    their base name. Two different Drive files with the same base name are a
    clash and are not downloaded. The same Drive id listed twice is one file.
    """
    grouped: dict[str, list[DriveFile]] = {}
    for item in files:
        if not item.name.lower().endswith(".sgf"):
            continue
        if item.name in {"", ".", ".."}:
            continue
        group = grouped.setdefault(item.name.casefold(), [])
        if any(present.id == item.id for present in group):
            continue
        group.append(item)

    present = {name.casefold() for name in existing_names}
    to_download: list[DriveFile] = []
    clashes: list[list[DriveFile]] = []
    for key, group in grouped.items():
        if len(group) > 1:
            clashes.append(group)
            continue
        if key in present:
            continue
        to_download.append(group[0])
    return SyncPlan(to_download=to_download, clashes=clashes)


def looks_like_html(path: Path) -> bool:
    with path.open("rb") as handle:
        head = handle.read(256).lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def list_drive_files(drive_folder_id: str) -> list[DriveFile]:
    import gdown

    last_error: Exception | None = None
    for attempt in range(1, LIST_ATTEMPTS + 1):
        try:
            listed = gdown.download_folder(
                id=drive_folder_id,
                skip_download=True,
                quiet=True,
                timeout=(30, 120),
            )
        except Exception as exc:
            last_error = exc
            print(f"Listing attempt {attempt} failed: {exc}", file=sys.stderr)
            if attempt < LIST_ATTEMPTS:
                time.sleep(5)
            continue
        if listed is None:
            last_error = RuntimeError("gdown returned no file list")
            print(f"Listing attempt {attempt} failed: {last_error}", file=sys.stderr)
            if attempt < LIST_ATTEMPTS:
                time.sleep(5)
            continue
        return [DriveFile(id=item.id, path=item.path) for item in listed]
    assert last_error is not None
    raise last_error


def download_files(files: list[DriveFile], directory: Path) -> bool:
    """Download into directory. Return False when any download fails."""
    import gdown

    for item in files:
        target = directory / item.name
        print(f"Downloading {item.path}")
        try:
            saved = gdown.download(
                id=item.id,
                output=str(target),
                quiet=False,
                retries=DOWNLOAD_RETRIES,
                timeout=(30, 120),
            )
        except Exception as exc:
            print(f"Failed to download {item.path}: {exc}", file=sys.stderr)
            return False
        if not isinstance(saved, str) or not target.is_file():
            print(f"Failed to download {item.path}", file=sys.stderr)
            return False
        if target.stat().st_size == 0 or looks_like_html(target):
            print(
                f"{item.path} is empty or an HTML page, not an SGF file",
                file=sys.stderr,
            )
            return False
    return True


def copy_downloads(files: list[DriveFile], directory: Path) -> bool:
    present = {name.casefold() for name in existing_sgf_names(DEST)}
    staged = []
    for item in files:
        source = directory / item.name
        if item.name.casefold() in present:
            print(f"Refusing to overwrite {item.name}", file=sys.stderr)
            return False
        if not source.is_file() or looks_like_html(source):
            print(f"{item.name} is not an SGF file", file=sys.stderr)
            return False
        staged.append((source, DEST / item.name, item.name))
        present.add(item.name.casefold())
    DEST.mkdir(parents=True, exist_ok=True)
    for source, target, name in staged:
        shutil.copyfile(source, target)
        print(f"Added static/club_games/{name}")
    return True


def report_clashes(clashes: list[list[DriveFile]]) -> None:
    print(
        "These Google Drive files use the same name and were left out:",
        file=sys.stderr,
    )
    for group in clashes:
        print(f"- {group[0].name}", file=sys.stderr)
        for item in group:
            print(f"  {item.path} ({item.id})", file=sys.stderr)


def main() -> int:
    try:
        drive_folder_id = folder_id(os.environ.get("GOOGLE_DRIVE_FOLDER", ""))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return EXIT_ERROR

    try:
        files = list_drive_files(drive_folder_id)
    except Exception as exc:
        print(f"Failed to list the Google Drive folder: {exc}", file=sys.stderr)
        return EXIT_ERROR

    plan = plan_sync(files, existing_sgf_names(DEST))
    sgf_count = sum(1 for item in files if item.name.lower().endswith(".sgf"))
    print(f"Found {sgf_count} SGF file(s) in Google Drive.")
    print(f"Adding {len(plan.to_download)} new file(s).")

    if plan.to_download:
        with tempfile.TemporaryDirectory() as temp_name:
            directory = Path(temp_name)
            ready = download_files(plan.to_download, directory) and copy_downloads(
                plan.to_download, directory
            )
        if not ready:
            if plan.clashes:
                report_clashes(plan.clashes)
            return EXIT_ERROR

    if plan.clashes:
        report_clashes(plan.clashes)
        return EXIT_CLASH
    if not plan.to_download:
        print("No new club games.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
