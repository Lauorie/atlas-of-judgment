"""Which fields of the embedded data islands carry display text worth translating.

The islands are the JSON `<script type="application/json" id="isl-*">` blocks in
index.html. Only glosses the page shows to a reader are listed here; review
quotations, paper titles, keys and numbers stay as they are. The `/api/` copies
of the same islands are served from `data/` and are not touched.
"""

from __future__ import annotations

from typing import Any, Iterator, List, Tuple

Path_ = Tuple[Any, ...]

SPEC = {
    "DATA": [
        "taxonomy.inspected_object[].label_en",
        "taxonomy.inspected_object[].definition",
        "taxonomy.reasoning[].label_en",
        "taxonomy.reasoning[].definition",
    ],
    "REPAIR": ["groups[].name"],
    "ELEMS": ["*.laws[].name", "*.laws[].def", "*.grounds[].name", "*.grounds[].def"],
    "COMBO": ["exceptions[].name", "exceptions[].def", "referents[].name", "referents[].def"],
    "MOVES": ["moves[].name", "moves[].def"],
    "ARCHI": ["islands[].name"],
    "LAWT": ["dockets.*[].name"],
    "SHEET": ["dockets.*[].name", "rows[].name", "*[].name", "top_cross[].a.name", "top_cross[].b.name",
              "bottom_cross[].a.name", "bottom_cross[].b.name", "top_same[].a.name", "top_same[].b.name"],
    "TML": ["*[].name", "rows[].name"],
}


def _walk(obj: Any, parts: List[str], path: Path_) -> Iterator[Tuple[Path_, str]]:
    if not parts:
        if isinstance(obj, str):
            yield path, obj
        return
    head, rest = parts[0], parts[1:]
    if head.endswith("[]"):
        key = head[:-2]
        target = obj if key == "" else (obj.get(key) if isinstance(obj, dict) else None)
        if key == "*" and isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, list):
                    for i, item in enumerate(v):
                        yield from _walk(item, rest, path + (k, i))
            return
        if isinstance(target, list):
            for i, item in enumerate(target):
                yield from _walk(item, rest, path + ((key, i) if key else (i,)))
        return
    if head == "*":
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from _walk(v, rest, path + (k,))
        return
    if isinstance(obj, dict) and head in obj:
        yield from _walk(obj[head], rest, path + (head,))


def fields(island: str, obj: Any) -> Iterator[Tuple[Path_, str]]:
    """Yield (json_path, value) for every display field of `island` listed in SPEC."""
    seen = set()
    for pattern in SPEC.get(island, []):
        for path, value in _walk(obj, pattern.split("."), ()):
            if path not in seen:
                seen.add(path)
                yield path, value


def set_path(obj: Any, path: Path_, value: str) -> None:
    """Assign `value` at `path` inside the parsed island."""
    cur = obj
    for p in path[:-1]:
        cur = cur[p]
    cur[path[-1]] = value
