"""Segment an HTML document into translatable spans without re-serializing it.

Every character of the document is attributed to a token; segments are spans of
the original text, so injection is a plain span replacement and the untouched
markup stays byte-identical. Script/style contents are left to the JS and
island tooling.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Iterator, List, Optional, Tuple

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
RAW_CONTENT = {"script", "style", "template", "pre", "textarea", "iframe"}
BLOCK = {
    "address", "article", "aside", "blockquote", "body", "button", "canvas", "caption", "dd", "details", "dialog",
    "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
    "head", "header", "hr", "html", "label", "legend", "li", "main", "menu", "nav", "noscript", "ol", "option",
    "optgroup", "p", "section", "select", "summary", "svg", "table", "tbody", "td", "tfoot", "th", "thead", "title",
    "tr", "ul", "text", "desc", "g", "foreignobject", "defs", "symbol", "marker", "pattern", "clippath", "mask",
    "lineargradient", "radialgradient", "filter", "video", "audio", "picture", "colgroup", "col", "output", "progress",
}
TEXT_ATTRS = ("title", "aria-label", "alt", "placeholder", "aria-description", "aria-valuetext", "data-tip",
              "data-label", "data-caption", "data-title", "data-mag", "aria-roledescription", "label")
META_TEXT = {"description", "og:title", "og:description", "twitter:title", "twitter:description", "keywords"}
_LETTERS = re.compile(r"[A-Za-z]{2,}")
_ATTR_RE = re.compile(r'(?<![\w-])([\w:-]+)\s*=\s*"([^"]*)"')
# elements whose start tag implicitly closes an open <p> (HTML spec)
_P_CLOSERS = {
    "address", "article", "aside", "blockquote", "details", "div", "dl", "fieldset", "figcaption", "figure", "footer",
    "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "main", "menu", "nav", "ol", "p", "pre",
    "section", "table", "ul",
}


@dataclass
class Tok:
    kind: str  # start | end | text | other
    start: int
    end: int
    tag: str = ""
    attrs: List[Tuple[str, Optional[str]]] = field(default_factory=list)
    selfclosing: bool = False


class _Scanner(HTMLParser):
    def __init__(self, src: str) -> None:
        super().__init__(convert_charrefs=False)
        self.src = src
        self.toks: List[Tok] = []
        self._lines = [0]
        for m in re.finditer(r"\n", src):
            self._lines.append(m.end())

    def _pos(self) -> int:
        line, off = self.getpos()
        return self._lines[line - 1] + off

    def _push(self, kind: str, tag: str = "", attrs: Optional[list] = None, selfclosing: bool = False) -> None:
        self.toks.append(Tok(kind, self._pos(), -1, tag, attrs or [], selfclosing))

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self._push("start", tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self._push("start", tag, attrs, selfclosing=True)

    def handle_endtag(self, tag: str) -> None:
        self._push("end", tag)

    def handle_data(self, data: str) -> None:
        self._push("text")

    def handle_entityref(self, name: str) -> None:
        self._push("text")

    def handle_charref(self, name: str) -> None:
        self._push("text")

    def handle_comment(self, data: str) -> None:
        self._push("other")

    def handle_decl(self, decl: str) -> None:
        self._push("other")

    def handle_pi(self, data: str) -> None:
        self._push("other")

    def unknown_decl(self, data: str) -> None:
        self._push("other")


def tokenize(src: str) -> List[Tok]:
    """Tokenize HTML so that tokens tile the whole document."""
    sc = _Scanner(src)
    sc.feed(src)
    sc.close()
    toks = sc.toks
    for i, t in enumerate(toks):
        t.end = toks[i + 1].start if i + 1 < len(toks) else len(src)
    merged: List[Tok] = []
    for t in toks:
        if t.kind == "text" and merged and merged[-1].kind == "text":
            merged[-1].end = t.end
        else:
            merged.append(t)
    if merged and merged[-1].end < len(src):
        merged[-1].end = len(src)
    return merged


@dataclass
class Node:
    tag: str  # "" for text
    start: int  # token index
    end: int  # token index of end tag (same as start for void/text)
    children: List["Node"] = field(default_factory=list)
    tok: Optional[Tok] = None

    @property
    def is_text(self) -> bool:
        return self.tag == ""


def build_tree(toks: List[Tok]) -> Node:
    """Build an element tree from the token stream, tolerating omitted end tags."""
    root = Node("#root", -1, len(toks))
    stack: List[Node] = [root]
    for i, t in enumerate(toks):
        if t.kind == "start":
            tag = t.tag
            top = stack[-1].tag
            if (tag in _P_CLOSERS and top == "p") or (tag == "li" and top == "li") \
                    or (tag in ("td", "th", "tr") and top in ("td", "th")) or (tag == "tr" and top == "tr") \
                    or (tag in ("dt", "dd") and top in ("dt", "dd")) or (tag == "option" and top == "option"):
                stack[-1].end = i
                stack.pop()
            node = Node(tag, i, i, tok=t)
            stack[-1].children.append(node)
            if not (t.selfclosing or tag in VOID):
                stack.append(node)
        elif t.kind == "end":
            for depth in range(len(stack) - 1, 0, -1):
                if stack[depth].tag == t.tag:
                    stack[depth].end = i
                    del stack[depth:]
                    break
        else:
            stack[-1].children.append(Node("", i, i, tok=t))
    for n in stack[1:]:
        n.end = len(toks) - 1
    return root


@dataclass(frozen=True)
class Segment:
    kind: str  # block | run | attr
    start: int  # char offset
    end: int
    path: str


def _has_letters(s: str) -> bool:
    return bool(_LETTERS.search(re.sub(r"<[^>]*>", " ", s)))


def _is_blockish(c: Node) -> bool:
    return c.tag in BLOCK or c.tag in RAW_CONTENT


def _contains_block(n: Node) -> bool:
    return any(_is_blockish(c) or (not c.is_text and _contains_block(c)) for c in n.children)


def _trim(src: str, a: int, b: int) -> Tuple[int, int]:
    while a < b and src[a].isspace():
        a += 1
    while b > a and src[b - 1].isspace():
        b -= 1
    return a, b


def _ident(c: Node) -> str:
    if c.tok is None:
        return ""
    d = dict(c.tok.attrs)
    return ("#" + d["id"]) if d.get("id") else ""


class _Collector:
    def __init__(self, src: str, toks: List[Tok]) -> None:
        self.src, self.toks = src, toks
        self.out: List[Segment] = []

    def attrs(self, n: Node, path: str) -> None:
        t = n.tok
        if t is None:
            return
        raw = self.src[t.start:t.end]
        wanted = set(TEXT_ATTRS)
        if n.tag == "meta":
            names = dict(t.attrs)
            key = names.get("name") or names.get("property") or ""
            if key not in META_TEXT:
                return
            wanted = {"content"}
        for m in _ATTR_RE.finditer(raw):
            name, val = m.group(1).lower(), m.group(2)
            if name not in wanted or not _LETTERS.search(val):
                continue
            if re.fullmatch(r"[\w./#:-]+", val) and (name == "content" or len(val) < 4):
                continue
            self.out.append(Segment("attr", t.start + m.start(2), t.start + m.end(2), f"{path}@{name}"))

    def attrs_only(self, n: Node, path: str) -> None:
        if n.is_text:
            return
        self.attrs(n, path)
        for c in n.children:
            self.attrs_only(c, path + ">" + c.tag)

    def leaf(self, n: Node, path: str) -> None:
        if n.tag in VOID or (n.tok and n.tok.selfclosing):
            return
        toks = self.toks
        a = toks[n.start].end
        b = toks[n.end].start if n.end != n.start else a
        a, b = _trim(self.src, a, b)
        if b > a and _has_letters(self.src[a:b]):
            self.out.append(Segment("block", a, b, path))

    def walk(self, n: Node, path: str) -> None:
        if n.is_text:
            return
        if n.tag != "#root":
            self.attrs(n, path)
        if n.tag in RAW_CONTENT:
            return
        if n.tag != "#root" and not _contains_block(n):
            self.leaf(n, path)
            return
        run: List[Node] = []

        def flush() -> None:
            if not run:
                return
            a = self.toks[run[0].start].start
            b = self.toks[run[-1].end].end
            a, b = _trim(self.src, a, b)
            if b > a and _has_letters(self.src[a:b]):
                self.out.append(Segment("run", a, b, path + "#run"))
            else:
                for c in run:
                    self.attrs_only(c, path + ">" + c.tag)
            run.clear()

        for c in n.children:
            inline = c.is_text or (not _is_blockish(c) and not _contains_block(c))
            if inline:
                if c.is_text and self.toks[c.start].kind != "text":
                    flush()
                    continue
                run.append(c)
            else:
                flush()
                self.walk(c, path + ">" + c.tag + _ident(c))
        flush()


def segments(src: str) -> List[Segment]:
    """Return all translatable spans: leaf-block inner HTML, inline runs, and text attributes."""
    toks = tokenize(src)
    root = build_tree(toks)
    col = _Collector(src, toks)
    col.walk(root, "")
    out = sorted(col.out, key=lambda s: s.start)
    for a, b in zip(out, out[1:]):
        if b.start < a.end:
            raise ValueError(f"overlapping segments at {a} / {b}")
    return out


def script_spans(src: str) -> Iterator[Tuple[dict, int, int]]:
    """Yield (attrs, content_start, content_end) for every <script> element."""
    toks = tokenize(src)
    for i, t in enumerate(toks):
        if t.kind == "start" and t.tag == "script" and not t.selfclosing:
            j = i + 1
            while j < len(toks) and not (toks[j].kind == "end" and toks[j].tag == "script"):
                j += 1
            if j < len(toks):
                yield dict(t.attrs), t.end, toks[j].start
