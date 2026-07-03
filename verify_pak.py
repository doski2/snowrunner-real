"""Verifica que initial.pak contiene los valores I6 del mod CK1500."""

from __future__ import annotations

import io
import sys
import zipfile

from repack_pak import PAK_OUT, PATCHES, split_zip_tail

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_patched_xml(pak_path: str) -> dict[str, str]:
    with open(pak_path, "rb") as f:
        zip_bytes, _ = split_zip_tail(f.read())
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        return {arc: zf.read(arc).decode("utf-8") for arc in PATCHES}


def verify_pak(pak_path: str | None = None) -> bool:
    path = pak_path or PAK_OUT
    try:
        blobs = load_patched_xml(path)
    except FileNotFoundError:
        print(f"FAIL archivo no encontrado: {path}")
        return False
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f"FAIL no se pudo leer {path}: {exc}")
        return False

    ok_all = True
    for arc, rules in PATCHES.items():
        text = blobs[arc]
        short = arc.rsplit("/", 1)[-1]
        for _old, new in rules:
            ok = new in text
            ok_all &= ok
            print(f"{'OK' if ok else 'FAIL'} [{short}] {new}")

    return ok_all


def main() -> None:
    if verify_pak():
        print("\nOK")
        return
    print("\nFAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()
