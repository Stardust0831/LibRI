#!/usr/bin/env python3
"""Keep complete compiler output for separate successful and failing examples."""

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--compiler", default="g++")
args = parser.parse_args()
root = Path(__file__).resolve().parent
version = subprocess.run([args.compiler, "--version"], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, check=True)
(root / "compiler.log").write_bytes(version.stdout)
results = []

for name in ("failure", "success", "range-for-reference"):
    case = root / name
    with tempfile.TemporaryDirectory(prefix="libri-collapse-example-") as directory:
        build = Path(directory)
        shutil.copyfile(case / "main.cpp", build / "main.cpp")
        command = [args.compiler, "-v", "-std=c++17", "-fopenmp", "main.cpp", "-o", "example"]
        (case / "compile-command.txt").write_text(shlex.join(command) + "\n")
        with (case / "compile.log").open("wb") as output:
            process = subprocess.run(command, cwd=build, stdout=output, stderr=subprocess.STDOUT)
        (case / "compile-exit-code.txt").write_text(str(process.returncode) + "\n")
        result = {"example": name, "compilation": "SUCCEEDED" if process.returncode == 0 else "FAILED",
                  "compile_exit_code": process.returncode, "execution": "NOT RUN"}
        if process.returncode == 0:
            assert (build / "example").is_file()
            (case / "run-command.txt").write_text("OMP_NUM_THREADS=2 ./example\n")
            with (case / "run.log").open("wb") as output:
                process = subprocess.run(["./example"], cwd=build, stdout=output, stderr=subprocess.STDOUT,
                                         env={**os.environ, "OMP_NUM_THREADS": "2"})
            (case / "run-exit-code.txt").write_text(str(process.returncode) + "\n")
            result["execution"] = "SUCCEEDED" if process.returncode == 0 else "FAILED"
            result["run_exit_code"] = process.returncode
        (case / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        results.append(result)
        print(json.dumps(result), flush=True)

(root / "results.json").write_text(json.dumps(results, indent=2) + "\n")
# Report compiler outcomes as recorded above; the failed example is never
# described as a successful compilation.
assert results[0]["compile_exit_code"] != 0
assert all(r["compile_exit_code"] == 0 and r["run_exit_code"] == 0 for r in results[1:])
