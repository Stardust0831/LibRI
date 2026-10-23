#!/usr/bin/env python3
"""Capture complete configure/build output for three LibRI source snapshots."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--libcomm-root", required=True, type=Path)
parser.add_argument("--cereal-root", required=True, type=Path)
parser.add_argument("--blas-library", required=True, type=Path)
parser.add_argument("--output-dir", type=Path,
                    help="Write a fresh comparison here, preserving the published logs")
args = parser.parse_args()
root = Path(__file__).resolve().parent
output_root = args.output_dir.resolve() if args.output_dir else root
output_root.mkdir(parents=True, exist_ok=True)
work = output_root / "work"
work.mkdir(exist_ok=False)  # Every capture starts from a clean build directory.
logs = output_root / "logs"
logs.mkdir(exist_ok=False)
transcript = logs / "full-transcript.log"
records = []


def capture(label, command):
    destination = logs / label
    destination.mkdir(parents=True)
    rendered = shlex.join([str(x) for x in command])
    (destination / "command.txt").write_text(rendered + "\n")
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with (destination / "output.log").open("wb") as output:
        process = subprocess.run(command, cwd=root, stdout=output, stderr=subprocess.STDOUT)
    (destination / "exit-code.txt").write_text(str(process.returncode) + "\n")
    with transcript.open("ab") as output:
        output.write(f"=== {label} ===\nStarted: {started}\n$ {rendered}\n".encode())
        output.write((destination / "output.log").read_bytes())
        output.write(f"\nExit code: {process.returncode}\n\n".encode())
    records.append({"step": label, "command": [str(x) for x in command],
                    "exit_code": process.returncode, "started_utc": started})
    print(f"{label}: exit code {process.returncode}", flush=True)
    return process.returncode


provenance = json.loads((root / "provenance.json").read_text())
for variant in ("parent", "before", "after"):
    archive = root / "source-archives" / f"{variant}.tar.gz"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == provenance["archive_sha256"][archive.name]
    destination = work / "sources" / variant
    destination.mkdir(parents=True)
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            path = Path(member.name)
            assert not path.is_absolute() and ".." not in path.parts
            assert member.isfile() or member.isdir()
        source.extractall(destination)

capture("environment/compiler", ["g++", "--version"])
capture("environment/mpi", ["mpicxx", "--showme:version"])
capture("environment/cmake", ["cmake", "--version"])
build = work / "build"
configuration = capture("configure", [
    "cmake", "-S", str(root / "control"), "-B", str(build),
    "-DSOURCES_ROOT=" + str(work / "sources"),
    "-DLIBCOMM_ROOT=" + str(args.libcomm_root.resolve()),
    "-DCEREAL_ROOT=" + str(args.cereal_root.resolve()),
    "-DTEST_BLAS=" + str(args.blas_library.resolve()),
])
if configuration:
    (logs / "results.json").write_text(json.dumps(records, indent=2) + "\n")
    raise SystemExit(configuration)

build_results = []
for variant in ("parent", "before", "after"):
    for suite in ("hartree", "lr"):
        target = f"{variant}_{suite}"
        status = capture(f"{variant}/{suite}", [
            "cmake", "--build", str(build), "--target", target, "--parallel", "2", "--verbose"
        ])
        result = {"variant": variant, "suite": suite,
                  "status": "BUILT" if status == 0 else "BUILD FAILED", "exit_code": status}
        executable = build / target
        if status == 0:
            assert executable.is_file()
            result["executable_size_bytes"] = executable.stat().st_size
            result["executable_sha256"] = hashlib.sha256(executable.read_bytes()).hexdigest()
        build_results.append(result)

shutil.copyfile(build / "compile_commands.json", logs / "compile_commands.json")
(logs / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
(logs / "results.json").write_text(json.dumps(build_results, indent=2) + "\n")
rows = ["| Source | Target | Actual build result | Exit code |", "| --- | --- | --- | ---: |"]
for result in build_results:
    rows.append(f"| {result['variant']} | {result['suite']} | {result['status']} | {result['exit_code']} |")
(logs / "RESULTS.md").write_text("\n".join(rows) + "\n")
print("\n".join(rows), flush=True)
# This exit code checks completion of the comparison; individual compiler
# outcomes are retained verbatim above and in each exit-code.txt.
raise SystemExit(0 if all((r["exit_code"] != 0) == (r["variant"] == "before") for r in build_results) else 1)
