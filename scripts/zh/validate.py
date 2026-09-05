"""Check translated chunks against their English sources and merge the good ones.

  python3 scripts/zh/validate.py                # check every i18n/zh/chunks/chunk-NN.zh.json
  python3 scripts/zh/validate.py chunk-03       # check one chunk
  python3 scripts/zh/validate.py --merge        # check all, write passing entries into tm.json

Hard failures (the entry is not merged): missing or empty value, changed tag
sequence, changed `${...}` placeholders, changed <code> contents. Soft warnings
are printed but merged: entity or number multiset changed, no CJK in the output.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "i18n" / "zh"
CHUNKS = I18N / "chunks"

_TAG = re.compile(r"<[^>]+>")
_TEXT_ATTR = re.compile(r'((?:title|aria-label|alt|placeholder|aria-description|data-tip|data-label|data-caption|data-title|label)=")[^"]*(")')
_CODE = re.compile(r"<(code|kbd|var|samp)\b[^>]*>(.*?)</\1>", re.S)
_ENTITY = re.compile(r"&[#\w]+;")
_NUMBER = re.compile(r"\d[\d,.]*")
_CJK = re.compile(r"[㐀-鿿　-〿＀-￯]")
_WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]+")


def placeholders(text: str) -> List[str]:
    """Return the `${...}` expressions of a template in order (brace-depth aware)."""
    out, i = [], 0
    while i < len(text):
        if text.startswith("${", i):
            depth, j = 1, i + 2
            while j < len(text) and depth:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                j += 1
            out.append(text[i:j])
            i = j
        else:
            i += 1
    return out


def norm_tags(text: str) -> List[str]:
    return [_TEXT_ATTR.sub(r"\1\2", t) for t in _TAG.findall(text)]


def check(en: str, zh: Any) -> Tuple[List[str], List[str]]:
    """Return (hard_failures, warnings) for one translation."""
    hard: List[str] = []
    soft: List[str] = []
    if not isinstance(zh, str) or not zh.strip():
        return ["empty or non-string"], soft
    if norm_tags(en) != norm_tags(zh):
        hard.append("tag sequence changed")
    if placeholders(en) != placeholders(zh):
        hard.append("placeholders changed")
    if sorted(m.group(2) for m in _CODE.finditer(en)) != sorted(m.group(2) for m in _CODE.finditer(zh)):
        hard.append("<code> contents changed")
    if sorted(_ENTITY.findall(en)) != sorted(_ENTITY.findall(zh)):
        soft.append("entities changed")
    if sorted(_NUMBER.findall(en)) != sorted(_NUMBER.findall(zh)):
        soft.append("numbers changed")
    words = [w for w in _WORD.findall(_TAG.sub(" ", en)) if len(w) >= 2]
    if len(words) >= 2 and not _CJK.search(zh):
        soft.append("no CJK in output")
    if zh.strip() == en.strip() and len(words) >= 2:
        soft.append("identical to source")
    return hard, soft


def load_chunk(name: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    src = json.loads((CHUNKS / f"{name}.json").read_text(encoding="utf-8"))
    zh_path = CHUNKS / f"{name}.zh.json"
    if not zh_path.exists():
        raise FileNotFoundError(zh_path)
    return src, json.loads(zh_path.read_text(encoding="utf-8"))


def validate_chunk(name: str, verbose: bool = True) -> Tuple[Dict[str, str], List[str]]:
    """Return (accepted sid->zh, failure lines) for one chunk."""
    src, zh = load_chunk(name)
    accepted: Dict[str, str] = {}
    failures: List[str] = []
    n_soft = 0
    for sid, rec in src.items():
        hard, soft = check(rec["en"], zh.get(sid))
        if hard:
            failures.append(f"{name} {sid}: {'; '.join(hard)}\n    EN: {rec['en'][:160]!r}\n    ZH: {str(zh.get(sid))[:160]!r}")
            continue
        if soft:
            n_soft += 1
            if verbose:
                logger.info("warn %s %s: %s | %r -> %r", name, sid, "; ".join(soft), rec["en"][:80], zh[sid][:80])
        accepted[sid] = zh[sid]
    extra = set(zh) - set(src)
    if extra:
        logger.info("%s: %d unknown sids ignored", name, len(extra))
    logger.info("%s: %d ok, %d failed, %d warnings", name, len(accepted), len(failures), n_soft)
    return accepted, failures


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("chunks", nargs="*")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    names = args.chunks or sorted(p.name[:-8] for p in CHUNKS.glob("chunk-*.zh.json"))
    all_ok: Dict[str, str] = {}
    all_fail: List[str] = []
    for name in names:
        ok, fail = validate_chunk(name, verbose=not args.quiet)
        all_ok.update(ok)
        all_fail.extend(fail)
    for line in all_fail:
        logger.error("FAIL %s", line)
    if args.merge:
        tm_path = I18N / "tm.json"
        tm = json.loads(tm_path.read_text(encoding="utf-8"))
        for sid, zh in all_ok.items():
            if sid in tm:
                tm[sid]["zh"] = zh
        tm_path.write_text(json.dumps(tm, ensure_ascii=False, indent=1), encoding="utf-8")
        pending = sum(1 for v in tm.values() if v["zh"] is None)
        logger.info("merged %d translations; %d still pending", len(all_ok), pending)
    sys.exit(1 if all_fail else 0)


if __name__ == "__main__":
    main()
