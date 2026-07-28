"""Tests para fix_markdownlint.py"""

from __future__ import annotations

import unittest

from fix_markdownlint import (
    fix_emphasis_headings,
    fix_fenced_code_language_v2,
    fix_line_length,
    fix_markdown,
    format_aligned_table,
    parse_table_cells,
    wrap_prose_line,
)


class TestMd013(unittest.TestCase):
    def test_wraps_long_prose(self) -> None:
        long = "a " * 60
        wrapped = wrap_prose_line(long.strip(), width=40)
        self.assertGreater(len(wrapped), 1)
        self.assertTrue(all(len(line) <= 40 for line in wrapped))

    def test_skips_long_url_without_spaces(self) -> None:
        url = "https://example.com/" + "a" * 90
        self.assertEqual(wrap_prose_line(url, width=100), [url])

    def test_wraps_ordered_list_item(self) -> None:
        src = "3. " + "word " * 30
        fixed, n = fix_line_length(src)
        self.assertGreater(n, 0)
        self.assertTrue(all(len(line) <= 100 for line in fixed.splitlines()))

    def test_wraps_blockquote_when_tail_has_no_spaces(self) -> None:
        src = (
            "> **Enfoque (jul 2026):** no `cargo_*.xml`. Masa chasis en Fase 1. "
            "Sim orienta; prueba en juego. CE archivado."
        )
        fixed, n = fix_line_length(src)
        self.assertGreater(n, 0)
        self.assertTrue(all(len(line) <= 100 for line in fixed.splitlines()))


class TestTables(unittest.TestCase):
    def test_parse_and_align(self) -> None:
        rows = [
            parse_table_cells("|a|b|"),
            parse_table_cells("|---|---|"),
            parse_table_cells("|Y|Yes|"),
        ]
        rows = [r for r in rows if r is not None]
        out = format_aligned_table(rows)
        self.assertTrue(all(" | " in line for line in out))
        self.assertEqual(len(out), 3)

    def test_compact_separator_gets_spaces(self) -> None:
        src = "| Escenario | Notas |\n|-----------|-------|\n| F1 | ok |\n"
        fixed, stats = fix_markdown(src)
        self.assertGreater(stats["MD060"], 0)
        self.assertIn("| ----------- |", fixed)


class TestFences(unittest.TestCase):
    def test_add_language_open_only(self) -> None:
        src = "```\nline\n```\n"
        fixed, n = fix_fenced_code_language_v2(src)
        self.assertEqual(n, 1)
        self.assertTrue(fixed.startswith("```text\n"))
        self.assertTrue(fixed.rstrip().endswith("```"))

    def test_keeps_powershell_close(self) -> None:
        src = "```powershell\npython x\n```\n"
        fixed, n = fix_fenced_code_language_v2(src)
        self.assertEqual(n, 0)
        self.assertNotIn("```text\n```", fixed)


class TestHeadings(unittest.TestCase):
    def test_emphasis_under_section_becomes_h4(self) -> None:
        src = "## Vehiculo\n\n**Comentarios**\n"
        fixed, n = fix_emphasis_headings(src)
        self.assertEqual(n, 1)
        self.assertIn("#### Comentarios", fixed)

    def test_italic_emphasis_becomes_heading(self) -> None:
        src = "# Doc\n\n_Seccion_\n"
        fixed, n = fix_emphasis_headings(src)
        self.assertEqual(n, 1)
        self.assertIn("## Seccion", fixed)

    def test_punctuation_emphasis_unchanged(self) -> None:
        src = "**My document.**\n"
        fixed, n = fix_emphasis_headings(src)
        self.assertEqual(n, 0)
        self.assertEqual(fixed.strip(), "**My document.**")

    def test_bold_inline_unchanged(self) -> None:
        src = "**Enfoque:** texto"
        fixed, n = fix_emphasis_headings(src)
        self.assertEqual(n, 0)
        self.assertEqual(fixed, src)


if __name__ == "__main__":
    unittest.main()
