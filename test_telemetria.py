"""
Tests Fase 5: telemetria manual y comparacion con sim.

Ejecutar:
  python -m unittest test_telemetria -v
"""

from __future__ import annotations

import os
import tempfile
import unittest

from telemetria import (
    TelemetrySample,
    TelemetrySession,
    compare_session_to_sim,
    export_comparison_report,
    list_bineditor_guides,
    meta_from_protocol,
    save_session,
    session_from_dict,
    session_to_dict,
    TEST_PROTOCOLS,
)


def _example_session() -> TelemetrySession:
    protocol = TEST_PROTOCOLS[2]  # f2_barro_offroad
    meta = meta_from_protocol(protocol, "Michigan", "Ruta barro test")
    meta.id = "test_barro_offroad"
    return TelemetrySession(
        meta=meta,
        samples=[
            TelemetrySample(0.0, 0.0, "stuck"),
            TelemetrySample(10.0, 5.0),
            TelemetrySample(20.0, 18.0),
            TelemetrySample(30.0, 35.0),
        ],
    )


class TestSessionIO(unittest.TestCase):
    def test_roundtrip_json(self) -> None:
        session = _example_session()
        data = session_to_dict(session)
        restored = session_from_dict(data)
        self.assertEqual(restored.meta.id, session.meta.id)
        self.assertEqual(len(restored.samples), 4)

    def test_save_default_vehicle_subdir(self) -> None:
        session = _example_session()
        with tempfile.TemporaryDirectory() as tmp:
            import telemetria as tm

            old_dir = tm.TELEMETRY_DIR
            try:
                tm.TELEMETRY_DIR = tmp
                path = save_session(session)
                norm = path.replace("\\", "/")
                self.assertTrue(norm.endswith("ck1500/test_barro_offroad.json"), norm)
                from telemetria import load_session

                loaded = load_session(path)
                self.assertEqual(loaded.samples[2].speed_kmh, 18.0)
            finally:
                tm.TELEMETRY_DIR = old_dir

    def test_save_and_load(self) -> None:
        session = _example_session()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.json")
            save_session(session, path)
            from telemetria import load_session

            loaded = load_session(path)
            self.assertEqual(loaded.samples[2].speed_kmh, 18.0)


class TestCompareSim(unittest.TestCase):
    def test_compare_returns_rows(self) -> None:
        cmp = compare_session_to_sim(_example_session())
        self.assertEqual(cmp["sample_count"], 4)
        self.assertIn("mae_kmh", cmp)
        self.assertGreater(cmp["sim_v30_kmh"], 0)

    def test_offroad_barro_sim_moves(self) -> None:
        cmp = compare_session_to_sim(_example_session())
        self.assertGreater(cmp["sim_v30_kmh"], 10.0)

    def test_export_report(self) -> None:
        report = export_comparison_report([_example_session()])
        self.assertIn("comparisons", report)
        self.assertIn("segments", report["comparisons"][0])
        self.assertIn("bineditor_guides", report)

    def test_split_session_by_terrain(self) -> None:
        from telemetria import (
            TelemetrySample,
            TelemetrySession,
            compare_session_by_terrain,
            meta_from_protocol,
        )

        protocol = TEST_PROTOCOLS[2]
        meta = meta_from_protocol(protocol)
        meta.vehicle_id = "mh9500"
        samples = []
        for i in range(30):
            samples.append(TelemetrySample(i * 0.5, 5.0 + i * 0.1, "kind=mud", terrain_kind="mud"))
        for i in range(30, 60):
            samples.append(
                TelemetrySample(i * 0.5, 40.0 + (i - 30), "kind=hard", terrain_kind="hard")
            )
        session = TelemetrySession(meta=meta, samples=samples)
        report = compare_session_by_terrain(session)
        self.assertGreaterEqual(len(report["segments"]), 2)
        kinds = {s["terrain_kind"] for s in report["segments"]}
        self.assertIn("mud", kinds)
        self.assertIn("hard", kinds)


class TestProtocols(unittest.TestCase):
    def test_default_protocol_maps_cover_all_vehicles(self) -> None:
        from camiones.registry import VEHICLES
        from telemetria import (
            DEFAULT_ASPHALT_PROTOCOL,
            DEFAULT_LOADED_MUD_PROTOCOL,
            DEFAULT_MUD_PROTOCOL,
        )

        for vid in VEHICLES:
            self.assertIn(vid, DEFAULT_MUD_PROTOCOL)
            self.assertIn(vid, DEFAULT_ASPHALT_PROTOCOL)
            self.assertIn(vid, DEFAULT_LOADED_MUD_PROTOCOL)

    def test_protocol_phases_cover_core(self) -> None:
        phases = {p.phase for p in TEST_PROTOCOLS}
        self.assertTrue({1, 2, 3, 4}.issubset(phases))

    def test_auto_protocol_ck1500_mud(self) -> None:
        from telemetria import resolve_auto_protocol

        pid, _ = resolve_auto_protocol("s_chevrolet_ck1500", "mud", "0.013")
        self.assertEqual(pid, "f2_barro_offroad")

    def test_auto_protocol_mh9500_mud(self) -> None:
        from telemetria import resolve_auto_protocol

        pid, _ = resolve_auto_protocol("s_gmc_9500", "mud", "0.01")
        self.assertEqual(pid, "mh_f2_barro_offroad")

    def test_auto_protocol_fleetstar_hard(self) -> None:
        from telemetria import resolve_auto_protocol

        pid, _ = resolve_auto_protocol("international_fleetstar_f2070a", "hard", "0.95")
        self.assertEqual(pid, "fs_f1_asfalto")
        pid2, _ = resolve_auto_protocol("s_fleetstar_f2070a", "mud", "0.01")
        self.assertEqual(pid2, "fs_f2_barro_uhd")
        pid3, _ = resolve_auto_protocol("s_fleetstar_f2070a", "hard", "0.20", "hard", "0.804")
        self.assertEqual(pid3, "fs_f1_asfalto")

    def test_auto_protocol_marshall_mud(self) -> None:
        from telemetria import resolve_auto_protocol

        pid, _ = resolve_auto_protocol("s_khan_39_marshall", "mud", "0.05")
        self.assertEqual(pid, "km_f2_barro_tm2")
        pid2, _ = resolve_auto_protocol("khan_39_marshall", "hard", "0.85")
        self.assertEqual(pid2, "km_f1_asfalto")

    def test_auto_protocol_fleetstar_loaded_mud(self) -> None:
        from telemetria import LoadDetection, resolve_auto_protocol

        load = LoadDetection("cargado", 5900.0, True, "frame_cargado")
        pid, msg = resolve_auto_protocol(
            "s_fleetstar_f2070a", "mud", "0.01", "mud", load_detection=load
        )
        self.assertEqual(pid, "fs_f3_carga")
        self.assertIn("carga", msg)

    def test_detect_load_from_ce_rows(self) -> None:
        from telemetria import detect_load_from_ce_rows, resolve_protocol_from_ce_rows

        vacio_rows = [
            {
                "vehicle_id": "s_fleetstar_f2070a",
                "terrain_kind": "mud",
                "load_hint": "vacio",
                "payload_kg": "0",
            },
        ] * 20
        loaded_rows = [
            {
                "vehicle_id": "s_fleetstar_f2070a",
                "terrain_kind": "mud",
                "load_hint": "cargado",
                "payload_kg": "5900",
                "wheel_grip": "0.01",
            },
        ] * 20
        det_v = detect_load_from_ce_rows(vacio_rows, "fleetstar")
        self.assertFalse(det_v.loaded)
        det_l = detect_load_from_ce_rows(loaded_rows, "fleetstar")
        self.assertTrue(det_l.loaded)
        self.assertEqual(det_l.load_scenario_id, "frame_cargado")

        proto, _, _, load_det = resolve_protocol_from_ce_rows(loaded_rows)
        self.assertEqual(proto, "fs_f3_carga")
        self.assertTrue(load_det.loaded)

    def test_auto_protocol_unknown_vehicle(self) -> None:
        from telemetria import resolve_auto_protocol

        with self.assertRaises(ValueError):
            resolve_auto_protocol("s_unknown_truck", "mud")

    def test_bineditor_guides_list(self) -> None:
        guides = list_bineditor_guides()
        if os.path.isdir(
            r"C:\Program Files (x86)\Steam\steamapps\common\SnowRunner\Sources\BinEditor\Guides"
        ):
            self.assertIn("SnowRunner_Editor_Guide.pdf", guides)


if __name__ == "__main__":
    unittest.main()
