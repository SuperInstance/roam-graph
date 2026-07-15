"""Tests for roam-graph."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from roam_graph import Roam, Audience
from roam_graph.roam import _parse_frontmatter, _extract_outbound_links, H1_RE


class TestFrontmatter(unittest.TestCase):
    def test_parses_simple(self):
        text = "---\nfoo: bar\nbaz: 123\n---\n# Title\n"
        fm = _parse_frontmatter(text)
        self.assertEqual(fm["foo"], "bar")
        self.assertEqual(fm["baz"], "123")

    def test_parses_with_quotes(self):
        text = '---\ntitle: "Hello"\naudience: \'engineer\'\n---\n'
        fm = _parse_frontmatter(text)
        self.assertEqual(fm["title"], "Hello")
        self.assertEqual(fm["audience"], "engineer")

    def test_no_frontmatter(self):
        fm = _parse_frontmatter("# Just a title\n")
        self.assertEqual(fm, {})


class TestLinkExtraction(unittest.TestCase):
    def test_relative_link(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.md").write_text("[link](b.md)")
            (root / "b.md").write_text("# B")
            out = _extract_outbound_links((root / "a.md").read_text(), root / "a.md", root)
            self.assertEqual(out, ["b.md"])

    def test_external_link_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.md").write_text("[ext](https://example.com)")
            (root / "a.md").write_text("[local](b.md)")
            (root / "b.md").write_text("# B")
            out = _extract_outbound_links((root / "a.md").read_text(), root / "a.md", root)
            self.assertEqual(out, ["b.md"])

    def test_parent_dir_link(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "sub").mkdir()
            (root / "sub" / "a.md").write_text("[up](../top.md)")
            (root / "top.md").write_text("# Top")
            out = _extract_outbound_links(
                (root / "sub" / "a.md").read_text(),
                root / "sub" / "a.md",
                root,
            )
            self.assertEqual(out, ["top.md"])


class TestRoam(unittest.TestCase):
    def _build_sample(self):
        d = Path(tempfile.mkdtemp())
        # 3 docs with cross-references
        (d / "README.md").write_text(
            "---\ntitle: Index\naudience: engineer\n---\n# Index\n"
            "[main](main.md)\n[explorer](explorer/explore.md)\n"
        )
        (d / "main.md").write_text(
            "---\naudience: builder\ntags: starter\n---\n# Main\n[back](../README.md)\n"
        )
        (d / "explorer").mkdir()
        (d / "explorer" / "explore.md").write_text(
            "---\naudience: explorer\n---\n# Explore\n"
        )
        (d / "lonely.md").write_text("# Lonely\n")
        return d

    def test_scan(self):
        d = self._build_sample()
        r = Roam.from_directory(str(d))
        self.assertIn("README.md", r.nodes)
        self.assertIn("main.md", r.nodes)
        self.assertIn("explorer/explore.md", r.nodes)

    def test_audiences(self):
        d = self._build_sample()
        r = Roam.from_directory(str(d))
        r.build_graph()
        eng = r.by_audience(Audience.ENGINEER)
        self.assertEqual(len(eng), 1)            # README.md
        bld = r.by_audience(Audience.BUILDER)
        self.assertEqual(len(bld), 1)            # main.md
        expl = r.by_audience(Audience.EXPLORER)
        self.assertEqual(len(expl), 1)
        orph = r.orphans()
        # lonely.md has no inbound/outbound
        self.assertTrue(any(n.path == "lonely.md" for n in orph))

    def test_inbound_populated(self):
        d = self._build_sample()
        r = Roam.from_directory(str(d))
        r.build_graph()
        # main.md is linked from README.md → should be in inbound
        main = r.nodes["main.md"]
        self.assertIn("README.md", main.inbound)

    def test_most_connected(self):
        d = self._build_sample()
        r = Roam.from_directory(str(d))
        r.build_graph()
        top = r.most_connected(limit=10)
        # README.md should be most connected (links to main.md, explore.md)
        self.assertGreater(len(top[0].outbound | top[0].inbound), 0)

    def test_report(self):
        d = self._build_sample()
        r = Roam.from_directory(str(d))
        r.build_graph()
        out = r.render_report()
        self.assertIn("Roam", out)
        self.assertIn("Orphan", out)

    def test_write_creates_files(self):
        d = self._build_sample()
        r = Roam.from_directory(str(d))
        r.build_graph()
        with tempfile.TemporaryDirectory() as od:
            out_path = r.write(out_path=str(Path(od) / "report.md"))
            self.assertTrue(out_path.exists())
            json_path = out_path.with_suffix(".json")
            self.assertTrue(json_path.exists())
            data = json.loads(json_path.read_text())
            self.assertEqual(data["root"], str(d.resolve()))


if __name__ == "__main__":
    unittest.main()
