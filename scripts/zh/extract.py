"""Extract every translatable segment of the atlas pages into i18n/zh/.

Outputs
  i18n/zh/segments/<page>.json  span-level records for inject.py
  i18n/zh/tm.json               translation memory: sid -> {en, zh, ctx}; zh is null until translated
  i18n/zh/chunks/chunk-NN.json  untranslated entries packed for translators (~WORDS_PER_CHUNK words)

Usage
  NODE_PATH=<dir containing acorn> python3 scripts/zh/extract.py [--chunk-words N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))
import htmlseg  # noqa: E402
import islands  # noqa: E402

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "i18n" / "zh"
PAGES = {
    "index.html": "index.html", "about.html": "about.html", "method.html": "method.html",
    "resources.html": "resources.html", "404.html": "404.html",
    "api-docs.html": "scripts/api_assets/api-docs.html",
}
JS_PAGES = {"index.html", "method.html", "about.html", "resources.html"}
_PLACEHOLDER = re.compile(r"^__[A-Z_]+__$")
WORDS_PER_CHUNK = 2000

_WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]+")
_CSSISH = re.compile(
    r"(^|[\s,(])(#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|color-mix\(|translate[XY]?\(|rotate\(|scale\(|matrix\(|url\(|var\(--)"
    r"|\d+(px|em|rem|vh|vw|ms)\b|;\s*[a-z-]+\s*:|monospace|sans-serif|\bserif\b|^M\s?-?\d"
    r"|^(position|display|background|color|opacity|transform|width|height|left|top|right|bottom|margin|padding|border"
    r"|font|z-index|pointer-events|inset|grid-template[a-z-]*|animation|transition|cursor|filter|overflow|flex|gap"
    r"|align-items|justify-content|text-align|line-height|letter-spacing|stroke[a-z-]*|fill|max-width|min-width|visibility)\s*:"
)
_IDENTISH = re.compile(r"^[\w./#:-]+$|^[\w-]+=|^#version|void main\(")
_SELECTORISH = re.compile(r"^[.#][A-Za-z_-]|:(first|last|nth|not|hover|focus)\b|\s>\s|\[data-|,\s*[.#][A-Za-z]")
_FILEISH = re.compile(r"\.(json|py|md|yaml|yml|html|svg|jpe?g|png|js|csv|txt)\b|^https?://|^/api/|[?&][\w-]+=")
_ATTR_FRAG = re.compile(r"""[\w-]+\s*=\s*("[^"]*("|$)|'[^']*('|$))|/>|<[\w-]*|>""")
_NOISY_OWNER = re.compile(r"class|cls|href|src|url|^id$|attr|sel|^s$|^r$|^out$|^spark$", re.I)
_LABEL_OWNER = re.compile(r"SHORT|LBL|LABEL|NAMES?$|_TIP|DEFS?$|NOTES?$|TXT|_TEXT|WORDS?$|CAPTION|_TITLE|^ACTS$|^liftWord$|^NAME$|^heads$")
_TEXT_SINK = re.compile(r"^(textContent|innerHTML|innerText|title|label|txt|text)$")
_CSS_WORDS = {"left", "right", "center", "middle", "end", "start", "text", "link", "title", "circle", "defs", "none",
              "auto", "block", "inline", "hidden", "visible", "space-between", "1fr", "bold", "normal", "italic",
              "minor", "open", "turned", "big", "selected", "on", "off", "active", "lit", "dim"}
_KNOWN_KEYS = {
    "empirical_scope", "baselines_ablations", "theory", "method_design", "compute_cost", "clarity", "novelty",
    "related_work", "stats_metrics", "robustness_sensitivity", "reproducibility", "problem_framing",
    "novelty_standard", "claim_evidence_match", "fair_comparison", "statistical_identifiability", "confound_hypothesis",
    "design_justification", "robustness_norm", "cost_benefit", "construct_validity", "reproducibility_norm",
    "presentation_trust", "merit_recognition", "negative", "uncertain", "mixed", "conditional", "positive",
    "NORM", "BLOCK", "ANCHOR", "REACH", "DOUBT", "WEIGH", "articulate", "evidence", "method", "report", "none",
    "substantiate", "disclose",
}


def sid_for(text: str) -> str:
    return "s" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def strip_markup(text: str) -> str:
    """Remove ${...} placeholders and tags so only reader-facing words remain."""
    out, i, depth = [], 0, 0
    while i < len(text):
        if text.startswith("${", i):
            depth += 1
            i += 2
            continue
        if depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
            continue
        out.append(text[i])
        i += 1
    return re.sub(r"<[^>]*>", " ", "".join(out))


def js_literals(js: str) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
        tmp = f.name
    try:
        res = subprocess.run(["node", str(ROOT / "scripts/zh/js_literals.mjs"), tmp], check=True,
                             capture_output=True, text=True, env=os.environ)
    finally:
        os.unlink(tmp)
    return json.loads(res.stdout)


def js_translatable(lit: Dict[str, Any], blocked: Set[str]) -> bool:
    if lit["ctx"] != "value":
        return False
    value = lit["value"]
    owner = lit.get("owner") or ""
    if lit["value"] in blocked and not _LABEL_OWNER.search(owner):
        return False
    label_map = bool(_LABEL_OWNER.search(owner))
    if (_IDENTISH.search(value) and not label_map) or _SELECTORISH.search(value):
        return False
    plain = _ATTR_FRAG.sub(" ", strip_markup(value)).strip()
    if _FILEISH.search(plain) or _CSSISH.search(plain):
        return False
    words = [w for w in _WORD.findall(plain) if len(w) >= 2]
    if not words:
        return False
    if len(words) >= 2:
        return True
    if _NOISY_OWNER.search(owner):
        return False
    if plain.strip() != plain.strip().split()[0]:
        return True
    if lit["kind"] == "template" and lit["exprs"]:
        return True
    if plain.strip() in _CSS_WORDS:
        return False
    if value != value.strip():
        return True  # a concatenation fragment such as "Act " or "rated "
    return bool(_LABEL_OWNER.search(owner)) or bool(_TEXT_SINK.match(owner)) or (lit.get("key") in _KNOWN_KEYS)


def extract_page(page: str, tm: Dict[str, Dict[str, Any]], order: List[str]) -> Dict[str, Any]:
    src = (ROOT / PAGES[page]).read_text(encoding="utf-8")
    recs: List[Dict[str, Any]] = []
    blocked: Set[str] = set()

    def add(kind: str, start: int, end: int, text: str, ctx: str, **extra: Any) -> None:
        if not _WORD.search(strip_markup(text)) or _PLACEHOLDER.match(text.strip()):
            return
        sid = sid_for(text)
        if sid not in tm:
            tm[sid] = {"en": text, "zh": None, "ctx": ctx}
            order.append(sid)
        recs.append({"kind": kind, "start": start, "end": end, "sid": sid, "path": ctx, **extra})

    for seg in htmlseg.segments(src):
        tail = ">".join(seg.path.split(">")[-3:])
        add(seg.kind, seg.start, seg.end, src[seg.start:seg.end], f"{page} · {seg.kind} · {tail}")

    scripts = list(htmlseg.script_spans(src))
    js_regions = [(a, s, e) for a, s, e in scripts if (a.get("type") or "text/javascript") in ("text/javascript", "module")]
    lit_sets = []
    if page in JS_PAGES:
        for _attrs, s, e in js_regions:
            info = js_literals(src[s:e])
            lit_sets.append((s, e, info))
            blocked |= set(info["keys"])
            blocked |= {l["value"] for l in info["literals"] if l["ctx"] in ("compare", "case", "member", "setlike", "selector", "attrname", "key")}
        for s, e, info in lit_sets:
            for lit in info["literals"]:
                if not js_translatable(lit, blocked):
                    continue
                kind = "tpl" if lit["kind"] == "template" else "js"
                owner = lit.get("owner") or "-"
                add(kind, s + lit["start"], s + lit["end"], lit["value"], f"{page} · {kind} · {owner}",
                    region=[s, e], exprs=[[s + a, s + b] for a, b in lit["exprs"]])

    if page == "index.html":
        for attrs, s, e in scripts:
            if attrs.get("type") != "application/json":
                continue
            name = (attrs.get("id") or "").removeprefix("isl-")
            if name not in islands.SPEC:
                continue
            obj = json.loads(src[s:e])
            for path, value in islands.fields(name, obj):
                if value in blocked:
                    logger.info("island %s %s doubles as a JS key; left in English", name, path)
                    continue
                add("isl", s, e, value, f"{page} · island {name} · {'.'.join(map(str, path))}", island=name, jpath=list(path))
    # inject.py refuses to run against a page that is not the one these offsets were measured on
    digest = hashlib.sha256(src.encode("utf-8")).hexdigest()
    return {"page": page, "source_path": PAGES[page], "source_sha256": digest, "segments": recs}


def write_chunks(tm: Dict[str, Dict[str, Any]], order: List[str], chunk_words: int) -> int:
    chunks_dir = I18N / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    for old in chunks_dir.glob("chunk-*.json"):
        if not old.name.endswith(".zh.json"):
            old.unlink()
    pending = [sid for sid in order if tm[sid]["zh"] is None]
    chunk: Dict[str, Any] = {}
    n_words = 0
    n = 0
    for sid in pending:
        words = len(_WORD.findall(strip_markup(tm[sid]["en"])))
        if chunk and n_words + words > chunk_words:
            n += 1
            (chunks_dir / f"chunk-{n:02d}.json").write_text(json.dumps(chunk, ensure_ascii=False, indent=1), encoding="utf-8")
            chunk, n_words = {}, 0
        chunk[sid] = {"en": tm[sid]["en"], "ctx": tm[sid]["ctx"]}
        n_words += words
    if chunk:
        n += 1
        (chunks_dir / f"chunk-{n:02d}.json").write_text(json.dumps(chunk, ensure_ascii=False, indent=1), encoding="utf-8")
    return n


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk-words", type=int, default=WORDS_PER_CHUNK)
    ap.add_argument("--pages", nargs="*", default=list(PAGES), help="subset of pages to (re)extract")
    ap.add_argument("--no-chunks", action="store_true", help="update tm.json and segments only; leave chunk files alone")
    args = ap.parse_args()
    (I18N / "segments").mkdir(parents=True, exist_ok=True)
    tm_path = I18N / "tm.json"
    tm: Dict[str, Dict[str, Any]] = json.loads(tm_path.read_text(encoding="utf-8")) if tm_path.exists() else {}
    order: List[str] = list(tm)
    seen_before = set(order)
    for page in args.pages:
        rec = extract_page(page, tm, order)
        (I18N / "segments" / f"{page}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        logger.info("%s: %d segments", page, len(rec["segments"]))
    tm_path.write_text(json.dumps(tm, ensure_ascii=False, indent=1), encoding="utf-8")
    pending = [s for s in order if tm[s]["zh"] is None]
    words = sum(len(_WORD.findall(strip_markup(tm[s]["en"]))) for s in pending)
    n = 0 if args.no_chunks else write_chunks(tm, order, args.chunk_words)
    logger.info("tm: %d entries (%d new), %d untranslated (%d words) -> %d chunks",
                len(tm), len(order) - len(seen_before), len(pending), words, n)


if __name__ == "__main__":
    main()
