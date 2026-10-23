# ABACUS end-to-end comparison before and after the LibRI symmetry fix

Original LibRI `f68342122e4d23007142028bf2d017ce026835eb` aborts in all four GPU RI runs with real-space symmetry enabled. Fixed LibRI `2781215e73813de9d58fc45a6087b7b857659f45` passes those four configurations. The other 16 configurations pass unchanged repository references in both versions.

The baseline was compiled independently from the same ABACUS source (`b30b66a5a333a2667d618932f8430a80dd92146a` plus the [test-only guard removal](../abacus-validation-only.patch)). Both LibRI versions receive the same [OpenMP compatibility patch](../move-declarations.patch). The baseline has none of the three symmetry-fix commits.

Inputs, structures, k-points, reference results and tolerance files are byte-identical to the fixed runs. The [input/reference hashes](results/input-reference-sha256.json) record all six fixture files per run. The 115 original LibRI headers are verified before applying the OpenMP patch; only its two `LRI_k` headers change. [Original header hashes](control/original-header-sha256.json), [applied patch log](control/apply-openmp-patch.log), [build header hashes](build-records/libri-header-sha256.json).

Each row below contains four calculations: real/complex RI tensors × one/two MPI ranks. All use `symmetry=1` and one OpenMP thread; two-rank GPU RI uses two GPUs. PASS means SCF convergence and successful repository reference checks.

| Solver / RI backend / real-space EXX symmetry | Before: `f683421` | After: `2781215` |
| --- | --- | --- |
| CPU ScaLAPACK / CPU RI / on | 4/4 PASS | 4/4 PASS |
| GPU cuSOLVER / CPU RI / on | 4/4 PASS | 4/4 PASS |
| GPU cuSOLVER / GPU RI / on | **4/4 abort with `std::invalid_argument`** | **4/4 PASS** |
| GPU cuSOLVER / CPU RI / off | 4/4 PASS | 4/4 PASS |
| GPU cuSOLVER / GPU RI / off | 4/4 PASS | 4/4 PASS |

The 16 configurations that complete in both versions also pass direct comparisons of their outputs. The Si fixture has symmetry-enforced zero forces. [Machine-readable outcomes and comparisons](results/summary.json).

## Complete original records

- [Full configuration](results/abacus/configure/output.log) and [full verbose compilation/linking](results/abacus/build/output.log), including BSE.
- [Version output](results/abacus/version/output.log), [build configuration](build-records/CMakeCache.txt), [compilation database](build-records/compile_commands.json) and [binary SHA-256](build-records/binary-sha256.txt).
- [All test inputs and calculation outputs](results/abacus-cases), [per-case test-driver output](results/autotest), [commands and exit codes](results/steps.json).
- [Real / 1 rank failure](results/autotest/real-mpi1/gpu_sym/output.log), [complex / 1 rank failure](results/autotest/complex-mpi1/gpu_sym/output.log), [real / 2 ranks failure](results/autotest/real-mpi2/gpu_sym/output.log), [complex / 2 ranks failure](results/autotest/complex-mpi2/gpu_sym/output.log).
- [Complete scheduler output](before-fix-1913589.log), [scheduler state](results/scheduler.txt) and [actual build/test script](control/run.py).
- [Previously recorded fixed-version runs](../README.md).

## Failure excerpt

The build path is abbreviated below; the complete original log is linked above.

```text
 Updating EXX terminate called after throwing an instance of 'std::invalid_argument'
  what():  label a0b0_a1b1 error in .../Filter_Atom_Symmetry.h line 49
```

All four GPU symmetry runs abort before a final energy is available. They are recorded as failed calculations; their expected failures make the regression-reproduction job succeed.

## Logs for each affected configuration

The original runs abort inside the symmetry callback. The matching fixed runs converge and pass all seven repository checks:

| RI tensors / MPI ranks | Before | After |
| --- | --- | --- |
| Real / 1 | [Exception and abort](results/autotest/real-mpi1/gpu_sym/output.log) | [Reference checks pass](https://github.com/Stardust0831/LibRI/blob/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi1/autotest.log#L29) |
| Complex / 1 | [Exception and abort](results/autotest/complex-mpi1/gpu_sym/output.log) | [Reference checks pass](https://github.com/Stardust0831/LibRI/blob/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi1/autotest.log#L41) |
| Real / 2 | [Exception and abort](results/autotest/real-mpi2/gpu_sym/output.log) | [Reference checks pass](https://github.com/Stardust0831/LibRI/blob/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/real-mpi2/autotest.log#L41) |
| Complex / 2 | [Exception and abort](results/autotest/complex-mpi2/gpu_sym/output.log) | [Reference checks pass](https://github.com/Stardust0831/LibRI/blob/11d8d5cafc22b23089c38024bbc8007a277ebd6c/gpu-symmetry/results/abacus-cases/complex-mpi2/autotest.log#L41) |

The [complete baseline case files](results/abacus-cases) and [complete fixed case files](../results/abacus-cases) contain all 20 configurations for each version.
