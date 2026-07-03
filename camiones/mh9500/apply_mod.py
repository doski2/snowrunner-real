"""CLI: aplica mod solo al GMC MH9500."""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _ROOT)

from repack_pak import apply_mod, set_active_vehicles

if __name__ == "__main__":
    set_active_vehicles(["mh9500"])
    apply_mod()
