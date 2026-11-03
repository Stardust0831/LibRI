# ABACUS HSE calculations with LibRI PR #17

PR #17 reduces the measured EXX electronic and force stage times in the 64-atom
Si case. Whole-calculation times overlap across the three versions, so these
runs do not establish a consistent overall speedup. The 8-atom case also shows
no consistent overall improvement. Both cases converge to matching numerical
results with unchanged iteration counts.

## Results

Each entry reports three independent complete calculations, with version order
rotated between rounds. Wall times are median [minimum, maximum], in seconds.
Speedup is the median of the three within-round baseline/variant ratios; it is
not necessarily the ratio of the table medians. Stage times are medians from
ABACUS's own timers, in seconds.

| Case | Version | Wall time, s | Paired speedup | EXX electronic stage, s | EXX force stage, s |
|---|---|---:|---:|---:|---:|
| si8 | Baseline | 51.971 [50.696, 52.552] | 1.000× | 2.41 | 2.09 |
| si8 | PR #17 | 53.051 [50.897, 53.110] | 0.980× | 2.43 | 1.96 |
| si8 | PR #17 + fixes | 52.153 [50.611, 53.997] | 1.002× | 2.50 | 1.82 |
| si64 | Baseline | 274.950 [272.033, 282.271] | 1.000× | 22.32 | 26.23 |
| si64 | PR #17 | 275.704 [265.991, 277.405] | 1.024× | 19.06 | 24.24 |
| si64 | PR #17 + fixes | 266.594 [266.194, 276.119] | 1.022× | 19.10 | 23.77 |

The electronic timer is `Exx_LRI.cal_exx_elec`; it includes D setup,
communication and postprocessing as well as contractions. It is not a GPU
kernel timer. Force time is `Exx_LRI.cal_exx_force`. The report does not attribute
the remaining wall-time variation to any particular component.

All 18 measured calculations and three warmup calculations completed and
converged. The 12 candidate-to-baseline comparisons passed the predefined
limits of `1e-6 eV` for total energy and `1e-4 eV/Angstrom` for each force
component. Maximum observed differences in the recorded outputs were
`5.45697e-12 eV` and
`1e-10 eV/Angstrom`, respectively.
Every version used seven outer EXX steps; Si8 used 94 inner SCF iterations and
Si64 used 96. Baseline self-comparisons are also retained in the raw JSON.

## Conditions and scope

The runs used one NVIDIA V100 16 GB, four OpenMP threads pinned to distinct
physical CPU cores, one MPI rank and one BLAS thread. The two deterministic,
slightly distorted diamond structures used HSE, forces, a 60 Ry cutoff,
`scf_thr=1e-9`, `scf_ene_thr=1e-8` and disabled symmetry. Si8 used
`gamma_only=0` / `exx_real_number=0`, exercising complex representation at a
single Gamma point; Si64 used real representation with `gamma_only=1` /
`exx_real_number=1`. This is not finite-k, symmetry, multi-GPU or LR coverage.

All runs selected `device_exx gpu`. The matching ABACUS source routes that
option through `set_gpu` to `cal_loop3_GPU` without a CPU fallback on that
route. Recorded evidence includes the effective input, GPU compilation flags,
GPU process activity and the process's loaded DDLA library.

ABACUS did not call the new C/V residency API. These are default-path results;
the larger speedups from explicitly retaining C/V in the separate
[contraction benchmark](../README.md) cannot be applied to these whole-ABACUS
calculations. The correctness fixes also do not establish an additional
performance optimization from this small sample.

## Source and build identity

- ABACUS: `1bd79c473134b366fa45f422e0efd0c54491c43c`.
- LibRI baseline: `a0661cbb4b4f89ceeb23e040d49accb00943093f`.
- Original PR #17: `e529a9930e75391d2c4c0c9ae3f91a1aa45d69d9`.
- Fixed headers: the three-file change in `32d6d32dd32f48c12d6971456fb531baef7b1b73`,
  patch SHA256 `f6c2c685c8767c4cf40660efe777604e9423a69cc525f016ce9957573d7c8a80`.
- DDLA 0.0.4, CUDA Toolkit 12.9 and GCC 13.3; the same DDLA binary was used
  for all versions.

All builds used identical Release flags (`-O3 -DNDEBUG`). The 95 ABACUS
translation units depending on LibRI were rebuilt for each header revision;
853 unaffected link objects were reused. These are dependency rebuilds,
not three fresh full builds. Normalized compile and link commands match.
Binary/source/library hashes, commands and complete compiler output are
preserved in the bundle. Inputs, pseudopotential/orbital hashes and physical
CPU affinity match across variants and repetitions.

## Original logs

[raw-logs.tar.gz](raw-logs.tar.gz) contains the complete original compiler,
linker and runtime text logs, exact inputs, per-run results, numerical
comparisons, source/binary identities, GPU/affinity records, execution scripts
and scheduler accounting. Verify it using `sha256sum -c raw-logs.sha256`.

After extraction, `performance17-e2e-results-v3/summary.json` contains the
table data; its individual run directories contain `stdout.log`,
`OUT.bench/running_scf.log`, effective input, GPU observations and forces.
`performance17-e2e-control-v3/` holds the executed scripts.
`performance17-summarize-e2e.py` regenerates the summary from the recorded
measurements. The successful measurement job completed with exit status zero.

The compact bundle omits charge-density restart files, which were not used in
the energy/force comparisons. `evidence-package.json` records their sizes and
SHA256 hashes along with all included files. The full output archive is retained
separately as `performance17-e2e-evidence.tar.gz`, SHA256
`3f491c6c5116a6d434570e664a89c141406766bec3e30cf96e121a44de37d79e`. Executables and object files are not included.

Two preliminary harness failures are preserved: the first requested six
physical cores in a four-core allocation after successfully rebuilding the
baseline; the second completed one warmup but rejected the trailing comment
in `INPUT.info` with an overly strict parser. Neither supplies any measured
sample in the final matrix. The final run used a fresh output directory,
four physical cores and a token-aware parser.
