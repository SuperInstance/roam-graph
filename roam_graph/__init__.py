"""roam-graph: lightweight cross-reference indexer for documentation graphs.

Walks a directory of markdown files, extracts outbound references between
documents, and produces:

1. A graph.json with nodes + edges
2. An audience-tagged index of reading guides (engineer, builder, agent,
   philosopher, explorer)
3. A markdown report that prints a one-page summary of what's connected
   to what

Use cases:
    - "What docs reference 'constraint theory'?"
    - "What's the entry point for a new engineer?"
    - "Which essays are referenced by code repos?"

Usage:
    from roam_graph import Roam, load_repo_index
    r = Roam.from_directory("/path/to/docs")
    r.build_graph()
    r.write("out/report.md")
"""

from roam_graph.roam import Roam, Audience, Node, Edge

__version__ = "0.1.0"
__all__ = ["Roam", "Audience", "Node", "Edge"]
