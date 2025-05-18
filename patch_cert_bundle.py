#!/usr/bin/env python3
"""
patch_cert_bundle.py
====================

Locate embedded PEM-encoded certificate bundles inside a binary and replace
them with a user-supplied bundle.  *Adjacent* bundles separated only by ASCII
whitespace are treated as **one logical bundle**.

**Default behaviour**: patch **all** bundles.  Use ``--index`` to limit which
ones are touched.

Usage
-----
```bash
# Patch all bundles
a python patch_cert_bundle.py -i firmware.bin -c new_roots.pem -o patched.bin

# Patch only the first and third bundles
a python patch_cert_bundle.py -i firmware.bin -c new.pem -o out.bin --index 0,2
```

Options
~~~~~~~
* ``--index LIST`` - comma-separated bundle numbers to patch (default: all).
* ``--strict`` - abort if the replacement is *shorter* than the original (no
  NUL-padding).  By default the script pads with ``0x00``.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple, Sequence

CERT_BEGIN = b"-----BEGIN CERTIFICATE-----"
CERT_END = b"-----END CERTIFICATE-----"
WHITESPACE = b" \t\r\n"  # ASCII whitespace bytes we ignore between bundles

# ---------------------------------------------------------------------------
# Scanning helpers
# ---------------------------------------------------------------------------

def _scan_single(data: bytes, pos: int) -> Tuple[int, int] | None:
    """Return *(start, end)* byte offsets of the bundle beginning at/after *pos*.

    Adjacent bundles separated only by ASCII whitespace are merged.
    Returns ``None`` if no BEGIN marker is found beyond *pos*.
    """
    start = data.find(CERT_BEGIN, pos)
    if start == -1:
        return None

    end = start
    while True:
        next_end = data.find(CERT_END, end)
        if next_end == -1:
            raise ValueError("Malformed bundle: BEGIN without matching END")
        end = next_end + len(CERT_END)

        # Eat trailing whitespace (spaces, tabs, CR, LF)
        while end < len(data) and data[end : end + 1] in WHITESPACE:
            end += 1

        # If another BEGIN follows immediately, keep consuming
        if data.startswith(CERT_BEGIN, end):
            continue
        return start, end


def find_all_bundles(data: bytes) -> List[Tuple[int, int]]:
    """Return list of *(start, end)* for every PEM bundle in *data*."""
    bundles: List[Tuple[int, int]] = []
    pos = 0
    while True:
        res = _scan_single(data, pos)
        if res is None:
            break
        start, end = res
        bundles.append((start, end))
        pos = end
    return bundles

# ---------------------------------------------------------------------------
# Patching logic
# ---------------------------------------------------------------------------

def _select_bundles(bundles: Sequence[Tuple[int, int]], indices: Sequence[int]) -> List[Tuple[int, int]]:
    """Return bundle slices for the requested *indices* (duplicates removed)."""
    selected: List[Tuple[int, int]] = []
    seen = set()
    for i in indices:
        if i < 0:
            idx = len(bundles) + i
        else:
            idx = i
        if idx < 0 or idx >= len(bundles):
            raise ValueError(
                f"Index {i} out of range – only {len(bundles)} bundle(s) present"
            )
        if idx not in seen:
            selected.append(bundles[idx])
            seen.add(idx)
    return selected


def patch_bundle(
    input_path: Path,
    cert_path: Path,
    output_path: Path,
    *,
    indices: List[int] | None = None,
    strict: bool = False,
) -> None:
    """Patch selected bundles in *input_path* with *cert_path* and write *output_path*."""
    blob = input_path.read_bytes()
    bundles = find_all_bundles(blob)
    if not bundles:
        raise ValueError("No certificate bundles found in input binary")

    # Determine which bundles to patch
    if indices is None:
        targets = bundles
    else:
        targets = _select_bundles(bundles, indices)

    replacement = cert_path.read_bytes()

    for idx, (start, end) in enumerate(targets):
        orig_len = end - start
        new = replacement
        if len(new) > orig_len:
            raise ValueError(
                f"Replacement bundle larger than original (target #{idx}): "
                f"{len(new)} > {orig_len} bytes"
            )
        if len(new) < orig_len:
            if strict:
                raise ValueError(
                    f"Replacement bundle smaller than original (target #{idx}) "
                    f"and --strict specified"
                )
            new += b"\x00" * (orig_len - len(new))
        blob = blob[:start] + new + blob[end:]
        print(
            f"Patched bundle #{idx} @0x{start:X}-0x{end:X} "
            f"with {len(replacement)} bytes (kept {orig_len})"
        )

    output_path.write_bytes(blob)
    print(
        f"→ {output_path} written: {len(targets)} of {len(bundles)} bundle(s) patched"
    )

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_indices(s: str) -> List[int]:
    """Parse a comma‑separated string into a list of ints."""
    try:
        return [int(tok.strip()) for tok in s.split(",") if tok.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--index expects comma‑separated integers") from exc


def _cli() -> None:
    p = argparse.ArgumentParser(
        description="Patch embedded PEM certificate bundle(s) in a binary"
    )
    p.add_argument("-i", "--input", required=True, help="Path to original binary")
    p.add_argument("-c", "--certs", required=True, help="Path to replacement PEM bundle")
    p.add_argument("-o", "--output", required=True, help="Path for patched binary")
    p.add_argument(
        "--index",
        type=_parse_indices,
        metavar="LIST",
        help="Comma‑separated bundle numbers to patch (default: all)",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Abort if replacement is shorter than original (no padding)",
    )

    args = p.parse_args()
    patch_bundle(
        Path(args.input),
        Path(args.certs),
        Path(args.output),
        indices=args.index,
        strict=args.strict,
    )

if __name__ == "__main__":
    _cli()

