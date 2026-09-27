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
assert "A3.5-dev201" in page
assert "Historical Dev87" in page
assert "physical Vita acceptance remain unverified" in page
assert "Glacier texture and player-name appearance still need visual confirmation" in page
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
print("PASS: page links, current-status caveats, poster and immutable recording hash")
