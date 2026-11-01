#!/usr/bin/env python3
"""Inspect extracted Android ELF libraries and compare them with this build.

The extracted APK libraries are reference material only. This script never copies
or packages them; the APK continues to use freshly built project libraries.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import subprocess
import sys

EXPECTED = {
    "libdm.so",
    "libmain_hook.so",
    "libfile_redirect_hook.so",
    "libgsl_alloc_hook.so",
    "libhook_impl.so",
}


def run(*args: str) -> str:
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect(path: pathlib.Path, readelf: str) -> tuple[str, bool]:
    header = run(readelf, "-h", str(path))
    dynamic = run(readelf, "-d", str(path))
    notes = run(readelf, "-n", str(path))
    symbols = run(readelf, "--dyn-syms", "--wide", str(path))
    elf_class = re.search(r"Class:\s*(.+)", header)
    machine = re.search(r"Machine:\s*(.+)", header)
    needed = re.findall(r"Shared library: \[(.*?)\]", dynamic)
    soname = re.search(r"Library soname: \[(.*?)\]", dynamic)
    build_id = re.search(r"Build ID: (\S+)", notes)
    exports = []
    for line in symbols.splitlines():
        fields = line.split()
        if len(fields) >= 8 and fields[3] in {"FUNC", "OBJECT", "NOTYPE"} and fields[6] != "UND":
            exports.append(fields[7].split("@")[0])
    ok = bool(elf_class and "ELF64" in elf_class.group(1) and
              machine and "AArch64" in machine.group(1))
    lines = [
        f"FILE: {path}",
        f"SIZE: {path.stat().st_size}",
        f"SHA256: {sha256(path)}",
        f"ELF_CLASS: {elf_class.group(1).strip() if elf_class else 'unknown'}",
        f"MACHINE: {machine.group(1).strip() if machine else 'unknown'}",
        f"SONAME: {soname.group(1) if soname else '(none)'}",
        f"BUILD_ID: {build_id.group(1) if build_id else '(none)'}",
        "NEEDED: " + (", ".join(needed) if needed else "(none)"),
        "DEFINED_DYNAMIC_SYMBOLS:",
    ]
    lines.extend(f"  {name}" for name in sorted(set(exports)))
    lines.append(f"ARM64_VALID: {'yes' if ok else 'NO'}")
    return "\n".join(lines), ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readelf", required=True)
    parser.add_argument("--reference", default="vendor/decompiled-apk/arm64-v8a")
    parser.add_argument("--build", default="work/build-android")
    parser.add_argument("--report", default="work/logs/decompiled-elf-report.txt")
    args = parser.parse_args()

    reference = pathlib.Path(args.reference)
    build = pathlib.Path(args.build)
    report = pathlib.Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    failures = []
    sections = [
        "Extracted APK ELF inspection",
        "NOTE: reference binaries are not copied into the APK.",
        "Expected ABI: ELF64 / AArch64 (arm64-v8a)",
        "",
    ]

    for name in sorted(EXPECTED):
        path = reference / name
        if not path.is_file():
            failures.append(f"missing reference library: {path}")
            continue
        try:
            detail, valid = inspect(path, args.readelf)
            sections.append(detail)
            sections.append("")
            if not valid:
                failures.append(f"wrong ELF ABI: {path}")
        except subprocess.CalledProcessError as exc:
            sections.append(f"FAILED TO INSPECT {path}:\n{exc.stdout}")
            failures.append(f"readelf failed: {path}")

        candidates = list(build.rglob(name)) if build.exists() else []
        if candidates:
            sections.append(f"BUILD COMPARISON for {name}:")
            for candidate in candidates:
                sections.append(f"  built: {candidate}")
                sections.append(f"  built_sha256: {sha256(candidate)}")
                sections.append(f"  reference_sha256: {sha256(path)}")
                sections.append(f"  byte_identical: {'yes' if sha256(candidate) == sha256(path) else 'no'}")
        else:
            sections.append(f"BUILD COMPARISON for {name}: no same-name build output found")
        sections.append("")

    sections.append("RESULT: " + ("FAIL" if failures else "PASS"))
    if failures:
        sections.extend("ERROR: " + item for item in failures)
    report.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(report.read_text(encoding="utf-8"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
