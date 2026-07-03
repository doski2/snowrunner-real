"""Tests CLI comparar_telemetria.py."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from comparar_telemetria import main
from test_telemetria import _example_session
from telemetria import save_session


class TestCompararTelemetriaCLI(unittest.TestCase):
    def test_main_missing_session_returns_1(self) -> None:
        self.assertEqual(main(["no_existe.json"]), 1)

    def test_main_with_session_ok(self) -> None:
        session = _example_session()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test_session.json")
            save_session(session, path)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main([path])
            self.assertEqual(code, 0)
            self.assertIn("COMPARACION JUEGO vs SIMULADOR", buf.getvalue())

    def test_list_empty_dir(self) -> None:
        with patch("comparar_telemetria.list_sessions", return_value=[]):
            self.assertEqual(main(["--list"]), 1)


if __name__ == "__main__":
    unittest.main()
