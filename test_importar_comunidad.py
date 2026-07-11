"""Tests importar_comunidad parsers."""

from __future__ import annotations

import unittest

from datos.importar_comunidad import _parse_num, parse_cargo, parse_wheels


class TestImportarComunidad(unittest.TestCase):
    def test_parse_num_spaces(self) -> None:
        self.assertEqual(_parse_num("10 000"), 10000)
        self.assertEqual(_parse_num("0.32"), 0.32)

    def test_parse_cargo_row(self) -> None:
        rows = [
            ["Cargo", "Slots", "Packed Mass", "Unpacked", "Internal Name", "Notes"],
            ["Bricks", "1", "1 000", "1 000", "CargoBricks", ""],
        ]
        items = parse_cargo(rows)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["internal_names"], ["CargoBricks"])
        self.assertEqual(items[0]["packed_mass_kg"], 1000)

    def test_parse_wheels_skip_template(self) -> None:
        rows = [
            ["Wheel", "Asphalt", "Body"],
            ["Highway", "", ""],
            ["Template", "3", "1"],
            ["HMD I", "3", "1", "0.4"],
        ]
        items = parse_wheels(rows)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "HMD I")
        self.assertEqual(items[0]["category"], "Highway")
        self.assertEqual(items[0]["friction"]["asphalt"], 3)


if __name__ == "__main__":
    unittest.main()
