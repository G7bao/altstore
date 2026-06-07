#!/usr/bin/env python3
"""
MA1 PLUS — Automated Source Updater
====================================
Fetches the latest IPA releases from configured GitHub repositories
and updates the ma1plus.json source file with new versions, download
URLs, sizes, and changelogs.

Usage:
    python scripts/update_source.py

Requires:
    - GITHUB_TOKEN environment variable (for API rate limits)
    - requests library (pip install requests)
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Configuration: Map bundle identifiers to their GitHub release sources.
# Only apps hosted on GitHub with .ipa assets in releases can be auto-updated.
# ---------------------------------------------------------------------------
GITHUB_SOURCES = {
    "com.atebits.Tweetie2": {
        "owner": "BandarHL",
        "repo": "BHTwitter",
        "asset_pattern": r"BHTwitter.*\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "com.rileytestut.Delta": {
        "owner": "rileytestut",
        "repo": "Delta",
        "asset_pattern": r"Delta.*\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "org.provenance-emu.provenance": {
        "owner": "Provenance-Emu",
        "repo": "Provenance",
        "asset_pattern": r"Provenance.*iOS.*\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "org.ppsspp.ppsspp": {
        "owner": "hrydgard",
        "repo": "ppsspp",
        "asset_pattern": r"PPSSPP.*iOS.*\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "com.utmapp.UTM": {
        "owner": "utmapp",
        "repo": "UTM",
        "asset_pattern": r"^UTM\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "com.utmapp.UTM-SE": {
        "owner": "utmapp",
        "repo": "UTM",
        "asset_pattern": r"^UTM-SE\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "com.leminlimez.Cowabunga": {
        "owner": "leminlimez",
        "repo": "Cowabunga",
        "asset_pattern": r"Cowabunga.*\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "com.kdt.LiveContainer": {
        "owner": "LiveContainer",
        "repo": "LiveContainer",
        "asset_pattern": r"^LiveContainer\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "kh.crysalis.feather": {
        "owner": "claration",
        "repo": "Feather",
        "asset_pattern": r"Feather\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "com.SideStore.SideStore": {
        "owner": "SideStore",
        "repo": "SideStore",
        "asset_pattern": r"SideStore\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "com.alfiecg.TrollInstallerX": {
        "owner": "alfiecg24",
        "repo": "TrollInstallerX",
        "asset_pattern": r"^TrollInstallerX\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
    "app.nicegram": {
        "owner": "nicegram",
        "repo": "Nicegram-iOS",
        "asset_pattern": r"Nicegram\.ipa$",
        "version_pattern": r"build-([\d]+)",
    },
    "com.zhiliaoapp.musically": {
        "owner": "BandarHL",
        "repo": "BHTikTok",
        "asset_pattern": r"TikTok.*BHTikTok.*\.ipa$",
        "version_pattern": r"v?([\d.]+)",
    },
}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SOURCE_FILE = "ma1plus.json"
API_BASE = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def get_github_token():
    """Retrieve the GitHub token from the environment."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        HEADERS["Authorization"] = f"Bearer {token}"
        print("[auth] Using GITHUB_TOKEN for API requests.")
    else:
        print("[auth] WARNING: No GITHUB_TOKEN set. API rate limits may apply.")


def fetch_latest_release(owner: str, repo: str) -> dict | None:
    """Fetch the latest release from a GitHub repository."""
    url = f"{API_BASE}/repos/{owner}/{repo}/releases/latest"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            print(f"  [skip] No releases found for {owner}/{repo}")
            return None
        else:
            print(f"  [error] HTTP {resp.status_code} for {owner}/{repo}: {resp.text[:200]}")
            return None
    except requests.RequestException as e:
        print(f"  [error] Network error fetching {owner}/{repo}: {e}")
        return None


def find_ipa_asset(release: dict, asset_pattern: str) -> dict | None:
    """Find the IPA asset in a release matching the given pattern."""
    for asset in release.get("assets", []):
        if re.search(asset_pattern, asset["name"], re.IGNORECASE):
            return asset
    return None


def extract_version(tag_name: str, version_pattern: str) -> str | None:
    """Extract a clean version string from a release tag."""
    match = re.search(version_pattern, tag_name)
    return match.group(1) if match else tag_name.lstrip("v")


def format_changelog(release: dict) -> str:
    """Format the release body as a clean changelog string."""
    body = release.get("body", "")
    if not body:
        return "• Updated to the latest version."

    lines = body.strip().split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[-*]\s+", "• ", line)
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", line)
        if line:
            cleaned.append(line)

    result = "\n".join(cleaned[:15])
    return result if result else "• Updated to the latest version."


def update_source():
    """Main update logic — uses AltStore V2 schema with versions array."""
    get_github_token()

    if not os.path.exists(SOURCE_FILE):
        print(f"[fatal] {SOURCE_FILE} not found in current directory.")
        sys.exit(1)

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        source = json.load(f)

    apps = source.get("apps", [])
    updated_count = 0
    checked_count = 0

    print(f"\n{'=' * 60}")
    print(f"  MA1 PLUS — Automated Source Updater (V2 Schema)")
    print(f"  Checking {len(GITHUB_SOURCES)} GitHub-tracked apps...")
    print(f"{'=' * 60}\n")

    for app in apps:
        bundle_id = app.get("bundleIdentifier", "")
        if bundle_id not in GITHUB_SOURCES:
            continue

        config = GITHUB_SOURCES[bundle_id]
        owner = config["owner"]
        repo = config["repo"]
        checked_count += 1

        print(f"[check] {app['name']} ({owner}/{repo})")

        release = fetch_latest_release(owner, repo)
        if not release:
            continue

        ipa_asset = find_ipa_asset(release, config["asset_pattern"])
        if not ipa_asset:
            print(f"  [skip] No IPA asset matching '{config['asset_pattern']}' found.")
            continue

        new_version = extract_version(release["tag_name"], config["version_pattern"])

        # V2 Schema: version data is inside the versions array
        versions = app.get("versions", [])
        current_version = versions[0]["version"] if versions else ""

        if new_version == current_version and not os.environ.get("FORCE_UPDATE"):
            print(f"  [ok] Already at v{current_version} — no update needed.")
            continue

        published = release.get("published_at", "")
        if not published:
            published = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        new_version_entry = {
            "version": new_version,
            "date": published,
            "localizedDescription": format_changelog(release),
            "downloadURL": ipa_asset["browser_download_url"],
            "size": ipa_asset["size"],
            "minOSVersion": versions[0].get("minOSVersion", "15.0") if versions else "15.0",
        }

        # Replace the versions array with the new version as the latest
        app["versions"] = [new_version_entry]

        updated_count += 1
        print(f"  [updated] v{current_version} -> v{new_version}")
        print(f"            URL: {ipa_asset['browser_download_url'][:80]}...")
        print(f"            Size: {ipa_asset['size']:,} bytes")

    with open(SOURCE_FILE, "w", encoding="utf-8") as f:
        json.dump(source, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"  Summary: Checked {checked_count} apps, updated {updated_count}.")
    print(f"  Source file: {SOURCE_FILE}")
    print(f"{'=' * 60}\n")



if __name__ == "__main__":
    update_source()
