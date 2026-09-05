"""Build the deployable site from this repository into one directory.

  python3 scripts/build_site.py --out .pages-dist [--base /atlas-of-judgment/] [--site https://lauorie.github.io]

Stages the five pages and their assets, rewrites root-absolute links for a
sub-path deployment (GitHub Pages project sites live under /<repo>/), and
builds the machine-reader layer — /api/v1/*, /llms.txt, /openapi.yaml, /api/ —
from data/, depositions/ and scripts/api_assets/. Replaces the author's
deploy_pages.py, which depended on paths that only existed on their machine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEPOSITIONS = ROOT / "depositions"
API_ASSETS = ROOT / "scripts" / "api_assets"
PAGES = ["index.html", "about.html", "method.html", "resources.html", "404.html"]
ASSETS = ["favicon.svg", "card.jpg"]
UPSTREAM_SITE = "https://atlas-of-judgment.pages.dev"
UPSTREAM_REPO = "t46/atlas-of-judgment"
MIRROR_REPO = "Lauorie/atlas-of-judgment"

# plate catalogue: id, number, title (zh), act (zh), islands read by the plate
PLATES = [
    ("plate-i", "I", "解剖", "第一幕 · 仪器", ["viz-data.json", "panel-data.json", "construct-data.json"]),
    ("plate-ii", "II", "语法", "第一幕 · 仪器", ["viz-data.json", "ninegrammar-data.json"]),
    ("plate-iii", "III", "修辞", "第一幕 · 仪器", ["rhetoric-v2.json"]),
    ("plate-iv", "IV", "句法", "第二幕 · 一人之手", ["chain-data.json"]),
    ("plate-v", "V", "行程", "第二幕 · 一人之手", ["structure-data.json", "itinerary-data.json"]),
    ("plate-vi", "VI", "早判", "第二幕 · 一人之手", ["commit-data.json", "score-data.json"]),
    ("plate-vii", "VII", "要件", "第三幕 · 法则", ["elements-all.json", "argument-raw-novelty.json"]),
    ("plate-viii", "VIII", "组合条款", "第三幕 · 法则", ["combination-data.json"]),
    ("plate-ix", "IX", "无名判例", "第三幕 · 法则", ["canon-data.json"]),
    ("plate-x", "X", "套语集", "第三幕 · 法则", ["boilerplate-data.json", "jurisprudence-data.json"]),
    ("plate-xi", "XI", "修复手册", "第三幕 · 法则", ["repair-manual.json", "repair-k-robustness.json"]),
    ("plate-xii", "XII", "裁决", "第三幕 · 法则", ["viz-data.json"]),
    ("plate-xiii", "XIII", "控罪单", "第三幕 · 法则", ["chargesheet-data.json"]),
    ("plate-xiv", "XIV", "代价", "第四幕 · 量刑表", ["lawtariff-data.json", "jurisprudence-data.json"]),
    ("plate-xv", "XV", "后果", "第四幕 · 量刑表", ["tribunal-ci.json", "panel-data.json", "decision-data.json"]),
    ("plate-xvi", "XVI", "对话的形状", "第五幕 · 交锋", ["threads-data.json"]),
    ("plate-xvii", "XVII", "Rebuttal", "第五幕 · 交锋", ["yield-data.json", "panel-data.json"]),
    ("plate-xviii", "XVIII", "招式", "第五幕 · 交锋", ["moves-data.json"]),
    ("plate-xix", "XIX", "一条异议的命运", "第五幕 · 交锋", ["lifecycle-data.json", "interrogative-data.json"]),
    ("plate-xx", "XX", "评审组", "第五幕 · 交锋", ["overrule-data.json", "panel-data.json", "searchparty-data.json"]),
    ("plate-xxi", "XXI", "合议", "第五幕 · 交锋", ["deliberation-data.json", "repertoire-data.json", "overrule-data.json"]),
    ("plate-xxii", "XXII", "上级法庭", "第六幕 · 上级法庭", ["court-data.json"]),
    ("plate-xxiii", "XXIII", "借来的裁决", "第六幕 · 上级法庭", ["acecho-data.json"]),
    ("plate-xxiv", "XXIV", "阶梯", "第七幕 · 尺度", ["score-depth.json", "score-data.json"]),
    ("plate-xxv", "XXV", "度量", "第七幕 · 尺度", ["lottery-data.json", "counterfactual-data.json"]),
    ("plate-xxvi", "XXVI", "漂移", "第八幕 · 时代与疆域", ["drift-data.json", "currents-data.json", "minds-data.json", "rhetoric-v2.json"]),
    ("plate-xxvii", "XXVII", "未修订的法典", "第八幕 · 时代与疆域", ["drift-data.json", "timeless-data.json"]),
    ("plate-xxviii", "XXVIII", "神谕", "第八幕 · 时代与疆域", ["oracle-data.json", "archipelago-data.json"]),
    ("plate-xxix", "XXIX", "水印", "第八幕 · 时代与疆域", ["llmtrace-data.json"]),
    ("plate-xxx", "XXX", "标本", "尾声 · 档案", ["viz-data.json"]),
    ("appendix-i", "附录 I", "词汇表", "附录", []),
    ("appendix-ii", "附录 II", "溯源与方法", "附录", ["viz-data.json", "structure-data.json", "galaxy.json", "panel-data.json"]),
    ("appendix-iii", "附录 III", "零假设陈列柜", "附录", ["mirage-data.json", "field-stats.json"]),
]

OG = {
    "api": ("机读接口 — 评判图谱",
            "与图版同源的静态 JSON 接口：每张图版的存证、数据岛、更正记录、llms.txt。"),
}


def head(site: str, base: str, path: str, title: str, desc: str) -> str:
    url = f"{site}{base}{path}"
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN">\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg">\n'
        f'<meta name="description" content="{desc}">\n'
        '<meta property="og:type" content="website">\n'
        '<meta property="og:site_name" content="评判图谱 · Atlas of Judgment">\n'
        f'<meta property="og:title" content="{title}">\n'
        f'<meta property="og:description" content="{desc}">\n'
        f'<meta property="og:url" content="{url}">\n'
        f'<meta property="og:image" content="{site}{base}card.jpg">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
    )


def rebase(text: str, base: str, site: str) -> str:
    """Point root-absolute references at the deployment base path."""
    if base != "/":
        text = re.sub(r'((?:href|src|action)=")/(?!/)', rf"\1{base}", text)
        text = re.sub(r'(["\'(\s>])/(api/|llms\.txt|openapi\.yaml|sitemap\.xml)', rf"\1{base}\2", text)
    text = text.replace(f'content="{UPSTREAM_SITE}/', f'content="{site}{base}')
    text = text.replace(f'content="{UPSTREAM_SITE}"', f'content="{site}{base.rstrip("/")}"')
    return text


def stage_pages(dist: Path, base: str, site: str) -> None:
    for page in PAGES:
        text = (ROOT / page).read_text(encoding="utf-8")
        (dist / page).write_text(rebase(text, base, site), encoding="utf-8")
    for asset in ASSETS:
        shutil.copy(ROOT / asset, dist / asset)
    (dist / ".nojekyll").write_text("")
    today = date.today().isoformat()
    urls = [("", "1.0"), ("about", "0.8"), ("method", "0.8"), ("resources", "0.6"), ("api/", "0.6")]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, prio in urls:
        sitemap.append(f"  <url><loc>{site}{base}{path}</loc><lastmod>{today}</lastmod>"
                       f"<changefreq>monthly</changefreq><priority>{prio}</priority></url>")
    sitemap.append("</urlset>")
    (dist / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    robots = re.sub(r"Sitemap: .*", f"Sitemap: {site}{base}sitemap.xml", robots)
    if base != "/":
        robots = robots.replace("#   /", f"#   {base}")
    (dist / "robots.txt").write_text(robots, encoding="utf-8")


def deposition_islands() -> Dict[str, set]:
    out: Dict[str, set] = {}
    for f in sorted(DEPOSITIONS.glob("*.json")):
        dep = json.loads(f.read_text(encoding="utf-8"))
        names = {c["source_island"] for fig in dep.get("figures", []) for c in fig.get("claims", []) if c.get("source_island")}
        names |= {Path(d).name for d in dep.get("links", {}).get("data", [])}
        out[f.stem] = names
    return out


def build_api(dist: Path, base: str, site: str) -> None:
    api = dist / "api" / "v1"
    (api / "data").mkdir(parents=True, exist_ok=True)
    (api / "plates").mkdir(parents=True, exist_ok=True)
    corpus = json.loads((API_ASSETS / "corpus.json").read_text(encoding="utf-8"))
    dep_islands = deposition_islands()
    cited = set().union(*dep_islands.values()) if dep_islands else set()

    islands: List[Dict[str, Any]] = []
    for src in sorted(DATA.glob("*.json")):
        shutil.copy(src, api / "data" / src.name)
        used_by = sorted({p[0] for p in PLATES if src.name in p[4]} | {pid for pid, names in dep_islands.items() if src.name in names})
        islands.append({
            "file": src.name, "bytes": src.stat().st_size,
            "sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
            "plates": used_by, "status": "active" if used_by else "orphaned",
        })
    missing = cited - {i["file"] for i in islands}
    if missing:
        raise SystemExit(f"depositions cite islands absent from data/: {sorted(missing)}")

    json.loads((API_ASSETS / "corrections.json").read_text(encoding="utf-8"))
    shutil.copy(API_ASSETS / "corrections.json", api / "corrections.json")

    dep_ids = []
    for f in sorted(DEPOSITIONS.glob("*.json")):
        shutil.copy(f, api / "plates" / f.name)
        dep_ids.append(f.stem)

    index = {
        "name": "评判图谱 · Atlas of Judgment — 机读接口（中文镜像）",
        "version": "1.0.0-zh",
        "generated": date.today().isoformat(),
        "upstream": {"site": UPSTREAM_SITE, "repo": f"https://github.com/{UPSTREAM_REPO}",
                     "note": "数据与存证与英文原站同源，未做改动；仅页面文字为中文译文。"},
        "corpus": {
            "units_2026": corpus["units_2026"], "reviews_2026": corpus["reviews_2026"],
            "units_2018_2026_direct": corpus["units_direct"], "forums_2018_2026": corpus["forums_direct"],
            "units_total": corpus["units_2026"] + corpus["units_direct"],
        },
        "endpoints": {
            "index": f"{base}api/v1/index.json",
            "deposition": f"{base}api/v1/plates/{{plate-id}}.json",
            "data": f"{base}api/v1/data/{{island}}.json",
            "corrections": f"{base}api/v1/corrections.json",
            "contact": f"{base}api/v1/contact.json",
            "openapi": f"{base}openapi.yaml",
            "llms": f"{base}llms.txt",
            "docs": f"{base}api/",
        },
        "plates": [
            {"id": pid, "number": no, "title": title, "act": act, "islands": isl,
             "deposition": f"{base}api/v1/plates/{pid}.json" if pid in dep_ids else None,
             "deposition_status": "available" if pid in dep_ids else "pending"}
            for pid, no, title, act, isl in PLATES
        ],
        "islands": islands,
    }
    (api / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding="utf-8")

    contact = {
        "what": "如何联系这份图谱的作者与本中文镜像的维护者，包括由 agent 直接发起、无需人工中转的方式。"
                "本站只提供静态文件，没有写入端点，也不发放 API key。收件箱是公开的 issue tracker，用你自己的凭据调用。",
        "upstream_author": {"name": "Shiro Takagi", "x": "https://x.com/takagi_shiro",
                            "site": UPSTREAM_SITE, "repo": f"https://github.com/{UPSTREAM_REPO}"},
        "mirror_maintainer": {"repo": f"https://github.com/{MIRROR_REPO}"},
        "channels": [
            {"id": "correction", "for": "你认为站上某条断言有误，或某个推导用它的重算脚本复现不出来。数据与分析属于原作者，请报到原仓库。",
             "visibility": "public",
             "web": f"https://github.com/{UPSTREAM_REPO}/issues/new?template=correction.yml",
             "api": {"method": "POST", "url": f"https://api.github.com/repos/{UPSTREAM_REPO}/issues",
                     "auth": "你自己的 GitHub token。", "body": {"title": "correction: <claim-id> — <one line>", "labels": ["correction"]}},
             "report_fields": {"claim_id": "必填。例如 plate-xi#11-extend-leads。写 id，不要抄图注。",
                               "as_published": "站上现在的数值或表述。", "proposed": "你认为正确的值。",
                               "evidence": "你如何核对：重算、数据岛路径、或对推导本身的论证。", "confidence": "可选。不确定就直说。"}},
            {"id": "translation", "for": "中文译文的错误、术语不当、排版问题。", "visibility": "public",
             "web": f"https://github.com/{MIRROR_REPO}/issues/new",
             "api": {"method": "POST", "url": f"https://api.github.com/repos/{MIRROR_REPO}/issues",
                     "auth": "你自己的 GitHub token。", "body": {"title": "translation: <page> — <one line>", "labels": ["translation"]}}},
            {"id": "question", "for": "关于方法、分类体系、语料或某条注意事项的问题。", "visibility": "public",
             "web": f"https://github.com/{UPSTREAM_REPO}/issues/new?template=question.yml"},
        ],
        "not_available": {"write_endpoint": "本站 /api/ 下没有 POST 端点。", "api_keys": "不发放。", "email": "不公开。"},
    }
    (api / "contact.json").write_text(json.dumps(contact, indent=1, ensure_ascii=False), encoding="utf-8")

    llms = (API_ASSETS / "llms.txt").read_text(encoding="utf-8")
    llms = (llms.replace("__TOTAL_UNITS__", f"{corpus['units_2026'] + corpus['units_direct']:,}")
                .replace("__U2026__", f"{corpus['units_2026']:,}")
                .replace("__R2026__", f"{corpus['reviews_2026']:,}")
                .replace("__ISLAND_COUNT__", str(len(islands)))
                .replace("__PLATE_COUNT__", str(len(dep_ids))))
    preface = (f"# 评判图谱 · Atlas of Judgment（中文译本）\n\n"
               f"> This is the Chinese translation of Shiro Takagi's Atlas of Judgment ({UPSTREAM_SITE}).\n"
               f"> Page text is translated; every data island, deposition and correction below is served unchanged\n"
               f"> from the same audited data. Paths on this host are prefixed with {base}. Translation issues:\n"
               f"> https://github.com/{MIRROR_REPO}/issues — data corrections belong upstream.\n\n")
    (dist / "llms.txt").write_text(preface + rebase(llms, base, site), encoding="utf-8")

    openapi = (API_ASSETS / "openapi.yaml").read_text(encoding="utf-8")
    openapi = openapi.replace(UPSTREAM_SITE, f"{site}{base.rstrip('/')}")
    (dist / "openapi.yaml").write_text(openapi, encoding="utf-8")

    rows = []
    for p in index["plates"]:
        dep = f'<a href="/api/v1/plates/{p["id"]}.json">JSON</a>' if p["deposition"] else '<span class="pending">PENDING</span>'
        chips = "".join(f'<span class="chip">{i}</span>' for i in p["islands"]) or "—"
        rows.append(f'<tr><td><span class="pn">{p["number"]}</span></td><td>{p["title"]}</td>'
                    f'<td style="font-family:var(--mono);font-size:10px">{p["act"]}</td>'
                    f'<td>{dep}</td><td>{chips}</td></tr>')
    details = []
    for isl in islands:
        if isl["bytes"] >= 8_000_000:
            keys = "(大文件)"
        else:
            doc = json.loads((api / "data" / isl["file"]).read_text(encoding="utf-8"))
            keys = ", ".join(list(doc)[:8]) if isinstance(doc, dict) else f"(数组，{len(doc)} 条记录)"
        flag = ' · <span style="color:var(--muted)">孤立 — 目前没有图版渲染它</span>' if isl["status"] == "orphaned" else ""
        plates_txt = ", ".join(isl["plates"]) or "—"
        details.append(
            f'<details><summary>{isl["file"]}<span class="sz">{isl["bytes"] / 1e6:.2f} MB</span></summary>'
            f'<div class="body">读取它的图版：{plates_txt}{flag}<br>顶层键：<code>{keys}</code>'
            f'<br><a href="/api/v1/data/{isl["file"]}">下载</a></div></details>')
    docs = (API_ASSETS / "api-docs.html").read_text(encoding="utf-8")
    docs = (docs.replace("__PLATE_ROWS__", "\n    ".join(rows))
                .replace("__ISLANDS__", "\n  ".join(details))
                .replace("__ISLAND_COUNT__", str(len(islands)))
                .replace("__BUILD_DATE__", date.today().isoformat()))
    if all(p["deposition"] for p in index["plates"]):
        docs = re.sub(r"<p[^>]*>[^<]*<span[^>]*>PENDING</span>[^<]*</p>\n?", "", docs)
    title, desc = OG["api"]
    (dist / "api" / "index.html").write_text(rebase(head(site, base, "api/", title, desc) + docs, base, site), encoding="utf-8")
    logger.info("api: %d islands, %d depositions, index + contact + llms.txt + openapi + docs", len(islands), len(dep_ids))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".pages-dist")
    ap.add_argument("--base", default="/")
    ap.add_argument("--site", default="https://lauorie.github.io")
    args = ap.parse_args()
    base = args.base if args.base.endswith("/") else args.base + "/"
    site = args.site.rstrip("/")
    dist = Path(args.out)
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True)
    stage_pages(dist, base, site)
    build_api(dist, base, site)
    total = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    logger.info("staged %s (%.1f MB) for %s%s", dist, total / 1e6, site, base)


if __name__ == "__main__":
    main()
