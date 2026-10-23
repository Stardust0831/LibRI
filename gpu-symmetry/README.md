# LibRI GPU real-space symmetry: diagnosis and fix

The warning in [ABACUS PR #8169](https://github.com/deepmodeling/abacus-develop/pull/8169#issuecomment-6244851698) describes a reproducible LibRI bug. The GPU contraction order differs from the CPU order, but its symmetry callbacks were not consistently adapted to the atoms available at each stage.

The [repair branch](https://github.com/Stardust0831/LibRI/tree/fix/gpu-symmetry-filter), at `2781215e73813de9d58fc45a6087b7b857659f45`, is based on `fac_add_Ds` at `f68342122e4d23007142028bf2d017ce026835eb`. It backports maki49's [initial fix](https://github.com/maki49/LibRI/commit/2f77684417313e78e2da67aeee2ebf9b44f1e9fe) and [extension to all contraction labels](https://github.com/maki49/LibRI/commit/a0db48f56ffadf448c8057788df57562b42cd3c8), preserving authorship. It then corrects four further numerical failures exposed by an actual CPU/GPU contraction comparison.

## ABACUS before/after comparison

The [matched end-to-end comparison](before-fix/README.md) now includes 20 runs with the original LibRI revision and the same 20 configurations with the fix. All four GPU RI runs with real-space symmetry enabled abort before the fix with `std::invalid_argument` (`a0b0_a1b1`); all four pass after the fix. The other 16 controls pass unchanged repository references in both versions. The 16 controls also pass direct comparisons between the original and fixed versions. Inputs, references and tolerances are byte-identical. Complete baseline compilation and runtime logs accompany the comparison.

## Complete original logs

Compiler output and calculation outputs are preserved without truncation or path replacement. Excerpts follow below.

| Verification | Original record |
| --- | --- |
| Original LibRI GPU build | [configuration](results/baseline/configure/output.log), [full compilation](results/baseline/build/output.log), [all 18 individual runs](results/baseline/) |
| Two maintainer backports | [full compilation](results/backport/build/output.log), [all 18 individual runs](results/backport/) |
| Fixed CPU-only build | [full compilation](results/fixed-cpu/build/output.log), [1 thread](results/fixed-cpu/omp1/output.log), [4 threads](results/fixed-cpu/omp4/output.log) |
| Fixed DDLA/CUDA build | [full compilation](results/fixed-gpu/build/output.log), [1 thread](results/fixed-gpu/omp1/output.log), [4 threads](results/fixed-gpu/omp4/output.log) |
| C++11 callback regression | [compilation](results/callbacks/build/output.log), [run](results/callbacks/test/output.log) |
| Full ABACUS GPU executable, including BSE | [configuration](results/abacus/configure/output.log), [full verbose compilation/linking](results/abacus/build/output.log) |
| HSE real tensors, 1 MPI rank | [four initial variants](results/abacus-cases/real-mpi1/autotest.log), [remaining host baseline](results/abacus-cases/real-mpi1/autotest-resume.log) |
| HSE complex tensors, 1 MPI rank | [all five variants](results/abacus-cases/complex-mpi1/autotest.log) |
| HSE real tensors, 2 MPI ranks | [all five variants](results/abacus-cases/real-mpi2/autotest.log) |
| HSE complex tensors, 2 MPI ranks | [all five variants](results/abacus-cases/complex-mpi2/autotest.log) |
| Individual energy/force/stress comparisons | [comparison.json](results/abacus-cases/comparison.json) |
| Commands, exit codes and final outcome | [summary.json](results/summary.json), [scheduler states](results/scheduler.txt) |

The first job completed the builds, contraction tests and four HSE cases. Its postprocessing then failed because the integration harness's default case-name regex skipped `host`, which has no underscore. The follow-up used an explicit all-case regex, ran that missing baseline and the remaining 15 cases, and finished with exit `0:0`. The original failure is preserved in [the first job log](final-1913058.log); the [follow-up log](cases-1913206.log) records completion. No calculation reference or tolerance was changed.

## Causes

1. Six labels visit the intermediate atom `Aa01` before output atom `Aa2` is known. The old symmetry filter treats those calls as invalid and throws. The fix defers screening until the output atoms are known; returning `false` at the earlier stage means “do not skip this candidate.” Four additional labels call the atom/cell overload with output atom `Ab01`, which was also unsupported.
2. Four `a01b01_a2b2` labels pass `(Aa01, Ab01, Ab2)` to a callback that screens its first and third arguments. Their output is `(Aa01, Ab01)`, so they screen the intermediate `Ab2` instead. The backport fixes this argument order so the callback checks the output pair `(Aa01, Ab01)`.
3. Four `a01b2_a2b01` labels still screen `(Aa01, Aa2)` while summing over `Aa2`. Restricting an internal summation to the output sector discards valid contributions. The additional fix moves that check into the loop where `Ab01` is available and screens `(Aa01, Ab01)` instead.

The third defect is visible only after removing the earlier exception. A callback-only test cannot detect it because it does not execute the actual packing and contraction loops.

## Reproduction

The numerical regression uses two atoms with different tensor entries, three periodic cells, and an off-diagonal output pair with a nonzero relative translation. Its reference is an unrestricted CPU contraction followed by an independent mask on the final output keys. This detects missing contributions as well as extra output blocks.

| Code | 18 individual GPU contractions with symmetry |
| --- | --- |
| Original `f683421` | 10 abort with invalid-label exceptions, 4 return incorrect outputs, 4 pass |
| The two maki49 backports | 14 pass; 4 retain the intermediate-sum defect |
| Backports plus `2781215` | All 18 pass, as does their combined sum |

The remaining four labels were `a0b2_a2b0`, `a0b2_a2b1`, `a1b2_a2b0`, and `a1b2_a2b1`. The failing values differ by approximately 4.9–5.1 in the synthetic fixture, far above the numerical tolerance.

## Validation

- CPU-only and DDLA v0.0.4/CUDA builds on NVIDIA V100 with GCC 13.3/OpenMP.
- Both CPU implementations and the GPU implementation, using real and complex double tensors, with 1 and 4 OpenMP threads.
- All 18 labels and their combined sum; unrestricted, restricted, and empty output; seeded negative, zero, and fractional accumulation.
- Negative controls compile the same regression against the original headers and the two-backport version, reproducing the failures above.
- The standalone C++11 callback regression passes.

- Full ABACUS GPU compilation and linking, including BSE, passed.
- All 20 fixed-version HSE runs passed unchanged repository references: real/complex RI tensors × one/two MPI ranks × five solver/RI/symmetry combinations. The five combinations are a CPU solver with CPU RI, a GPU solver with CPU/GPU RI and real-space symmetry enabled, and a GPU solver with CPU/GPU RI and real-space symmetry disabled. Every case uses `symmetry=1` and `OMP_NUM_THREADS=1`.
- All 16 additional CPU/GPU comparisons passed. This two-atom Si case has zero force by symmetry; the synthetic contraction test provides the nontrivial tensor-level checks.
- CPU/GPU backend selections, real/complex selections and the real-space symmetry switch were checked in each emitted `INPUT.info`; every SCF calculation converged.

## Selected excerpts

Original `f683421`, contraction `a0b0_a1b1` ([complete output](results/baseline/label-16/output.log)):

```text
terminate called after throwing an instance of 'std::invalid_argument'
  what(): label a0b0_a1b1 error in .../Filter_Atom_Symmetry.h line 49
```

After the two maintainer fixes, contraction `a1b2_a2b1` still fails ([complete output](results/backport/label-01/output.log)):

```text
real label=a1b2_a2b1 sector=1 mode=2 atoms=1,0 cell=1 element=0 error=4.89589
real label=a1b2_a2b1 sector=1 mode=2: contraction differs from masked CPU reference
```

With the additional fix, all real/complex contractions and their sum pass in the [1-thread](results/fixed-gpu/omp1/output.log) and [4-thread](results/fixed-gpu/omp4/output.log) runs. The ABACUS follow-up ends with:

```text
PASS repository references: real-mpi1
PASS repository references: complex-mpi1
PASS repository references: real-mpi2
PASS repository references: complex-mpi2
PASS all 20 HSE symmetry runs and 16 component comparisons
ALL VALIDATION PASSED
```

## Scope

The repair branch fixes LibRI. The ABACUS integration experiment uses PR #8169 at `b30b66a5a` with only its GPU-symmetry rejection removed in an isolated test copy. The published ABACUS PR retains that rejection until its dependency and supported-scope changes are reviewed together.

The independent OpenMP declaration-movement patch remains necessary for the `LRI_k` headers when building ABACUS BSE with GCC 13.3. It is applied only to the validation copy and is not part of this symmetry fix. BSE numerical paths, MAGMA and multi-node execution were not validated here.

See the [standalone test commands](https://github.com/Stardust0831/LibRI/blob/2781215e73813de9d58fc45a6087b7b857659f45/unittests/gpu_symmetry/README.md).

[manifest.json](manifest.json) and [committed-source.json](committed-source.json) identify the exact tested source. [baseline.tar.gz](baseline.tar.gz), [backport.tar.gz](backport.tar.gz) and [fixed.tar.gz](fixed.tar.gz) preserve the three LibRI source snapshots. The [ABACUS test-only patch](abacus-validation-only.patch) reconstructs its isolated source changes from `b30b66a5a`; the large ABACUS source archive is not duplicated here. All 115 LibRI headers used in the ABACUS build match the fixed source plus the separately recorded [OpenMP patch](move-declarations.patch), as verified by [header hashes](build-records/libri-header-sha256.json).

[control](control/) contains the actual build and test scripts. [build-records](build-records/) contains CMake configuration, the full compilation database and executable hash. [SHA256SUMS.json](SHA256SUMS.json) covers the 978 raw evidence files, including the additional [before-fix records](before-fix/README.md). The numerical fixture and all three implementations were tested with identical compiler and dependency settings.
