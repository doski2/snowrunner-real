"""Tests de auditoria de remolques (sin .pak)."""

from __future__ import annotations

import unittest

from auditar_remolques import TRAILER_KEYS, audit_trailer_xml, load_trailers

SAMPLE_XML = """
<Truck>
  <Body Mass="800" CenterOfMassOffset="(0; 0; 0)" />
  <Body Mass="150" />
  <Wheel />
  <Wheel />
  <Axle />
  <AttachType="Drawbar" />
</Truck>
"""


class TestAuditarRemolques(unittest.TestCase):
    def test_audit_trailer_xml_parses_mass_and_attach(self) -> None:
        info = audit_trailer_xml(SAMPLE_XML)
        self.assertEqual(info["mass_largest_body_kg"], 800.0)
        self.assertEqual(info["mass_all_bodies_kg"], 950.0)
        self.assertEqual(info["mass_parts_kg"], [800.0, 150.0])
        self.assertEqual(info["attach_type"], "Drawbar")
        self.assertEqual(info["wheel_count"], 2)
        self.assertEqual(info["axle_count"], 1)

    def test_audit_trailer_xml_empty(self) -> None:
        info = audit_trailer_xml("<Truck></Truck>")
        self.assertEqual(info["mass_largest_body_kg"], 0.0)
        self.assertEqual(info["attach_type"], "Drawbar")

    def test_trailer_keys_count(self) -> None:
        self.assertEqual(len(TRAILER_KEYS), 6)

    def test_load_trailers_missing_pak(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_trailers("no_existe.pak")


if __name__ == "__main__":
    unittest.main()
