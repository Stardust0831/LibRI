#!/usr/bin/env python3
"""Validate completeness and retain the numerical comparison results."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
pattern = re.compile(
    r"^PASS (\S+) mode=(\d+) elements=(\d+) max_abs=(\S+) max_scaled=(\S+)$",
    re.MULTILINE,
)
records = []
runs = []
for backend in ("cpu", "gpu"):
    for scalar in ("float", "double", "complex_float", "complex_double"):
        for threads in (1, 4):
            name = f"{backend}_{scalar}-omp{threads}.log"
            content = (root / "results" / name).read_text()
            matches = pattern.findall(content)
            modes = (0, 1) if backend == "cpu" else (0, 1, 2)
            assert len(matches) == 27 * len(modes), (name, len(matches))
            for mode in modes:
                assert sum(int(x[1]) == mode for x in matches) == 27, (name, mode)
            assert "Numerical comparison failed" not in content, name
            runs.append({"log": name, "modes": len(modes)})
            for test, mode, count, absolute, scaled in matches:
                records.append({"backend": backend, "scalar": scalar, "threads": threads,
                                "mode": int(mode), "test": test, "elements": int(count),
                                "max_absolute": float(absolute), "max_scaled": float(scaled)})

inrepo = []
for scalar in ("float", "double", "complex_float", "complex_double"):
    for threads in (1, 4):
        name = f"inrepo_{scalar}-omp{threads}.log"
        content = (root / "results" / name).read_text()
        modes = re.findall(r"Accumulation: all 18 contractions and their sum passed, mode=(\d+)", content)
        assert modes == ["0", "1", "2"], (name, modes)
        inrepo.append({"log": name, "modes": len(modes)})

negative = {}
for suite in ("contractions", "physics"):
    content = (root / "results" / f"negative-{suite}.log").read_text()
    assert "Numerical comparison failed" in content, suite
    negative[suite] = next(line for line in content.splitlines()
                           if "actual=" in line and "expected=" in line)
assert "Accumulation differs from the CPU reference" in (root / "results/negative-inrepo.log").read_text()
negative["inrepo"] = "unscaled accumulation rejected"

summary = {"commit": json.loads((root / "artifacts/source.json").read_text())["commit"],
           "external_runs": len(runs), "external_mode_combinations": sum(x["modes"] for x in runs),
           "inrepo_runs": len(inrepo), "inrepo_mode_combinations": sum(x["modes"] for x in inrepo),
           "checks": len(records), "element_checks": sum(x["elements"] for x in records),
           "negative_controls": negative, "records": records}
for case in ("source_hartree", "source_lr"):
    content = (root / "results" / f"{case}-build.log").read_text()
    assert content.count("error: not enough for loops to collapse") == 5, case
summary["lri_k"] = {
    "candidate_build": "Hartree and LR fail at five changed collapse loops under GCC 13.3/OpenMP",
    "baseline_build": "Both pass",
    "baseline_runtime": {
        "Hartree": "Passed with 1 and 4 OpenMP threads",
        "LR": "Existing reference-tolerance assertion fails with 1 and 4 OpenMP threads",
    },
    "static_index_findings": [
        {"file": "include/RI/ri/LRI_k-cal_cvc_mo.hpp", "line": 468,
         "actual": "const TA& mu = list_J[mu_index];",
         "expected": "const TA& mu = list_I[mu_index];"},
        {"file": "include/RI/ri/LRI_k-cal_hartree.hpp", "line": 125,
         "actual": "u_index < list_I.size() while indexing list_J[u_index]",
         "expected": "u_index < list_J.size()"},
    ],
}
(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "records"}, indent=2))
for scalar in ("float", "complex_float", "double", "complex_double"):
    for test in ("Exx-Hs", "Exx-energy", "Exx-dHs", "Exx-force", "Exx-stress", "Exx-density-update"):
        selected = [r for r in records if r["backend"] == "gpu" and r["mode"] == 2
                    and r["scalar"] == scalar and r["test"] == test]
        print(scalar, test, "max_abs=", max(x["max_absolute"] for x in selected),
              "max_scaled=", max(x["max_scaled"] for x in selected))
