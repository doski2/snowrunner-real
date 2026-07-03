"""Tests indexar_sesion.py."""

from __future__ import annotations

import os
import tempfile
import unittest

from telemetria import (
    TelemetrySample,
    TelemetrySession,
    meta_from_protocol,
    save_session,
    TEST_PROTOCOLS,
)
from indexar_sesion import (
    build_entries_from_session,
    index_session_path,
    merge_entries,
    remove_session_entries,
)


def _mixed_session() -> TelemetrySession:
    protocol = TEST_PROTOCOLS[2]
    meta = meta_from_protocol(protocol, "Michigan", "partida libre")
    meta.id = "test_index_mixed"
    meta.vehicle_id = "mh9500"
    meta.session_context = {
        "baseline_tag": "play_free_v1",
        "build_juego": "test-build",
        "mod_commit": "abc123",
        "setup": {"tire": "offroad"},
    }
    samples: list[TelemetrySample] = []
    for i in range(30):
        samples.append(
            TelemetrySample(i * 0.5, 5.0 + i * 0.1, "kind=mud", terrain_kind="mud")
        )
    for i in range(30, 60):
        samples.append(
            TelemetrySample(i * 0.5, 40.0 + (i - 30), "kind=hard", terrain_kind="hard")
        )
    return TelemetrySession(meta=meta, samples=samples)


class TestIndexarSesion(unittest.TestCase):
    def test_build_entries_session_and_segments(self) -> None:
        session = _mixed_session()
        entries = build_entries_from_session(session)
        self.assertGreaterEqual(len(entries), 3)
        types = {e["entry_type"] for e in entries}
        self.assertIn("session", types)
        self.assertIn("segment", types)
        sess = next(e for e in entries if e["entry_type"] == "session")
        self.assertEqual(sess["vehicle_id"], "mh9500")
        self.assertEqual(sess["baseline_tag"], "play_free_v1")
        self.assertIn("mud", sess["terrain_counts"])
        self.assertIsNotNone(sess.get("whole_mae_kmh"))
        segs = [e for e in entries if e["entry_type"] == "segment"]
        kinds = {s["terrain_kind"] for s in segs}
        self.assertIn("mud", kinds)
        self.assertIn("hard", kinds)
        for seg in segs:
            self.assertEqual(seg.get("whole_mae_kmh"), seg.get("mae_kmh"))

    def test_merge_entries_idempotent_without_reindex(self) -> None:
        session = _mixed_session()
        entries = build_entries_from_session(session)
        cal: dict = {"sessions": []}
        added1, _ = merge_entries(cal, entries, reindex=False)
        self.assertGreater(added1, 0)
        added2, _ = merge_entries(cal, entries, reindex=False)
        self.assertEqual(added2, 0)
        added3, _ = merge_entries(cal, entries, reindex=True)
        self.assertGreater(added3, 0)

    def test_index_session_path_dry_run(self) -> None:
        session = _mixed_session()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test_index_mixed.json")
            save_session(session, path)
            entries, added, _ = index_session_path(path, dry_run=True)
            self.assertGreater(len(entries), 0)
            self.assertEqual(added, len(entries))

    def test_remove_session_entries(self) -> None:
        cal = {
            "sessions": [
                {"session_id": "a", "entry_type": "session"},
                {"session_id": "a", "entry_type": "segment", "segment_id": "a__mud_0"},
                {"session_id": "b", "entry_type": "session"},
            ]
        }
        n = remove_session_entries(cal, "a")
        self.assertEqual(n, 2)
        self.assertEqual(len(cal["sessions"]), 1)


if __name__ == "__main__":
    unittest.main()
