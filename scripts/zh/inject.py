"""Rebuild the atlas pages with the translations held in i18n/zh/tm.json.

  python3 scripts/zh/inject.py --out DIR [--no-tweaks] [--marker TEXT] [pages...]

For each page the English segments recorded by extract.py are replaced by
their translations: HTML spans directly, JS string/template literals through a
nesting-aware rebuild of every <script> region, island fields by re-serialising
the JSON. Segments without a translation keep their English. With --tweaks
(default) the page is then adapted for Chinese readers: lang="zh-CN", a
China-reachable font mirror, CJK fallbacks in the font stacks.

--marker wraps every "translation" as <en><marker> instead of using tm.json —
a pipeline test that exercises every span without needing translations.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixups  # noqa: E402
import htmlseg  # noqa: E402
import islands  # noqa: E402
from validate import placeholders  # noqa: E402

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "i18n" / "zh"
PAGES = {
    "index.html": "index.html", "about.html": "about.html", "method.html": "method.html",
    "resources.html": "resources.html", "404.html": "404.html",
    "api-docs.html": "scripts/api_assets/api-docs.html",
}
ATTRIBUTION = (
    '<div class="col-fine col-zh">本站是 Shiro Takagi 所作 <a href="https://atlas-of-judgment.pages.dev">Atlas of Judgment</a>'
    ' 的中文译本。原文、图与派生数据 CC BY 4.0，代码 MIT；数据与机读接口与原站同源、未作改动。'
    '译文由 <a href="https://github.com/Lauorie/atlas-of-judgment">Lauorie/atlas-of-judgment</a> 维护，'
    '译文问题请到该仓库提 issue；数据与断言的更正请报到<a href="https://github.com/t46/atlas-of-judgment/issues">原仓库</a>。</div>\n'
)

FONT_MIRROR = ("https://fonts.googleapis.com", "https://fonts.loli.net")
GSTATIC_MIRROR = ("https://fonts.gstatic.com", "https://gstatic.loli.net")
CJK_SERIF = '"Noto Serif SC", "Songti SC", "STSong", "Source Han Serif SC", "Noto Serif CJK SC", "SimSun"'
CJK_SANS = '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC"'
FONT_STACKS = [
    ('"Cormorant Garamond", Georgia, serif', f'"Cormorant Garamond", {CJK_SERIF}, Georgia, serif'),
    ('"Source Serif 4", Georgia, serif', f'"Source Serif 4", {CJK_SERIF}, Georgia, serif'),
    ('"IBM Plex Mono", ui-monospace, monospace', f'"IBM Plex Mono", ui-monospace, {CJK_SANS}, monospace'),
    ('"IBM Plex Mono",ui-monospace,monospace', f'"IBM Plex Mono", ui-monospace, {CJK_SANS}, monospace'),
]
CJK_FAMILY_PARAM = "&family=Noto+Serif+SC:wght@400;600"


_PIECE = re.compile(r"(<[^>]+>|\$\{(?:[^{}]|\{[^{}]*\})*\})")


def mark(text: str, marker: str) -> str:
    """Append `marker` to every text piece outside tags and placeholders (pipeline test mode)."""
    out = []
    for piece in _PIECE.split(text):
        if piece and not _PIECE.fullmatch(piece) and re.search(r"[A-Za-z]{2,}", piece):
            piece = re.sub(r"(\S)(\s*)$", lambda m: m.group(1) + marker + m.group(2), piece, count=1)
        out.append(piece)
    return "".join(out)


def js_string(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def tpl_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


class Rebuilder:
    """Apply nested JS-literal translations inside one <script> region."""

    def __init__(self, js: str, base: int, segs: List[Dict[str, Any]], zh_of: Dict[str, Optional[str]]) -> None:
        self.js, self.base = js, base
        self.segs = sorted(segs, key=lambda s: (s["start"], -s["end"]))
        self.zh_of = zh_of

    def build(self, lo: int, hi: int) -> str:
        out: List[str] = []
        pos = lo
        for s in self.segs:
            if s["start"] < pos or s["end"] > hi or (s["start"], s["end"]) == (lo, hi):
                continue
            out.append(self.js[pos - self.base:s["start"] - self.base])
            out.append(self.render(s))
            pos = s["end"]
        out.append(self.js[pos - self.base:hi - self.base])
        return "".join(out)

    def render(self, s: Dict[str, Any]) -> str:
        zh = self.zh_of.get(s["sid"])
        if s["kind"] == "js":
            return js_string(zh) if zh is not None else self.js[s["start"] - self.base:s["end"] - self.base]
        if zh is None:
            return self.build(s["start"], s["end"])
        parts = placeholders(zh)
        if len(parts) != len(s["exprs"]):
            raise ValueError(f"placeholder count mismatch for {s['sid']}")
        text = zh
        pieces: List[str] = []
        for ph, (a, b) in zip(parts, s["exprs"]):
            i = text.index(ph)
            pieces.append(tpl_escape(text[:i]))
            pieces.append("${" + self.build(a, b) + "}")
            text = text[i + len(ph):]
        pieces.append(tpl_escape(text))
        return "`" + "".join(pieces) + "`"


def rebuild_page(page: str, tm: Dict[str, Dict[str, Any]], marker: Optional[str]) -> Tuple[str, int, int]:
    src = (ROOT / PAGES[page]).read_text(encoding="utf-8")
    rec = json.loads((I18N / "segments" / f"{page}.json").read_text(encoding="utf-8"))
    segs = rec["segments"]
    want = rec.get("source_sha256")
    if want and hashlib.sha256(src.encode("utf-8")).hexdigest() != want:
        raise SystemExit(f"{page}: source differs from the page the segments were extracted from "
                         "(already injected, or upstream changed) — re-run extract.py on the English source first")

    def zh(sid: str) -> Optional[str]:
        if marker is not None:
            return mark(tm[sid]["en"], marker)
        return tm[sid]["zh"]

    zh_of = {s["sid"]: zh(s["sid"]) for s in segs}
    done = sum(1 for s in segs if zh_of[s["sid"]] is not None)
    repl: List[Tuple[int, int, str]] = []

    for s in segs:
        if s["kind"] in ("block", "run", "attr"):
            t = zh_of[s["sid"]]
            if t is None:
                continue
            if s["kind"] == "attr":
                t = t.replace('"', "&quot;")
            repl.append((s["start"], s["end"], t))

    regions: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for s in segs:
        if s["kind"] in ("js", "tpl"):
            regions.setdefault(tuple(s["region"]), []).append(s)
    for (a, b), rsegs in regions.items():
        rb = Rebuilder(src[a:b], a, rsegs, zh_of)
        repl.append((a, b, rb.build(a, b)))

    isl: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for s in segs:
        if s["kind"] == "isl":
            isl.setdefault((s["start"], s["end"]), []).append(s)
    for (a, b), isegs in isl.items():
        if all(zh_of[s["sid"]] is None for s in isegs):
            continue
        obj = json.loads(src[a:b])
        for s in isegs:
            t = zh_of[s["sid"]]
            if t is not None:
                path = tuple(s["jpath"])
                if isinstance(path[-1], str):
                    # keep the English original beside the translation: some JS keys off it
                    islands.set_path(obj, path[:-1] + (path[-1] + "_en",), tm[s["sid"]]["en"])
                islands.set_path(obj, path, t)
        repl.append((a, b, json.dumps(obj, ensure_ascii=False, separators=(",", ":"))))

    repl.sort(key=lambda r: r[0])
    for x, y in zip(repl, repl[1:]):
        if y[0] < x[1]:
            raise ValueError(f"overlapping replacements in {page}: {x[:2]} / {y[:2]}")
    out: List[str] = []
    pos = 0
    for a, b, t in repl:
        out.append(src[pos:a])
        out.append(t)
        pos = b
    out.append(src[pos:])
    return "".join(out), done, len(segs)


def tweak(page_html: str) -> str:
    """Adapt a rebuilt page for Chinese readers."""
    s = page_html.replace('<html lang="en">', '<html lang="zh-CN">', 1)
    if "<meta charset" not in s:
        s = s.replace('<html lang="zh-CN">', '<html lang="zh-CN">\n<meta charset="utf-8">', 1)
    s = s.replace(FONT_MIRROR[0], FONT_MIRROR[1]).replace(GSTATIC_MIRROR[0], GSTATIC_MIRROR[1])
    s = s.replace("&display=swap", CJK_FAMILY_PARAM + "&display=swap")
    for old, new in FONT_STACKS:
        s = s.replace(old, new)
    if "</footer>" in s and "col-zh" not in s:
        s = s.replace("</footer>", ATTRIBUTION + "</footer>", 1)
    return s


def check_scripts(page_html: str) -> None:
    """Fail loudly if any inline script no longer parses."""
    for attrs, a, b in htmlseg.script_spans(page_html):
        if (attrs.get("type") or "text/javascript") not in ("text/javascript", "module"):
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(page_html[a:b])
            tmp = f.name
        try:
            res = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        finally:
            os.unlink(tmp)
        if res.returncode:
            raise SystemExit(f"script no longer parses:\n{res.stderr[:2000]}")
    for attrs, a, b in htmlseg.script_spans(page_html):
        if attrs.get("type") == "application/json":
            json.loads(page_html[a:b])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-tweaks", action="store_true")
    ap.add_argument("--marker")
    ap.add_argument("pages", nargs="*", default=list(PAGES))
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    tm = json.loads((I18N / "tm.json").read_text(encoding="utf-8"))
    for page in args.pages:
        built, done, total = rebuild_page(page, tm, args.marker)
        if page == "index.html" and args.marker is None:
            segs = json.loads((I18N / "segments" / f"{page}.json").read_text(encoding="utf-8"))["segments"]
            built = fixups.apply(built, tm, segs)
        if not args.no_tweaks:
            built = tweak(built)
        check_scripts(built)
        target = out_dir / PAGES[page]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(built, encoding="utf-8")
        logger.info("%s: %d/%d segments translated -> %s", page, done, total, target)


if __name__ == "__main__":
    main()
