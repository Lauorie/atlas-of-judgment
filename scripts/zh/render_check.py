"""Load built pages in headless Chromium and report errors, leftover English, screenshots.

  <venv>/bin/python scripts/zh/render_check.py --dist DIR [--base /atlas-of-judgment/] [--shots DIR]

Serves DIR (mounted under --base) on a local port, opens every page, collects
console errors and uncaught exceptions, counts visible text blocks that still
read as English, and saves full-page screenshots. Exits non-zero on page errors.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import logging
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)
PAGES = ["index.html", "about.html", "method.html", "resources.html", "404.html"]

LEFTOVER_JS = """
() => {
  const cjk = /[\\u4e00-\\u9fff]/, word = /[A-Za-z][A-Za-z'’-]+/g;
  const out = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    const p = n.parentElement;
    if (!p || ["SCRIPT", "STYLE", "CODE", "PRE", "KBD"].includes(p.tagName)) continue;
    const t = n.textContent.trim();
    const words = t.match(word) || [];
    if (words.length >= 4 && !cjk.test(t)) {
      const cs = getComputedStyle(p);
      if (cs.display === "none" || cs.visibility === "hidden") continue;
      out.push({ text: t.slice(0, 140), path: p.tagName.toLowerCase() + (p.id ? "#" + p.id : "") + (p.className && typeof p.className === "string" ? "." + p.className.split(" ")[0] : "") });
    }
  }
  return out;
}
"""


def serve(root: Path, base: str, port: int) -> http.server.ThreadingHTTPServer:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path: str) -> str:  # noqa: D401
            path = path.split("?", 1)[0].split("#", 1)[0]
            if path.startswith(base):
                path = "/" + path[len(base):]
            elif base != "/":
                return str(root / "__nope__")
            return super().translate_path(path)

        def log_message(self, *_: Any) -> None:
            return

    handler = functools.partial(Handler, directory=str(root))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", required=True)
    ap.add_argument("--base", default="/")
    ap.add_argument("--shots")
    ap.add_argument("--port", type=int, default=8765 + 1000)
    ap.add_argument("--pages", nargs="*", default=PAGES)
    args = ap.parse_args()
    base = args.base if args.base.endswith("/") else args.base + "/"
    srv = serve(Path(args.dist), base, args.port)
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    failed = False
    report: Dict[str, Any] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for page_name in args.pages:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors: List[str] = []
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
            url = f"http://127.0.0.1:{args.port}{base}{page_name}"
            page.goto(url, wait_until="load", timeout=120_000)
            page.wait_for_timeout(2500)
            for _ in range(6):
                page.mouse.wheel(0, 2400)
                page.wait_for_timeout(400)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(800)
            title = page.title()
            leftovers = page.evaluate(LEFTOVER_JS)
            font_errors = [e for e in errors if "fonts" in e or "loli" in e]
            real_errors = [e for e in errors if e not in font_errors and "favicon" not in e]
            report[page_name] = {"title": title, "errors": real_errors, "leftover_english_blocks": len(leftovers),
                                 "leftover_samples": leftovers[:25]}
            logger.info("%s | title=%r | errors=%d | english blocks=%d", page_name, title, len(real_errors), len(leftovers))
            for e in real_errors[:8]:
                logger.info("    %s", e[:300])
            if shots:
                page.screenshot(path=str(shots / (page_name.replace(".html", "") + ".png")), full_page=False)
            if real_errors:
                failed = True
            page.close()
        browser.close()
    srv.shutdown()
    out = Path(args.shots or ".") / "render-report.json" if args.shots else None
    if out:
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
