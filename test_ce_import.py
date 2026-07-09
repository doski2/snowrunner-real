"""Tests importacion CSV Cheat Engine."""

from __future__ import annotations

import csv
import os
import tempfile
import unittest

from importar_ce_csv import csv_to_session, load_ce_csv, suggest_protocol
from telemetria import compare_session_to_sim


class TestCeImport(unittest.TestCase):
    def _write_csv(self, path: str) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t_s", "speed_kmh", "vel_x", "vel_y", "vel_z", "ang_yaw", "fuel_pct"])
            w.writerow(["0.0", "0.0", "0", "0", "0", "0", "80.0"])
            w.writerow(["10.0", "12.5", "3.47", "0", "0", "0.1", "79.5"])
            w.writerow(["30.0", "38.0", "10.5", "0", "0", "0.2", "78.0"])

    def test_load_ce_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "log.csv")
            self._write_csv(path)
            rows = load_ce_csv(path)
            self.assertEqual(len(rows), 3)
            self.assertEqual(float(rows[2]["speed_kmh"]), 38.0)

    def test_csv_to_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "log.csv")
            self._write_csv(path)
            session, _, game_id = csv_to_session(path, "f2_barro_offroad")
            self.assertTrue(session.meta.id.startswith("ce_"))
            self.assertEqual(len(session.samples), 3)
            self.assertIn("CE", session.meta.notes)

    def test_csv_detects_mh9500(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "log.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["t_s", "speed_kmh", "vehicle_id", "terrain_hint"])
                w.writerow(["0.0", "5.0", "s_gmc9500", "crawl"])
            session, terrains, game_id = csv_to_session(path, "f2_barro_offroad")
            self.assertEqual(game_id, "s_gmc9500")
            self.assertEqual(session.meta.vehicle_id, "mh9500")
            self.assertEqual(terrains.get("crawl"), 1)

    def test_suggest_protocol_marshall(self) -> None:
        self.assertEqual(suggest_protocol("marshall", "f2_barro_offroad"), "km_f2_barro_tm2")
        self.assertEqual(suggest_protocol("marshall", "f1_asfalto_i6"), "km_f1_asfalto")
        self.assertIsNone(suggest_protocol("marshall", "km_f2_barro_tm2"))

    def test_suggest_protocol_t813(self) -> None:
        self.assertEqual(suggest_protocol("t813", "f2_barro_offroad"), "t813_f2_barro_msh")
        self.assertEqual(suggest_protocol("t813", "f1_asfalto_i6"), "t813_f1_asfalto")
        self.assertEqual(suggest_protocol("t813", "f3_carga_barro"), "t813_f3_carga")

    def test_compare_imported_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "log.csv")
            self._write_csv(path)
            session, _, _ = csv_to_session(path, "f2_barro_offroad")
            cmp = compare_session_to_sim(session)
            self.assertGreater(cmp["sim_v30_kmh"], 0)

    def test_terrain_kind_in_import_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "log.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(
                    [
                        "t_s",
                        "speed_kmh",
                        "vehicle_id",
                        "terrain_kind",
                        "surface_wheel",
                        "wheel_grip",
                        "surface_avg",
                        "pos_x",
                        "pos_z",
                    ]
                )
                w.writerow(
                    [
                        "0.0",
                        "5.0",
                        "s_fleetstar_f2070a",
                        "mixed",
                        "mixed",
                        "0.45",
                        "0.2",
                        "100",
                        "200",
                    ]
                )
            session, _, _ = csv_to_session(path, "fs_f2_barro_uhd")
            self.assertIn("kind=mixed", session.samples[0].note)
            self.assertIn("pos=(100,200)", session.samples[0].note)


class TestTerrainClassifier(unittest.TestCase):
    def test_asphalt_wheels(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        r = mh.classify_terrain_from_wheels([1.0, 1.0, 1.0], [0.8, 0.79, 0.84])
        self.assertEqual(r["terrain_kind"], "hard")

    def test_fleetstar_asphalt_wheels(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        # asfalto_fs.json — grip bajo UHD pero deform negativo (no nieve)
        r = mh.classify_terrain_from_wheels(
            [0.2] * 6,
            [0.804] * 6,
            deforms=[-0.9315] * 6,
        )
        self.assertEqual(r["terrain_kind"], "hard")

    def test_alaska_snow_wheels(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        # North Port Alaska — grip ~0.2, deform +0.87, contact ~0.80
        r = mh.classify_terrain_from_wheels(
            [0.2] * 4,
            [0.804] * 4,
            deforms=[0.87, 0.92, 0.87, 0.92],
        )
        self.assertEqual(r["terrain_kind"], "snow")
        grade, label = mh.classify_mud_grade("snow", 0.2, 0.804, 0.87)
        self.assertEqual(label, "snow_packed")

    def test_ice_wheels(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        r = mh.classify_terrain_from_wheels(
            [0.04, 0.05, 0.03, 0.04],
            [0.72, 0.71, 0.70, 0.69],
            deforms=[0.2, 0.15, 0.18, 0.22],
        )
        self.assertEqual(r["terrain_kind"], "ice")
        grade, label = mh.classify_mud_grade("ice", 0.04, 0.71, 0.18)
        self.assertEqual(label, "ice")

    def test_mud_wheels(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        r = mh.classify_terrain_from_wheels([0.013, 0.013, 0.014], [-0.15, -0.15, -0.08])
        self.assertEqual(r["terrain_kind"], "mud")

    def test_mud_via_contact(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        r = mh.classify_terrain_from_wheels([0.013, 0.013], [0.57, 0.56])
        self.assertEqual(r["terrain_kind"], "mud")

    def test_mixed_wheels(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        r = mh.classify_terrain_from_wheels([1.0, 0.02, 1.0, 0.01], [0.8, -0.15, 0.79, -0.1])
        self.assertEqual(r["terrain_kind"], "mixed")

    def test_majority_mud_three_of_four(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        # 3 ruedas barro, 1 soft — mayoria mud (antes: mixed)
        r = mh.classify_terrain_from_wheels(
            [0.013, 0.013, 0.013, 0.35],
            [0.55, 0.56, 0.54, 0.65],
        )
        self.assertEqual(r["terrain_kind"], "mud")
        self.assertTrue(r["wheel_disagreement"])


class TestMudGrade(unittest.TestCase):
    def test_mud_grade_deep_ck1500(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        g, label = mh.classify_mud_grade("mud", 0.017, 0.359, -0.15)
        self.assertEqual(g, 3)
        self.assertEqual(label, "mud_deep")

    def test_mud_grade_light(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        g, label = mh.classify_mud_grade("mud", 0.12, 0.48, -0.08)
        self.assertEqual(g, 2)
        self.assertEqual(label, "mud_light")

    def test_mud_grade_dry_hard(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        g, label = mh.classify_mud_grade("hard", 0.95, 0.80, 0.75)
        self.assertEqual(g, 0)
        self.assertEqual(label, "dry_hard")

    def test_read_wheel_terrain_includes_grade_fields(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        r = mh.classify_terrain_from_wheels([0.12, 0.11], [0.48, 0.49])
        extra = mh._terrain_grade_fields(
            r["terrain_kind"],
            [0.12, 0.11],
            [0.48, 0.49],
            [-0.08, -0.07],
        )
        self.assertEqual(extra["mud_grade_label"], "mud_light")
        self.assertIn("surface_deform_avg", extra)


class TestWheelSubstanceDiff(unittest.TestCase):
    def test_diff_terrain_summary_only_changes(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import scan_wheel_substance as sws

        a = {
            "terrain": {
                "terrain_kind": "hard",
                "mud_grade": "0",
                "mud_grade_label": "dry_hard",
                "wheel_grip": "1.000",
                "contact_avg": "1.000",
            }
        }
        b = {
            "terrain": {
                "terrain_kind": "mud",
                "mud_grade": "3",
                "mud_grade_label": "mud_deep",
                "wheel_grip": "0.024",
                "contact_avg": "0.345",
            }
        }
        changes = sws.diff_terrain_summary(a, b)
        keys = [c[0] for c in changes]
        self.assertIn("terrain_kind", keys)
        self.assertIn("mud_grade_label", keys)
        self.assertNotIn("wheel_grip", [c for c in keys if a["terrain"].get(c) == b["terrain"].get(c)])

    def test_diff_snapshots_key_offsets_only(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import scan_wheel_substance as sws

        a = {
            "wheels": [
                {
                    "floats": [
                        {"off": "+2FC", "f": 1.0},
                        {"off": "+010", "f": 9.9},
                    ]
                }
            ]
        }
        b = {
            "wheels": [
                {
                    "floats": [
                        {"off": "+2FC", "f": 0.02},
                        {"off": "+010", "f": 9.9},
                    ]
                }
            ]
        }
        changes = sws.diff_snapshots(a, b)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["off"], "+2FC")
        full = sws.diff_snapshots(a, b, key_offsets=())
        self.assertGreaterEqual(len(full), 1)


class TestLoadDetector(unittest.TestCase):
    def test_load_hint_vacio(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        self.assertEqual(mh._estimate_cargo_mass_kg([]), 0.0)
        self.assertTrue(mh._id_looks_like_trailer("s_trailer_scout_offroad"))
        self.assertFalse(mh._id_looks_like_cargo("s_scout_allterrain_chain_Ultima"))

    def test_wheel_addon_detection(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        self.assertTrue(mh._id_looks_like_wheel_addon("s_scout_allterrain_chain_Ultima", "s_chevrolet_ck1500"))
        self.assertTrue(mh._id_looks_like_wheel_addon("s_scout_offroad_OSI", "s_chevrolet_ck1500"))
        self.assertFalse(mh._id_looks_like_wheel_addon("s_chevrolet_ck1500", "s_chevrolet_ck1500"))
        self.assertFalse(mh._id_looks_like_wheel_addon("s_trailer_scout_offroad", "s_chevrolet_ck1500"))
        self.assertEqual(mh.classify_tire_kind("s_scout_allterrain_chain_Ultima"), "chain")
        self.assertEqual(mh.classify_tire_kind("s_scout_offroad_33"), "offroad")
        self.assertEqual(mh.classify_tire_kind("offroad_1"), "offroad")
        self.assertEqual(mh.classify_tire_kind("wheels_scout_offroad"), "offroad")
        self.assertEqual(mh.classify_tire_kind("highway_1_uhd"), "uhd")
        self.assertEqual(mh._tire_kind_from_ui_text("ma AT I"), "allterrain")
        self.assertEqual(mh._tire_kind_from_ui_text("33 OS I"), "offroad")
        kinds = [
            {"tire_kind": "offroad"},
            {"tire_kind": "offroad"},
            {"tire_kind": "offroad"},
        ]
        kind, mixed = mh._consensus_tire_kind(kinds)
        self.assertEqual(kind, "offroad")
        self.assertFalse(mixed)
        self.assertTrue(mh._id_looks_like_cargo("s_metal_planks_cargo"))
        self.assertTrue(mh._id_looks_like_cargo("cargo_service_spare_parts_1"))

    def test_estimate_service_spare_special(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        self.assertAlmostEqual(
            mh._estimate_cargo_mass_kg(["cargo_service_spare_parts_special_1"]),
            1200.0,
        )
        self.assertAlmostEqual(
            mh._estimate_cargo_mass_kg(["cargo_service_spare_parts_1"]),
            1200.0,
        )

    def test_is_ascii_game_id(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        self.assertTrue(mh._is_ascii_game_id("BoneCargo_1_cdt"))
        self.assertTrue(mh._is_ascii_game_id("cargo_service_spare_parts_1"))
        self.assertFalse(mh._is_ascii_game_id("\xff\xfe"))

    def test_payload_from_masses_fleetstar(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        # Havok vacio ~6947 kg vs XML 6650 + tara 400
        vacio = mh.payload_from_masses(6947, 6650)
        self.assertEqual(vacio["payload_kg"], 0.0)

        cargado = mh.payload_from_masses(12947, 6650)
        self.assertAlmostEqual(cargado["payload_kg"], 5897.0)

        trailer = mh.payload_from_masses(6947, 6650, trailer_mass_kg=3300, trailer_tare_kg=800)
        self.assertAlmostEqual(trailer["trailer_payload_kg"], 2400.0)
        self.assertEqual(trailer["payload_kg"], 2400.0)

    def test_load_hint_from_payload(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        self.assertEqual(
            mh._load_hint_from_payload(trailer_id="", truck_payload_kg=0, trailer_payload_kg=0),
            "vacio",
        )
        self.assertEqual(
            mh._load_hint_from_payload(trailer_id="", truck_payload_kg=6000, trailer_payload_kg=0),
            "cargado",
        )
        self.assertEqual(
            mh._load_hint_from_payload(
                trailer_id="s_trailer_scout", truck_payload_kg=0, trailer_payload_kg=2500
            ),
            "trailer_cargado",
        )

    def test_effective_packed_slots_from_bones(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        self.assertEqual(
            mh._effective_packed_slots(0, ["BoneCargo_0_cdt", "BoneCargo_1_cdt"]), 2
        )
        self.assertEqual(mh._effective_packed_slots(1, ["BoneCargo_0_cdt"]), 1)

    def test_load_latch_holds_cargado(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        mh._VEH_LOAD_LATCH.clear()
        veh = 0xABC
        loaded = {
            "load_hint": "cargado",
            "cargo_mass_kg": "1200",
            "packed_cargo_slots": "1",
            "packed_cargo_bones": "BoneCargo_1_cdt",
            "path_cargo_type": "",
            "attached_cargo_mass_kg": "",
            "frame_addon": "trucks_addons_frame_addon_sideboard_2",
            "empty_mass_kg": "6650",
            "total_mass_kg": "7850",
        }
        mh._apply_load_latch(veh, loaded)
        empty = {
            "load_hint": "vacio",
            "cargo_mass_kg": "0",
            "packed_cargo_slots": "",
            "packed_cargo_bones": "",
            "path_cargo_type": "",
            "attached_cargo_mass_kg": "",
            "frame_addon": "",
            "empty_mass_kg": "6650",
            "total_mass_kg": "6650",
        }
        held = mh._apply_load_latch(veh, empty)
        self.assertEqual(held["load_hint"], "cargado")
        self.assertEqual(held["cargo_mass_kg"], "1200")
        mh._VEH_LOAD_LATCH.clear()

    def test_frame_payload_from_path_without_slots(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        payload = mh._frame_payload_from_packed(
            0, "cargo_service_spare_parts_special_1"
        )
        self.assertAlmostEqual(payload, 1200.0)
        hint = mh._truck_payload_signal(
            trailer_id="",
            truck_payload_kg=0.0,
            frame_payload_kg=payload,
            path_cargo_type="cargo_service_spare_parts_special_1",
            packed_slots=0,
        )
        self.assertGreater(hint, mh.PAYLOAD_LOAD_THRESHOLD_KG)

    def test_sane_truck_mass_filters_glitches(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        self.assertTrue(mh._is_sane_truck_mass(7850.0, 6650.0))
        self.assertTrue(mh._is_sane_truck_mass(6650.0, 6650.0))
        self.assertFalse(mh._is_sane_truck_mass(3237.0, 6650.0))
        self.assertFalse(mh._is_sane_truck_mass(86178.0, 6650.0))

    def test_payload_from_cargo_ids_capped(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        spam = [f"cargo_service_spare_parts_{i}" for i in range(80)]
        self.assertLessEqual(mh._payload_from_cargo_ids(spam), mh.MAX_FRAME_PAYLOAD_KG)


class TestTurnMetrics(unittest.TestCase):
    def test_turn_metrics_straight(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        m = mh.turn_metrics_from_yaw(8.0, 0.0)
        self.assertEqual(m["yaw_rate_deg_s"], 0.0)
        self.assertEqual(m["turn_radius_m"], "")

    def test_turn_metrics_curving(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        m = mh.turn_metrics_from_yaw(10.0, 0.1)
        self.assertGreater(m["yaw_rate_deg_s"], 5.0)
        self.assertGreater(float(m["turn_radius_m"]), 0)

    def test_format_csv_row_includes_yaw(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        sample = mh.enrich_turn_fields(
            {
                "speed_kmh": 10.0,
                "vel_x": 1.0,
                "vel_y": 0.0,
                "vel_z": 2.0,
                "ang_yaw": 0.1,
                "pos_y": 0.0,
                "vehicle_id": "s_chevrolet_ck1500",
                "total_mass_kg": "1750",
                "payload_kg": "0",
                "load_hint": "vacio",
            }
        )
        row = mh.format_csv_row(1.0, sample)
        self.assertIn("terrain_map", mh.CSV_HEADER)
        self.assertIn("yaw_rate_deg_s", mh.CSV_HEADER)
        self.assertIn(",5.7", row)  # ~0.1 rad/s -> 5.73 deg/s

    def test_format_csv_row_terrain_map_column(self) -> None:
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cheat_engine"))
        import memoria_havok as mh

        sample = {
            "speed_kmh": 5.0,
            "vel_x": 0.0,
            "vel_y": 0.0,
            "vel_z": 0.0,
            "ang_yaw": 0.0,
            "pos_y": 68.0,
            "vehicle_id": "s_fleetstar_f2070a",
            "terrain_kind": "hard",
            "terrain_map": "mud",
            "pos_x": 500.0,
            "pos_z": -100.0,
        }
        row = mh.format_csv_row(0.0, sample)
        parts = row.strip().split(",")
        hdr = mh.CSV_HEADER.strip().split(",")
        self.assertEqual(parts[hdr.index("terrain_kind")], "hard")
        self.assertEqual(parts[hdr.index("terrain_map")], "mud")

    def test_yaw_note_parts_from_csv_row(self) -> None:
        from importar_ce_csv import _yaw_note_parts

        parts = _yaw_note_parts({"yaw_rate_deg_s": "12.5", "turn_radius_m": "8.2"})
        self.assertTrue(any(p.startswith("yaw_deg_s=") for p in parts))
        self.assertTrue(any(p.startswith("turn_r=") for p in parts))


class TestGrabarLive(unittest.TestCase):
    def test_format_live_line(self) -> None:
        from grabar_ce import format_live_line

        line = format_live_line(
            10.0,
            {
                "speed_kmh": "8.2",
                "terrain_kind": "mud",
                "wheel_grip": "0.013",
                "contact_avg": "0.21",
                "load_hint": "vacio",
                "total_mass_kg": "1780",
                "vehicle_id": "s_khan_39_marshall",
            },
        )
        self.assertIn("8.2 km/h", line)
        self.assertIn("mud", line)
        self.assertIn("vacio", line)

    def test_format_live_line_pos_y(self) -> None:
        from grabar_ce import format_live_line

        line = format_live_line(5.0, {"speed_kmh": "3", "terrain_kind": "mud", "pos_y": "-0.42"})
        self.assertIn("pos_y=-0.420", line)


class TestDriveState(unittest.TestCase):
    def test_truck_drive_catalog_hints_fleetstar(self) -> None:
        from datos.catalog_lookup import truck_drive_catalog_hints

        hints = truck_drive_catalog_hints("fleetstar")
        self.assertEqual(hints.get("diff_lock_catalog"), "Installed")
        self.assertIn("gearbox_awd_modifier_xml", hints)

    def test_fuel_rate_tracker(self) -> None:
        import memoria_havok as mh

        tr = mh.FuelRateTracker()
        self.assertEqual(tr.update(0.0, "100.0"), "")
        self.assertEqual(tr.update(0.5, "100.0"), "0.00")
        rate = tr.update(30.5, "99.0")
        self.assertTrue(rate)
        self.assertAlmostEqual(float(rate), 1.97, places=1)

    def test_format_csv_row_drive_columns(self) -> None:
        import memoria_havok as mh

        sample = {
            "speed_kmh": 0.0,
            "vel_x": 0.0,
            "vel_y": 0.0,
            "vel_z": 0.0,
            "ang_yaw": 0.0,
            "pos_y": 0.0,
            "diff_lock_live": "1",
            "awd_live": "1",
            "low_gear_live": "0",
            "throttle": "0.450",
            "engine_rpm": "1200",
            "fuel_rate_pct_min": "2.50",
            "map_name": "North Port",
            "level_id": "level_us_02_01",
        }
        row = mh.format_csv_row(1.0, sample)
        self.assertIn(",1,1,0,0.450,1200,2.50,North Port,level_us_02_01", row)
        self.assertIn("map_name", mh.CSV_HEADER)

    def test_idle_fuel_consumption_at_zero_throttle(self) -> None:
        from sim.core import ENGINE_I6, SURFACES, VEHICLE_I6, run_sim

        mud = next(s for s in SURFACES if s.name == "Barro")
        s = run_sim(VEHICLE_I6, ENGINE_I6, mud, 10.0, low_gear=True)
        self.assertGreater(s.state.fuel_used, 0.0)

    def test_aat8v_engine_maps_to_i6_sim(self) -> None:
        from camiones.ck1500.engines import AAT8V_ENGINE_XML, engine_for_ck1500
        from sim.core import ENGINE_I6

        self.assertIs(engine_for_ck1500("aat8v"), ENGINE_I6)
        self.assertIs(engine_for_ck1500("i6", AAT8V_ENGINE_XML), ENGINE_I6)

    def test_f1_asfalto_aat8v_protocol_exists(self) -> None:
        from telemetria import TEST_PROTOCOLS

        proto = next(p for p in TEST_PROTOCOLS if p.id == "f1_asfalto_aat8v")
        self.assertEqual(proto.engine_id, "aat8v")
        self.assertFalse(proto.diff_lock)
        self.assertEqual(proto.tire, "highway")


class TestCatalogLookup(unittest.TestCase):
    def test_setup_xml_marshall(self) -> None:
        from datos.catalog_lookup import setup_xml_from_catalog

        setup = setup_xml_from_catalog("marshall")
        self.assertEqual(setup.get("catalog_source"), "initial.pak.bak stock")
        self.assertEqual(setup.get("steer_speed_xml"), 0.03)
        self.assertEqual(setup.get("responsiveness_xml"), 0.6)
        self.assertIn("engine_responsiveness_xml", setup)
        self.assertEqual(setup.get("default_engine_xml"), "ru_scout_old_engine_0")
        self.assertIn("engine_socket_type_xml", setup)
        self.assertEqual(setup.get("default_gearbox_xml"), "g_scout_default")
        self.assertEqual(setup.get("gearbox_socket_type_xml"), "gearboxes_scouts")
        self.assertEqual(setup.get("gearbox_file_id_xml"), "gearboxes_scouts")
        self.assertEqual(setup.get("gearbox_first_gear_ang_vel_xml"), 3.0)
        self.assertIs(setup.get("gearbox_lower_gear_xml"), True)
        self.assertIs(setup.get("gearbox_high_gear_xml"), False)
        self.assertEqual(setup.get("suspension_socket_xml"), "s_khan_39_marshall")
        self.assertIn("suspension_strength_front_xml", setup)
        self.assertIn("suspension_strength_rear_xml", setup)

    def test_setup_xml_ck1500_suspension_strength(self) -> None:
        from datos.catalog_lookup import setup_xml_from_catalog

        setup = setup_xml_from_catalog("ck1500")
        self.assertEqual(setup.get("suspension_strength_front_xml"), 0.035)
        self.assertEqual(setup.get("suspension_strength_rear_xml"), 0.025)
        self.assertEqual(setup.get("suspension_damping_front_xml"), 0.2)
        self.assertEqual(setup.get("suspension_damping_rear_xml"), 0.35)
        self.assertEqual(setup.get("suspension_height_front_xml"), 0.065)
        self.assertEqual(setup.get("suspension_height_rear_xml"), 0.12)

    def test_setup_xml_mh9500_suspension_socket(self) -> None:
        from datos.catalog_lookup import setup_xml_from_catalog

        setup = setup_xml_from_catalog("mh9500")
        self.assertEqual(setup.get("suspension_socket_xml"), "s_gmc9500")
        self.assertIn("suspension_strength_front_xml", setup)

    def test_setup_xml_unknown_vehicle(self) -> None:
        from datos.catalog_lookup import setup_xml_from_catalog

        self.assertEqual(setup_xml_from_catalog("no_existe"), {})


if __name__ == "__main__":
    unittest.main()
