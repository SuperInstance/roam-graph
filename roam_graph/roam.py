"""Roam — cross-reference graph builder for an org's docs.

Walks a directory, identifies markdown files, extracts:

    title     : first H1, fallback to filename
    audience  : tag from YAML frontmatter or path
    outbound  : files this doc links to (markdown links only)
    tags      : keywords from frontmatter

Then produces:
    - nodes: {path: {title, audience, tags, size_words}}
    - edges: {path: [outbound_paths]}
    - report: a markdown one-pager with reading guides per audience
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


class Audience(str, Enum):
    """Document's intended audience — derived from frontmatter or path."""

    ENGINEER = "engineer"
    PHILOSOPHER = "philosopher"
    BUILDER = "builder"
    AGENT = "agent"
    EXPLORER = "explorer"
    UNKNOWN = "unknown"


@dataclass
class Node:
    path: str                               # relative path from root
    title: str                              # first H1
    audience: Audience = Audience.UNKNOWN
    tags: List[str] = field(default_factory=list)
    word_count: int = 0
    inbound: Set[str] = field(default_factory=set)    # computed after graph build
    outbound: Set[str] = field(default_factory=set)


@dataclass
class Edge:
    src: str
    dst: str                                # relative to root, resolved


# ---------------------------------------------------------------------------
# Markdown scanning
# ---------------------------------------------------------------------------

H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
LINK_RE = re.compile(r"\]\(([^)#?]+)(?:#[^)]*)?\)")
YAML_FRONT_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
KEYVAL_RE = re.compile(r"^([A-Za-z_]+):\s*(.+?)\s*$", re.MULTILINE)


def _slugify(text: str) -> str:
    """Best-effort slug from a path or string."""
    text = re.sub(r"[^A-Za-z0-9_-]+", "-", text.lower()).strip("-")
    return text or ""


def _parse_frontmatter(text: str) -> Dict[str, str]:
    m = YAML_FRONT_RE.search(text)
    out: Dict[str, str] = {}
    if not m:
        return out
    block = m.group(1)
    for km in KEYVAL_RE.finditer(block):
        k = km.group(1).lower()
        v = km.group(2).strip().strip('"\'')
        out[k] = v
    return out


def _extract_outbound_links(text: str, current_path: Path, root: Path) -> List[str]:
    """Find markdown links and resolve to existing files (by name)."""
    candidates: List[str] = []

    for lm in LINK_RE.finditer(text):
        target = lm.group(1).strip()
        if target.startswith(("/", "http:", "https:", "mailto:")):
            continue
        # Resolve relative to the current file
        try:
            if not target:
                continue
            resolved = (current_path.parent / target).resolve()
            try:
                rel = resolved.relative_to(root.resolve())
                candidates.append(str(rel))
            except ValueError:
                continue
        except OSError:
            continue
    return candidates


def _audience_from_path(path: Path) -> Audience:
    """Guess audience from path components."""
    s = str(path).lower()
    if "/engineer" in s or "/engineering" in s or "/spec" in s or "/flux" in s or "/plato" in s:
        return Audience.ENGINEER
    if "/philosopher" in s or "/essays" in s or "/philosophy" in s or "/paradigm" in s:
        return Audience.PHILOSOPHER
    if "/builder" in s or "/example" in s or "/tutorial" in s or "/getting-started" in s:
        return Audience.BUILDER
    if "agent" in s or "baton" in s or "/lessons" in s:
        return Audience.AGENT
    if "/explorer" in s or "/polyformalism" in s or "/excavation" in s or "/casting" in s:
        return Audience.EXPLORER
    if "/ideation" in s:
        return Audience.AGENT
    return Audience.UNKNOWN


# ---------------------------------------------------------------------------
# Roam — the graph
# ---------------------------------------------------------------------------


class Roam:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.nodes: Dict[str, Node] = {}

    @classmethod
    def from_directory(cls, root: str) -> "Roam":
        r = cls(root)
        r._scan()
        return r

    def _scan(self) -> None:
        if not self.root.exists():
            return
        for md in self.root.rglob("*.md"):
            try:
                rel = md.relative_to(self.root)
            except ValueError:
                continue
            text = md.read_text(encoding="utf-8", errors="replace")
            h1 = H1_RE.search(text)
            title = h1.group(1).strip() if h1 else md.stem.replace("-", " ").title()
            front = _parse_frontmatter(text)
            audience = Audience.UNKNOWN
            if "audience" in front:
                try:
                    audience = Audience(front["audience"].lower())
                except ValueError:
                    audience = Audience.UNKNOWN
            else:
                audience = _audience_from_path(md)
            tags: List[str] = []
            if "tags" in front:
                tags = [t.strip() for t in re.split(r"[,\s]+", front["tags"]) if t.strip()]
            elif "topics" in front:
                tags = [t.strip() for t in re.split(r"[,\s]+", front["topics"]) if t.strip()]
            word_count = len(text.split())
            outbound = set(_extract_outbound_links(text, md, self.root))
            n = Node(
                path=str(rel),
                title=title,
                audience=audience,
                tags=tags,
                word_count=word_count,
                outbound=outbound,
            )
            self.nodes[str(rel)] = n

    def build_graph(self) -> None:
        """Resolve outbound links to nodes; populate inbound sets."""
        for n in self.nodes.values():
            for o in list(n.outbound):
                if o not in self.nodes:
                    # Unknown target — remove from outbound (broken link)
                    continue
            n.outbound = {o for o in n.outbound if o in self.nodes}
        for n in self.nodes.values():
            for o in n.outbound:
                if o in self.nodes:
                    self.nodes[o].inbound.add(n.path)

    # ----- queries --------------------------------------------------------

    def by_audience(self, audience: Audience, limit: int = 50) -> List[Node]:
        items = [n for n in self.nodes.values() if n.audience == audience]
        items.sort(key=lambda x: (-x.word_count, x.path))
        return items[:limit]

    def inbound_to(self, path: str) -> List[Node]:
        if path not in self.nodes:
            return []
        return [self.nodes[p] for p in self.nodes[path].inbound]

    def most_connected(self, limit: int = 20) -> List[Node]:
        items = []
        for n in self.nodes.values():
            score = len(n.inbound) + len(n.outbound)
            if score > 0:
                items.append((score, n))
        items.sort(key=lambda x: -x[0])
        return [n for _, n in items[:limit]]

    def orphans(self) -> List[Node]:
        """Documents with zero inbound and zero outbound links."""
        out = []
        for n in self.nodes.values():
            if not n.inbound and not n.outbound:
                out.append(n)
        return out

    # ----- output ---------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "root": str(self.root),
            "node_count": len(self.nodes),
            "edges": [
                {"src": n.path, "dst": o}
                for n in self.nodes.values()
                for o in n.outbound
            ],
            "audiences": {
                a.value: [
                    {"path": n.path, "title": n.title, "word_count": n.word_count}
                    for n in self.by_audience(a, limit=100)
                ]
                for a in Audience
                if self.by_audience(a, limit=1)
            },
        }

    def write(self, out_path: str = "roam-report.md") -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        text = self.render_report()
        out.write_text(text, encoding="utf-8")
        # Also dump JSON sidecar
        json_out = out.with_suffix(".json")
        json_out.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return out

    def render_report(self) -> str:
        lines: List[str] = []
        lines.append(f"# Roam — Cross-reference Report")
        lines.append(f"\n**Root:** `{self.root}`")
        lines.append(f"**Documents scanned:** {len(self.nodes)}\n")

        lines.append("## Summary by Audience\n")
        for aud in Audience:
            items = self.by_audience(aud, limit=5)
            if not items:
                continue
            lines.append(f"### {aud.value.title()} ({len(self.by_audience(aud, limit=1000))} docs)\n")
            for n in items:
                lines.append(f"- [{n.title}]({n.path}) — {n.word_count} words")
            lines.append("")

        lines.append("## Most Connected (Top 15)\n")
        for n in self.most_connected(limit=15):
            lines.append(
                f"- [{n.title}]({n.path}) — "
                f"{len(n.inbound)} in, {len(n.outbound)} out"
            )
        lines.append("")

        orphans_ = self.orphans()
        lines.append(f"## Orphan Documents ({len(orphans_)})\n")
        lines.append("These have no inbound or outbound references — likely entry points or dead ends.\n")
        for n in orphans_[:25]:
            lines.append(f"- [{n.title}]({n.path}) — {n.word_count} words")
        lines.append("")

        return "\n".join(lines).rstrip() + "\n"
