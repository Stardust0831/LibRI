# ABACUS end-to-end comparison before and after the LibRI symmetry fix

Original LibRI `f68342122e4d23007142028bf2d017ce026835eb` aborts in all four GPU RI runs with real-space symmetry enabled. Fixed LibRI `2781215e73813de9d58fc45a6087b7b857659f45` passes those four configurations. The other 16 configurations pass unchanged repository references in both versions.

The baseline was compiled independently from the same ABACUS source (`b30b66a5a333a2667d618932f8430a80dd92146a` plus the [test-only guard removal](../abacus-validation-only.patch)). Both LibRI versions receive the same [OpenMP compatibility patch](../move-declarations.patch). The baseline has none of the three symmetry-fix commits.

Inputs, structures, k-points, reference results and tolerance files are byte-identical to the fixed runs. The [input/reference hashes](results/input-reference-sha256.json) record all six fixture files per run. The 115 original LibRI headers are verified before applying the OpenMP patch; only its two `LRI_k` headers change. [Original header hashes](control/original-header-sha256.json), [applied patch log](control/apply-openmp-patch.log), [build header hashes](build-records/libri-header-sha256.json).

Each row below contains four calculations: real/complex RI tensors × one/two MPI ranks. All use `symmetry=1` and one OpenMP thread; two-rank GPU RI uses two GPUs. After-version errors are relative to the CPU RI symmetry reference within each scalar/rank group.

| Configuration | Before: `f683421` | After: `2781215` | After: max abs ΔE (eV) | After: max abs ΔF (eV/Å) | After: max abs Δstress (kbar) |
| --- | --- | --- | ---: | ---: | ---: |
| CPU ScaLAPACK / CPU RI / symmetry on (`host`) | **4/4 PASS** | **4/4 PASS** | 3.41e-13 | 0 | 0 |
| GPU cuSOLVER / CPU RI / symmetry on (`cpu_sym`, reference) | **4/4 PASS** | **4/4 PASS** | — | — | — |
| GPU cuSOLVER / GPU RI / symmetry on (`gpu_sym`) | **0/4 PASS; 4 aborts** | **4/4 PASS** | 4.26e-13 | 0 | 0 |
| GPU cuSOLVER / CPU RI / symmetry off (`cpu_full`) | **4/4 PASS** | **4/4 PASS** | 4.55e-13 | 0 | 0 |
| GPU cuSOLVER / GPU RI / symmetry off (`gpu_full`) | **4/4 PASS** | **4/4 PASS** | 4.55e-13 | 0 | 0 |

Across the 16 configurations that complete in both versions, the maximum before/after energy difference is **6.54e-13 eV**. Force and stress components agree at printed precision. The Si fixture has symmetry-enforced zero forces. [Machine-readable before/after comparisons](results/summary.json).

## Complete original records

- [Full configuration](results/abacus/configure/output.log) and [full verbose compilation/linking](results/abacus/build/output.log), including BSE.
- [Version output](results/abacus/version/output.log), [build configuration](build-records/CMakeCache.txt), [compilation database](build-records/compile_commands.json) and [binary SHA-256](build-records/binary-sha256.txt).
- [All test inputs and calculation outputs](results/abacus-cases), [per-case test-driver output](results/autotest), [commands and exit codes](results/steps.json).
- [Real / 1 rank failure](results/autotest/real-mpi1/gpu_sym/output.log), [complex / 1 rank failure](results/autotest/complex-mpi1/gpu_sym/output.log), [real / 2 ranks failure](results/autotest/real-mpi2/gpu_sym/output.log), [complex / 2 ranks failure](results/autotest/complex-mpi2/gpu_sym/output.log).
- [Complete scheduler output](before-fix-1913589.log), [scheduler state](results/scheduler.txt) and [actual build/test script](control/run.py).
- [Previously recorded fixed-version runs](../README.md).

## Exact failure excerpt

```text
 Updating EXX terminate called after throwing an instance of 'std::invalid_argument'
  what():  label a0b0_a1b1 error in /org/abacus-group/abacususer01/abacus_hse_gpu_experiment/runs/lcao-hse/libri-gpu-symmetry-20261023/before-fix/libri/include/RI/physics/./symmetry/Filter_Atom_Symmetry.h line 49
```

All four GPU symmetry runs abort before a final energy is available. They are recorded as failed calculations; their expected failures make the regression-reproduction job succeed.

## Individual before/after energies

<details>
<summary>All 20 matched configurations: before/after energies and raw results</summary>

Each Before/After result links to the corresponding original inputs and outputs. PASS means SCF convergence and all seven repository checks passed. An abort produces no final energy; it is not assigned a numerical error of zero.

| RI tensors / MPI ranks | Configuration | Before: energy (eV) | After: energy (eV) | Before | After |
| --- | --- | ---: | ---: | --- | --- |
| Real / 1 | `host` | -189.44067551708753 | -189.44067551708753 | [PASS](results/abacus-cases/real-mpi1/tests/08_RI/host) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi1/tests/08_RI/host) |
| Real / 1 | `cpu_sym` | -189.44067551708753 | -189.44067551708767 | [PASS](results/abacus-cases/real-mpi1/tests/08_RI/cpu_sym) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi1/tests/08_RI/cpu_sym) |
| Real / 1 | `gpu_sym` | — (aborted) | -189.44067551708724 | [ABORT](results/abacus-cases/real-mpi1/tests/08_RI/gpu_sym) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi1/tests/08_RI/gpu_sym) |
| Real / 1 | `cpu_full` | -189.44067551708719 | -189.44067551708767 | [PASS](results/abacus-cases/real-mpi1/tests/08_RI/cpu_full) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi1/tests/08_RI/cpu_full) |
| Real / 1 | `gpu_full` | -189.44067551708767 | -189.44067551708775 | [PASS](results/abacus-cases/real-mpi1/tests/08_RI/gpu_full) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi1/tests/08_RI/gpu_full) |
| Complex / 1 | `host` | -189.44067551708764 | -189.44067551708764 | [PASS](results/abacus-cases/complex-mpi1/tests/08_RI/host) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi1/tests/08_RI/host) |
| Complex / 1 | `cpu_sym` | -189.44067551708767 | -189.44067551708753 | [PASS](results/abacus-cases/complex-mpi1/tests/08_RI/cpu_sym) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi1/tests/08_RI/cpu_sym) |
| Complex / 1 | `gpu_sym` | — (aborted) | -189.44067551708716 | [ABORT](results/abacus-cases/complex-mpi1/tests/08_RI/gpu_sym) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi1/tests/08_RI/gpu_sym) |
| Complex / 1 | `cpu_full` | -189.44067551708761 | -189.44067551708707 | [PASS](results/abacus-cases/complex-mpi1/tests/08_RI/cpu_full) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi1/tests/08_RI/cpu_full) |
| Complex / 1 | `gpu_full` | -189.44067551708747 | -189.44067551708707 | [PASS](results/abacus-cases/complex-mpi1/tests/08_RI/gpu_full) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi1/tests/08_RI/gpu_full) |
| Real / 2 | `host` | -189.44067551708804 | -189.44067551708804 | [PASS](results/abacus-cases/real-mpi2/tests/08_RI/host) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi2/tests/08_RI/host) |
| Real / 2 | `cpu_sym` | -189.44067551708807 | -189.44067551708770 | [PASS](results/abacus-cases/real-mpi2/tests/08_RI/cpu_sym) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi2/tests/08_RI/cpu_sym) |
| Real / 2 | `gpu_sym` | — (aborted) | -189.44067551708784 | [ABORT](results/abacus-cases/real-mpi2/tests/08_RI/gpu_sym) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi2/tests/08_RI/gpu_sym) |
| Real / 2 | `cpu_full` | -189.44067551708827 | -189.44067551708787 | [PASS](results/abacus-cases/real-mpi2/tests/08_RI/cpu_full) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi2/tests/08_RI/cpu_full) |
| Real / 2 | `gpu_full` | -189.44067551708795 | -189.44067551708795 | [PASS](results/abacus-cases/real-mpi2/tests/08_RI/gpu_full) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi2/tests/08_RI/gpu_full) |
| Complex / 2 | `host` | -189.44067551708761 | -189.44067551708761 | [PASS](results/abacus-cases/complex-mpi2/tests/08_RI/host) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi2/tests/08_RI/host) |
| Complex / 2 | `cpu_sym` | -189.44067551708798 | -189.44067551708784 | [PASS](results/abacus-cases/complex-mpi2/tests/08_RI/cpu_sym) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi2/tests/08_RI/cpu_sym) |
| Complex / 2 | `gpu_sym` | — (aborted) | -189.44067551708827 | [ABORT](results/abacus-cases/complex-mpi2/tests/08_RI/gpu_sym) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi2/tests/08_RI/gpu_sym) |
| Complex / 2 | `cpu_full` | -189.44067551708770 | -189.44067551708818 | [PASS](results/abacus-cases/complex-mpi2/tests/08_RI/cpu_full) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi2/tests/08_RI/cpu_full) |
| Complex / 2 | `gpu_full` | -189.44067551708832 | -189.44067551708767 | [PASS](results/abacus-cases/complex-mpi2/tests/08_RI/gpu_full) | [PASS](https://github.com/Stardust0831/LibRI/tree/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi2/tests/08_RI/gpu_full) |

</details>
