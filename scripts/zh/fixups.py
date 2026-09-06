"""Post-translation patches for JS that reads English data values as display text.

A few places in index.html's main script show a data-island string directly
(fate bands, deliberation scenarios) or test a translated island label against
an English literal (the repair-manual "extend" binding, the "(imported)" suffix
on law names). Translating the islands alone would leave those spots English or
silently break the test, so inject.py applies these patches after the rebuild.
Everything here is derived from tm.json where it can be, so a retranslation
keeps the patches in step.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# island values the JS prints verbatim (data keys stay English; the display is mapped)
ZH_DISPLAY = {
    "held (no visible change)": "维持（无可见变化）",
    "clarified only": "仅澄清",
    "unreadable (no fate read)": "无法判读（未读出命运）",
    "softened or reversed": "软化或反转",
    "hardened": "加强",
    "held": "维持",
    "clarified": "澄清",
    "unreadable": "无法判读",
    "a softening": "软化",
    "an entrenchment": "固守",
    "a reversal": "反转",
    "a split verdict": "分歧裁决",
    "unanimity": "一致",
    "Accept (Poster)": "Accept (Poster)",
    "softening": "软化", "entrenchment": "固守", "reversal": "反转", "split verdict": "分歧裁决",
    "contested": "争议", "silence": "沉默", "procedural": "程序性", "hedged": "有保留",
}
# literals the JS both shows and compares against; nothing in the islands carries them
LITERALS = {"nothing asked": "无所要求", "all meta units": "全部元评审单元"}
ZH_VALENCE = {"negative": "否定", "uncertain": "存疑", "mixed": "混合", "conditional": "有条件", "positive": "肯定"}
ZH_ACT = {"I": "第一幕", "II": "第二幕", "III": "第三幕", "IV": "第四幕", "V": "第五幕", "VI": "第六幕",
          "VII": "第七幕", "VIII": "第八幕", "CODA": "尾声"}


def _zh_for(tm: Dict[str, Dict[str, Any]], segs: List[Dict[str, Any]], island: str, jpath_prefix: tuple) -> List[str]:
    out = []
    for s in segs:
        if s["kind"] == "isl" and s["island"] == island and tuple(s["jpath"][:len(jpath_prefix)]) == jpath_prefix:
            zh = tm[s["sid"]]["zh"]
            if zh:
                out.append((tm[s["sid"]]["en"], zh))
    return out


def apply(page_html: str, tm: Dict[str, Dict[str, Any]], segs: List[Dict[str, Any]]) -> str:
    """Patch index.html after translation; returns the page unchanged if nothing applies."""
    s = page_html
    anchor = 'const GALAXY = __ISL("GALAXY_LITE");'
    if anchor in s and "const __ZH" not in s:
        s = s.replace(anchor, anchor + "\nconst __ZH = " + json.dumps(ZH_DISPLAY, ensure_ascii=False) + ";"
                      + "\nconst __ZH_ACT = " + json.dumps(ZH_ACT, ensure_ascii=False) + ";", 1)
        # valence keys are printed as-is in chips, tooltips and the lexicon
        s = s.replace("\nconst __ZH_ACT = ", "\nconst __ZHV = " + json.dumps(ZH_VALENCE, ensure_ascii=False) + ";\nconst __ZH_ACT = ", 1)
        for old, new in (("${v} ${pct(", "${__ZHV[v] || v} ${pct("),
                         ("→ ${v}</div>", "→ ${__ZHV[v] || v}</div>"),
                         ("${v}  ${(100 * valTot[v]", "${__ZHV[v] || v}  ${(100 * valTot[v]"),
                         ("VAL_ORDER.map(v => [v, VAL_DEFS[v]", "VAL_ORDER.map(v => [__ZHV[v] || v, VAL_DEFS[v]")):
            s = s.replace(old, new)
        # specimen cards, filter bars, population rows and legends print raw keys
        s = s.replace(">${u.valence}</span>", ">${__ZHV[u.valence] || u.valence}</span>", 1)
        s = s.replace('<span class="fb-l">${shortOf(k)}</span>', '<span class="fb-l">${dim === "v" ? (__ZHV[k] || k) : shortOf(k)}</span>', 1)
        s = s.replace('const full = dim === "v" ? k :', 'const full = dim === "v" ? (__ZHV[k] || k) :', 1)
        s = s.replace('${key === "split" ? "split verdict" : key}', '${__ZH[key === "split" ? "split verdict" : key] || key}', 1)
        i = s.find('["hedged", hedV')
        if i > 0:
            head, region, tail = s[:i], s[i:i + 3000], s[i + 3000:]
            region = re.sub(r"\$\{name\}(?=[ ，,])", "${__ZH[name] || __ZHV[name] || name}", region)
            s = head + region + tail
        s = re.sub(r'("[^"]{1,20}", )"random"(, (?:true|false))', r'\1"随机"\2', s)
        s = re.sub(r'\["(softening|contested|entrenchment|procedural)", ("[^"]+"), "[A-Z]+"\]',
                   lambda m: '["%s", %s, "%s"]' % (m.group(1), m.group(2), ZH_DISPLAY[m.group(1)]), s)
        for en, zh in LITERALS.items():
            s = s.replace(json.dumps(en), json.dumps(zh, ensure_ascii=False))
        # deliberation case-file group headers are built from the scenario key
        s = s.replace('${scen.replace(/^an? /, "").toUpperCase()}', '${(__ZH[scen] || scen.replace(/^an? /, "")).toUpperCase()}', 1)
        # "Act " + no  ->  第N幕 ; the "Act " literal itself was translated to "幕 " by inject
        s, n = re.subn(r'\((\w+)\.no === "CODA" \? "(?:Coda|CODA)" : "幕 " \+ \1\.no\)', r'(__ZH_ACT[\1.no] || "幕 " + \1.no)', s)
        logger.info("fixup: %d act-number expressions now use Chinese act names", n)
        s = s.replace("(FATE_SHORT[b.label] || b.label) : b.label}", "(FATE_SHORT[b.label] || b.label) : (__ZH[b.label] || b.label)}", 1)
        s = s.replace("${F.scenario.toUpperCase()}", "${(__ZH[F.scenario] || F.scenario).toUpperCase()}", 1)

    # repair-manual binding: startsWith(<English group name prefix>)
    for en, zh in _zh_for(tm, segs, "REPAIR", ("groups", 0, "name")):
        if en.startswith("Extend the evidence"):
            prefix = zh.split(" — ")[0].split("—")[0].strip()
            s = s.replace('startsWith("Extend the evidence")', "startsWith(" + json.dumps(prefix, ensure_ascii=False) + ")", 1)
            logger.info("fixup: repair 'extend' binding now matches %r", prefix)

    # combination plate: exception/referent classes are recognised by regexes over the English
    # name; the island keeps the original beside the translation as name_en
    n = s.count(".test(a.name)")
    s = s.replace(".test(a.name)", ".test(a.name_en || a.name)")
    logger.info("fixup: %d name regex tests now read the English original", n)
    # nav: overture/interlude rows are styled by their (now translated) label
    s = s.replace("/^Overture|^Interlude/i.test(it.label)", "/^Overture|^Interlude|^序曲|^间奏/i.test(it.label)", 1)

    # mirage plate: the measured/null row is told apart by its label prefix
    for sid, rec in tm.items():
        if rec["en"].startswith("MEASURED") and rec["zh"]:
            prefix = rec["zh"].split(" — ")[0].split("—")[0].strip()
            s = s.replace('label.startsWith("MEASURED")', "label.startsWith(" + json.dumps(prefix, ensure_ascii=False) + ")", 1)
            logger.info("fixup: mirage 'measured' row now matches %r", prefix)
            break

    # console bar: strips the "Corpus: " prefix off the plate-scope line
    prefixes = set()
    for rec in tm.values():
        if rec["en"].startswith("Corpus: ") and rec["zh"]:
            m = re.match(r"^[^:：]{1,8}[:：]\s*", rec["zh"])
            if m:
                prefixes.add(m.group(0))
    if len(prefixes) == 1:
        pre = next(iter(prefixes))
        s = s.replace('.replace("Corpus: ", "")', '.replace("Corpus: ", "").replace(' + json.dumps(pre, ensure_ascii=False) + ', "")', 1)
        logger.info("fixup: console bar also strips %r", pre)
    elif prefixes:
        logger.warning("fixup: inconsistent 'Corpus:' prefixes in translations: %s", sorted(prefixes))

    # law names: the " (imported)" suffix the JS strips or marks
    suffixes = set()
    for en, zh in _zh_for(tm, segs, "ELEMS", ()):
        if en.endswith(" (imported)"):
            m = re.search(r"[（(][^（）()]+[)）]\s*$", zh)
            if m:
                suffixes.add(m.group(0))
    if len(suffixes) == 1:
        suf = next(iter(suffixes))
        n = s.count('.replace(" (imported)", ')
        s = s.replace('.replace(" (imported)", ', ".replace(" + json.dumps(suf, ensure_ascii=False) + ", ")
        logger.info("fixup: %d '(imported)' replaces now target %r", n, suf)
    elif suffixes:
        logger.warning("fixup: inconsistent '(imported)' suffixes in translations: %s", sorted(suffixes))
    return s
