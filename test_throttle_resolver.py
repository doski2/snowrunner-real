"""Tests throttle_resolver (per-vehicle + auto-probe)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from cheat_engine.throttle_resolver import (
    auto_probe_throttle_spec,
    per_vehicle_specs,
    resolve_throttle_input_spec,
    save_per_vehicle_throttle,
)


class TestThrottleResolver(unittest.TestCase):
    def test_per_vehicle_specs(self) -> None:
        raw = {
            "per_vehicle": {
                "s_krs_58_bandit": {
                    "throttle_input": {"base": "tc+0E8", "offset": "+0x0C8", "kind": "u8"}
                }
            }
        }
        out = per_vehicle_specs(raw)
        self.assertEqual(out["s_krs_58_bandit"]["base"], "tc+0E8")

    def test_save_per_vehicle(self) -> None:
        ref: dict = {"drive_runtime": {}}
        spec = {"base": "tc+0F8", "offset": "+0x0C8", "kind": "u8"}
        save_per_vehicle_throttle(ref, "s_chevrolet_ck1500", spec)
        self.assertEqual(
            ref["drive_runtime"]["per_vehicle"]["s_chevrolet_ck1500"]["throttle_input"]["base"],
            "tc+0F8",
        )

    @patch("cheat_engine.throttle_resolver.mh.resolve_field_base_ptr")
    @patch("cheat_engine.throttle_resolver.mh.read_u8")
    def test_resolve_per_vehicle_first(self, read_u8, resolve_ptr) -> None:
        resolve_ptr.return_value = 0x1000
        read_u8.return_value = 0
        pv = {
            "s_chevrolet_ck1500": {
                "base": "tc+0F8",
                "offset": "+0x0C8",
                "kind": "u8",
            }
        }
        global_spec = {"base": "tc+0E8", "offset": "+0x0C8", "kind": "u8"}
        spec, src = resolve_throttle_input_spec(
            1,
            2,
            3,
            "s_chevrolet_ck1500",
            global_spec=global_spec,
            per_vehicle=pv,
            use_cache=False,
        )
        self.assertEqual(src, "per_vehicle")
        self.assertEqual(spec["base"], "tc+0F8")

    @patch("cheat_engine.throttle_resolver.enumerate_scan_targets")
    @patch("cheat_engine.throttle_resolver.mh.read_u8")
    def test_auto_probe_tc_child(self, read_u8, enum_targets) -> None:
        target = MagicMock()
        target.label = "tc+0F8"
        target.ptr = 0x2000
        target.scan_end = 0x600
        enum_targets.return_value = [target]
        read_u8.return_value = 128

        with patch("cheat_engine.throttle_resolver._spec_readable", return_value=True):
            spec = auto_probe_throttle_spec(1, 2, 3)
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec["base"], "tc+0F8")
        self.assertEqual(spec["offset"], "+0x0C8")


if __name__ == "__main__":
    unittest.main()
