#!/usr/bin/env python3
"""Record a minimal OpenMP collapse reproduction for GCC 13.3."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--compiler", default="g++")
args = parser.parse_args()
root = Path(__file__).resolve().parent
cases = (
    ("range_for.cpp", True),
    ("intervening_declaration.cpp", False),
    ("declarations_innermost.cpp", True),
)
lines = [
    "Minimal OpenMP collapse object-compilation reproduction",
    "Recorded at: " + datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "",
]
version = subprocess.run([args.compiler, "--version"], text=True, capture_output=True, check=True)
lines.extend(["$ " + shlex.join([args.compiler, "--version"]), version.stdout.rstrip(), ""])
matched = True

with tempfile.TemporaryDirectory(prefix="libri-collapse-evidence-") as build:
    for source, expected_success in cases:
        shutil.copyfile(root / source, Path(build) / source)
        output = Path(source).with_suffix(".o").name
        command = [args.compiler, "-std=c++17", "-fopenmp", "-c", source, "-o", output]
        result = subprocess.run(command, cwd=build, text=True, capture_output=True)
        lines.extend(["$ " + shlex.join(command), "stdout:", result.stdout.rstrip() or "(empty)",
                      "stderr:", result.stderr.rstrip() or "(empty)",
                      "Exit code: " + str(result.returncode)])
        actual_success = result.returncode == 0
        if actual_success:
            object_exists = (Path(build) / output).is_file()
            lines.append("Object file generated: " + str(object_exists).lower())
            matched = matched and object_exists
        expectation_matches = actual_success == expected_success
        matched = matched and expectation_matches
        lines.append("Expected on GCC 13.3: " + ("success" if expected_success else "failure"))
        lines.extend(["Matches expectation: " + str(expectation_matches).lower(), ""])

lines.append("All GCC 13.3 expectations matched: " + str(matched).lower())
transcript = "\n".join(lines) + "\n"
(root / "compilation.log").write_text(transcript)
print(transcript, end="")
raise SystemExit(0 if matched else 1)
