#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "beautifulsoup4",
#   "markdownify",
# ]
# ///

import requests
from bs4 import BeautifulSoup
import markdownify
from pathlib import Path

BASE = "https://teenage.engineering"

PAGES = [
    "/guides/ep-133/hardware-overview",
    "/guides/ep-133/power-on",
    "/guides/ep-133/screen",
    "/guides/ep-133/buttons-and-combos",
    "/guides/ep-133/guide-conventions",
    "/guides/ep-133/workflow",
    "/guides/ep-133/get-started",
    "/guides/ep-133/modes",
    "/guides/ep-133/play-and-record",
    "/guides/ep-133/functions",
    "/guides/ep-133/effects",
    "/guides/ep-133/how-to",
    "/guides/ep-133/system",
    "/guides/ep-133/erase-drive",
    "/guides/ep-133/tech-specs",
    "/guides/ep-133/credits",
    "/guides/ep-133/warnings-warranty-fcc",
    "/guides/ep-133/whats-new",
    "/guides/ep-133/software-licenses",
]

OUTPUT = (Path(__file__).parent / "../references/user-manual.md").resolve()

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

sections = []

for path in PAGES:
    url = BASE + path
    print(f"Fetching {url} ...")
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # TE guide pages wrap content in <article> or <main>; fall back to <body>
    content = soup.find("article") or soup.find("main") or soup.find("body")

    # Remove nav, footer, header noise
    for tag in content.find_all(["nav", "footer", "header", "script", "style"]):
        tag.decompose()

    md = markdownify.markdownify(str(content), heading_style="ATX", strip=["a"])
    md = md.strip()

    slug = path.rstrip("/").split("/")[-1]
    sections.append(f"# {slug}\n\n{md}\n")

OUTPUT.write_text("\n---\n\n".join(sections), encoding="utf-8")
print(f"\nWrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")
