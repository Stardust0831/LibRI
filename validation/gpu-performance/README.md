# LibRI PR #17: measured GPU performance

PR #17 improves repeated GPU contractions in the two synthetic workloads measured here. On the larger 24-atom workload with four physical CPU cores, the original PR improves default timings by 1.16–1.18× relative to its merge base; explicitly keeping C/V on the GPU improves them by 2.61–3.32×. The proposed correctness fixes retain the improvement. These are contraction timings, not whole ABACUS calculations.

All figures compare these exact source versions:

- Baseline: `a0661cbb4b4f89ceeb23e040d49accb00943093f`.
- PR #17: `e529a9930e75391d2c4c0c9ae3f91a1aa45d69d9`.
- Fixed: the PR head plus the three-file suggestion patch, SHA256 `f6c2c685c8767c4cf40660efe777604e9423a69cc525f016ce9957573d7c8a80`.

The hardware was one NVIDIA V100 16 GB, using CUDA and DDLA 0.0.4. All six real/complex executables were compiled with GCC 13.3 and identical `-O3 -DNDEBUG` flags. Runs used one MPI rank, one BLAS thread, and either one or four OpenMP threads bound to distinct physical cores within the scheduler allocation. The larger confirmation reused the exact executable and DDLA hashes from the first matrix.

## Measurement

Each input is a deterministic dense one-cell tensor set. C has shape `(auxiliary, orbitals, orbitals)` and is registered under both C labels using the same saved name; V has shape `(auxiliary, auxiliary)`. Four EXX contractions are evaluated together. C/V stay fixed while a fresh D map is supplied before every call, under one name shared by its four labels. D values are scaled by a known factor at each iteration so every output can be checked for linearity.

Each process makes one cold call, two warmup calls, and five measured calls. The cold call includes LibRI cache construction; CUDA runtime initialization and C/V setup occur beforehand. `cudaDeviceSynchronize()` brackets the `cal_loop3` timer. D generation/setter time, output checking, and process startup are excluded from that timer and retained separately in the raw logs. Each configuration has three independent process runs; variant order rotates between rounds. Tables report the median of the three run medians. Speedups are the median of the three within-round baseline/variant ratios, so they need not exactly equal the ratio of table medians.

The first fixture uses 16 atoms, 16 orbitals, and 64 auxiliary functions. Its baseline pilot gave 0.3211 s/call, so its size was retained. Because several resident calls were shorter than 0.15 s and showed jitter, a second 24-atom fixture was then run with four physical cores. Both complete matrices are retained; no further size sweep was performed.

## Larger confirmation: 24 atoms, 16 orbitals, 64 auxiliary functions

Median steady time per call, in seconds:

| Scalar | Baseline | PR default | PR resident | Fixed default | Fixed resident |
|---|---:|---:|---:|---:|---:|
| real | 0.643522 | 0.548421 | 0.231208 | 0.519355 | 0.203852 |
| complex | 1.228868 | 1.033810 | 0.370325 | 1.051796 | 0.369800 |

The complete ranges and cold timings are:

| Threads | Type | Version | Residency | Steady median (s) | 3-run median range (s) | Paired speedup | Cold median (s) |
|---:|---|---|---|---:|---:|---:|---:|
| 4 | real | master | False | 0.643522 | 0.594641–0.646260 | 1.000× | 0.656476 |
| 4 | real | pr17 | False | 0.548421 | 0.524797–0.557175 | 1.160× | 0.592293 |
| 4 | real | pr17 | True | 0.231208 | 0.214989–0.247201 | 2.614× | 0.453233 |
| 4 | real | pr17-suggestions | False | 0.519355 | 0.514368–0.557080 | 1.155× | 0.573745 |
| 4 | real | pr17-suggestions | True | 0.203852 | 0.186864–0.215652 | 3.170× | 0.410772 |
| 4 | complex | master | False | 1.228868 | 1.194990–1.232335 | 1.000× | 1.150947 |
| 4 | complex | pr17 | False | 1.033810 | 1.022866–1.039819 | 1.182× | 1.024176 |
| 4 | complex | pr17 | True | 0.370325 | 0.367573–0.380196 | 3.318× | 0.680035 |
| 4 | complex | pr17-suggestions | False | 1.051796 | 1.018560–1.059525 | 1.172× | 1.084471 |
| 4 | complex | pr17-suggestions | True | 0.369800 | 0.362277–0.381046 | 3.323× | 0.622794 |

The fixed and original PR run-median ranges overlap for every type/option in this larger fixture. There is no consistent timing penalty from the fix in these runs. The real resident medians differ, but this small sample does not establish that the correctness fix itself accelerates calculation. Copying an LRI object and replacing C/V is not timed here; detaching that cache can require another upload.

## Original matrix: 16 atoms, 16 orbitals, 64 auxiliary functions

| Threads | Type | Version | Residency | Steady median (s) | 3-run median range (s) | Paired speedup | Cold median (s) |
|---:|---|---|---|---:|---:|---:|---:|
| 1 | real | master | False | 0.386479 | 0.351820–0.412099 | 1.000× | 0.423500 |
| 1 | real | pr17 | False | 0.313489 | 0.310476–0.317812 | 1.216× | 0.355828 |
| 1 | real | pr17 | True | 0.089912 | 0.087013–0.142245 | 3.913× | 0.250804 |
| 1 | real | pr17-suggestions | False | 0.299538 | 0.292471–0.312853 | 1.290× | 0.346352 |
| 1 | real | pr17-suggestions | True | 0.093954 | 0.090037–0.094345 | 4.292× | 0.251687 |
| 1 | complex | master | False | 0.725810 | 0.675740–0.730735 | 1.000× | 0.811196 |
| 1 | complex | pr17 | False | 0.502472 | 0.469245–0.546493 | 1.454× | 0.541664 |
| 1 | complex | pr17 | True | 0.150743 | 0.117733–0.153050 | 4.848× | 0.326748 |
| 1 | complex | pr17-suggestions | False | 0.553017 | 0.534143–0.557928 | 1.312× | 0.559221 |
| 1 | complex | pr17-suggestions | True | 0.111479 | 0.110995–0.120930 | 6.062× | 0.264147 |
| 4 | real | master | False | 0.320230 | 0.261804–0.347434 | 1.000× | 0.331009 |
| 4 | real | pr17 | False | 0.205321 | 0.190573–0.263928 | 1.560× | 0.243687 |
| 4 | real | pr17 | True | 0.066590 | 0.063537–0.066695 | 4.809× | 0.170536 |
| 4 | real | pr17-suggestions | False | 0.228545 | 0.214190–0.264358 | 1.314× | 0.311335 |
| 4 | real | pr17-suggestions | True | 0.102440 | 0.062534–0.105903 | 3.392× | 0.194550 |
| 4 | complex | master | False | 0.473561 | 0.470159–0.485530 | 1.000× | 0.494338 |
| 4 | complex | pr17 | False | 0.374565 | 0.360253–0.446872 | 1.255× | 0.478742 |
| 4 | complex | pr17 | True | 0.107044 | 0.105731–0.128948 | 4.392× | 0.247495 |
| 4 | complex | pr17-suggestions | False | 0.372856 | 0.355658–0.427816 | 1.261× | 0.429325 |
| 4 | complex | pr17-suggestions | True | 0.133454 | 0.079521–0.142215 | 3.549× | 0.211167 |

The short resident calls show appreciable variability. Their individual samples and all three process-run medians are retained; small differences between the original and fixed versions should not be treated as measured optimization from the fix.

## Numerical validation and boundaries

The two matrices comprise 90 independent process runs and 450 measured steady calls, in addition to their cold/warmup calls. All passed. Full first and last output tensors were compared across versions, residency settings, repeats, and thread counts: 180 comparisons covering 16,711,680 scalar values. Maximum absolute difference from the baseline GPU outputs was 2.27377e-13; maximum error scaled by `1 + abs(reference)` was 6.5816e-16. Every D update also passed the independent linear-scaling check; maximum scaled error was 1.44352e-15. The predefined scaled tolerance was `1e-10`.

The resident variants explicitly call `set_gpu_resident_data_names({"C", "V"})`; this is an opt-in API configuration. These results do not mean that unmodified ABACUS uses it. This test measures synthetic dense EXX contractions with stable C/V, not the author’s 63-atom NV-diamond LR fixture, physical SCF convergence, or whole-application speedup. The main matrix uses one/four physical CPU cores, not the author’s six-thread configuration. It does not benchmark the cost of the copy-on-write correction or other density/key/shape update patterns.

## Reproduce a single invocation

The [driver](driver.cpp) and [CMake configuration](CMakeLists.txt) are standalone. For the exact source versions measured above, configure with CUDA and DDLA 0.0.4, plus LibComm, cereal, OpenBLAS and MPI:

```sh
cmake -S validation/gpu-performance -B build-gpu-performance \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG" \
  -DLIBRI_ROOT=/path/to/LibRI -DLIBCOMM_ROOT=/path/to/LibComm \
  -DCEREAL_ROOT=/path/to/cereal -DDDLA_ROOT=/path/to/ddla-0.0.4 \
  -DBLA_VENDOR=OpenBLAS -DBENCH_RESIDENCY=ON
cmake --build build-gpu-performance --parallel 2
```

Run inside an allocation with one GPU and four physical CPU cores. Each invocation should use a fresh working directory, because the driver saves its samples and complete first/last outputs there. For example:

```sh
OMP_NUM_THREADS=4 OMP_PLACES=cores OMP_PROC_BIND=close \
OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
mpirun -np 1 --bind-to core --map-by slot:PE=4 \
  /absolute/path/to/build-gpu-performance/benchmark_real 24 16 64 5 2 1
```

Arguments are atoms, orbitals, auxiliary functions, measured calls, warmup calls, and residency (0/1). Use `benchmark_complex` for complex tensors. Build the merge-base source with `BENCH_RESIDENCY=OFF` and pass residency 0; PR/fixed sources support both runtime settings. The full experiment used three independent rounds with rotated variant order; one invocation alone does not reproduce that statistical comparison.

## Evidence

The [raw log bundle](raw-logs.tar.gz) keeps all original configure/build/runtime logs, per-call CSV tables, result/comparison JSON files, source snapshots and manifests, exact commands, executable/DDLA hashes, GPU/affinity records and scheduler accounting. Logs are complete and unedited. Verify it with `sha256sum -c raw-logs.sha256` before extraction.

The bundle omits the large raw tensor dumps; `omitted-binary-outputs-sha256.json` indexes each omitted file by original path, byte size and SHA256. All 16,711,680 scalar values were compared using the full dumps before creating this compact bundle. The complete archive including those binary outputs is retained separately as `performance17-micro-evidence.tar.gz`, SHA256 `e3006300ec8342ce9321162d7ecf1361b596fe77b0a325a7289f817be8fe0ee4`.

After extraction, `performance17-micro-results-2153583/` holds the full 16-atom matrix and `performance17-micro-large-results-2153717/` the full 24-atom matrix. Each has `summary.json`, `results.json`, `comparisons.json`, and individual run directories. Both measurement jobs completed with exit status 0.

An initial harness compilation attempt failed because its output flattener treated `std::valarray` as if it had member `begin/end`; no timings ran in that attempt. The original source archive and failed log are preserved separately in the bundle. The indexed flattener was used in the subsequent successful identical Release builds. No LibRI source was changed for benchmarking.
