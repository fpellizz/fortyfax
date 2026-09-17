"""Update checking against the GitHub releases of the public mirror.

Releases are published by the GitHub Actions workflow on the mirror
(`fpellizz/fortyfax`) whenever the Bitbucket pipeline mirrors a `v*` tag, with
the `.rpm` and `.deb` packages attached as assets. The GitHub API is used
because it is public and needs no authentication, unlike Bitbucket Downloads
on a private repository.

Nothing here touches the system: the new package is only downloaded, the
install command is left to the user.
"""

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import __version__, distro

log = logging.getLogger(__name__)

RELEASES_API = "https://api.github.com/repos/fpellizz/fortyfax/releases/latest"
RELEASES_PAGE = "https://github.com/fpellizz/fortyfax/releases"

_TIMEOUT_S = 10
_USER_AGENT = f"fortyfax/{__version__}"

# Un controllo al giorno: il limite GitHub non autenticato e' 60 richieste/ora
# per IP, ma non c'e' motivo di interrogare l'API a ogni avvio.
CHECK_INTERVAL_S = 24 * 60 * 60


@dataclass
class ReleaseInfo:
    """A release newer than the running version."""

    version: str  # "2.4.0" (without the leading "v")
    tag: str  # "v2.4.0"
    url: str  # release page on GitHub
    notes: str  # release notes (markdown, may be empty)
    asset_name: str = ""  # package matching this distro, if any
    asset_url: str = ""
    asset_size: int = 0


def parse_version(text: str) -> tuple[int, ...]:
    """"v2.10.1" -> (2, 10, 1). Non-numeric suffixes are dropped.

    Returns an empty tuple when nothing usable is found, which compares as
    lower than any real version.
    """
    match = re.search(r"(\d+(?:\.\d+)*)", text or "")
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer(candidate: str, current: str) -> bool:
    """True if `candidate` is a strictly newer version than `current`."""
    parsed_candidate = parse_version(candidate)
    if not parsed_candidate:
        return False
    return parsed_candidate > parse_version(current)


def _package_suffix() -> str:
    """The package extension for the running distro ('.rpm' / '.deb')."""
    return ".deb" if distro.pkg_manager() == "apt" else ".rpm"


def _pick_asset(assets: list[dict]) -> dict | None:
    """Pick the release asset matching this distro's package format."""
    suffix = _package_suffix()
    for asset in assets:
        if str(asset.get("name", "")).endswith(suffix):
            return asset
    return None


def fetch_latest_release(timeout: int = _TIMEOUT_S) -> dict | None:
    """Fetch the latest release from the GitHub API. None on any failure.

    An update check must never get in the way: no network, a rate limit or a
    malformed answer are all logged and ignored.
    """
    request = urllib.request.Request(
        RELEASES_API,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": _USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as e:
        log.info("Controllo aggiornamenti non riuscito: %s", e)
        return None


def check_for_update(current: str = __version__, timeout: int = _TIMEOUT_S) -> ReleaseInfo | None:
    """Return the latest release if newer than `current`, otherwise None."""
    data = fetch_latest_release(timeout=timeout)
    if not data:
        return None
    if data.get("draft") or data.get("prerelease"):
        return None

    tag = str(data.get("tag_name") or "")
    if not is_newer(tag, current):
        return None

    asset = _pick_asset(data.get("assets") or [])
    return ReleaseInfo(
        version=tag.lstrip("v"),
        tag=tag,
        url=str(data.get("html_url") or RELEASES_PAGE),
        notes=str(data.get("body") or ""),
        asset_name=str(asset.get("name", "")) if asset else "",
        asset_url=str(asset.get("browser_download_url", "")) if asset else "",
        asset_size=int(asset.get("size", 0)) if asset else 0,
    )


def download_dir() -> Path:
    """The user's download directory, falling back to the home directory."""
    try:
        from gi.repository import GLib

        path = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        if path:
            return Path(path)
    except Exception:  # GLib missing or no XDG user dirs configured
        pass
    return Path.home()


def download_asset(release: ReleaseInfo, dest_dir: Path | None = None,
                   progress=None, timeout: int = 60) -> Path:
    """Download the release package. Returns the path of the saved file.

    `progress` is called as progress(downloaded_bytes, total_bytes) — total is
    0 when the server does not report a length. Raises on failure.
    """
    if not release.asset_url:
        raise ValueError("Nessun pacchetto disponibile per questa distribuzione")

    dest_dir = dest_dir or download_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / release.asset_name
    # Scrittura su file temporaneo e rename finale: un download interrotto non
    # lascia un pacchetto troncato dall'aspetto valido.
    tmp = dest.with_name(dest.name + ".part")

    request = urllib.request.Request(release.asset_url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, open(tmp, "wb") as out:
            total = int(response.headers.get("Content-Length") or release.asset_size or 0)
            downloaded = 0
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total)
        os.replace(tmp, dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return dest


def install_command(package_path: Path) -> str:
    """The command to install a downloaded package on this distro.

    distro.pkg_manager() only ever returns "apt" or "dnf", the two families
    Fortyfax builds packages for.
    """
    if distro.pkg_manager() == "apt":
        return f"sudo apt install '{package_path}'"
    return f"sudo dnf install '{package_path}'"


def should_check_now(last_check: float, interval_s: int = CHECK_INTERVAL_S) -> bool:
    """True when enough time has passed since the last automatic check.

    A timestamp in the future (clock changed) also triggers a check rather
    than blocking updates until it is reached.
    """
    now = time.time()
    if not last_check or last_check > now:
        return True
    return (now - last_check) >= interval_s
