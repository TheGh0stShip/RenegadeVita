"""Validate the historical video page without modifying its media evidence."""

import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src", "poster") and value:
                self.targets.append(value)


root = Path(__file__).resolve().parents[1]
page = (root / "index.html").read_text(encoding="utf-8")
parser = Links()
parser.feed(page)
assert "A3.5-dev204" in page
assert "Latest published build: A3.5-dev207" in page
assert "Latest development candidate: A3.5-dev204" not in page
assert "These later changes are not included in Dev207" in page
assert "108 numbered builds plus A3.1" in page
assert "HISTORICAL_SCREENSHOT_TIMELINE.md" in page
assert "Issue #1 remains open" in page
for build in (205, 206, 207):
    assert f"releases/tag/A3.5-dev{build}" in page
assert "Dev204 LiveArea in Vita3K" in page
assert "Historical Dev87" in page
assert "physical Vita acceptance remain open" in page
assert "Full Practice gameplay" in page
assert "no audio track" in page
assert 'https://hits.sh/thegh0stship.github.io/RenegadeVita.svg?label=visitors&amp;color=d4473c&amp;labelColor=38474a' in page
assert "Renegade Vita visitor count" in page
for target in parser.targets:
    url = urlsplit(target)
    if url.scheme:
        assert url.scheme == "https", target
        continue
    path = (root / url.path).resolve()
    assert path.is_relative_to(root) and path.is_file(), target
video = root / "RenegadeVita-A3.5-dev87-physical-M00.mp4"
assert video.stat().st_size == 44746182
assert hashlib.sha256(video.read_bytes()).hexdigest() == (
    "e6f10ac1add71090bfa83246f4829b668d2d7629f25e5c0f3dfd1eb09ea44aaf")
assert (root / "dev87-m00-poster.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
new_video = root / "dev202-practice-vita3k-silent.mp4"
assert hashlib.sha256(new_video.read_bytes()).hexdigest() == (
    "4e07cddc0d42911ad2f2cd5a81d05a32057e75c5c0938f5a54eb718286478899")
for name, digest in {
    "dev204-banner.png": "d00735971158b95138a5d698cf92bb5290a5aff1361e2634c7e1267035af1ddc",
    "dev204-icon.png": "e47a1c2a6cfe0bbbf8473363f1ecb419ebf19e9a2f38e95fd8c78a4a744e8d27",
    "dev204-livearea.png": "001e27fea0d44693ecee0c2b0139b4b176e8a36daabb02972a1c1c8f3838c10e",
    "dev202-main-menu.png": "58823a89f870d01565b3ba8a54ebde1ef7d50c073a7f881858802c9e8b4a8b6d",
    "dev202-practice-loading.png": "61f2f098cc755545e307e87b16d68878e2af096a2b7e9a5cc37f4b1e51f63b25",
    "dev202-practice-gameplay.png": "041a76808d9fe611b7176d660a718f3541e4212b84f77791537128eb0e04e9f2",
}.items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
print("PASS: Dev207 publication status, timeline links, evidence caveats, and unchanged historical media hashes")
