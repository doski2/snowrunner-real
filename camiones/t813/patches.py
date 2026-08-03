"""Parches XML Tatra T813 — solo masa (motor/neumáticos stock)."""

from __future__ import annotations

# Stock ~14021 kg; mod **14000 kg** (TE ~13800). Sin parches: masa catálogo ≈ objetivo mod.

PATCHES: dict[str, list[tuple[str, str]]] = {}
