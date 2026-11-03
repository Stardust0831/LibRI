# GPU input and cache regression tests

These tests reproduce two regressions in LibRI PR #17 at
`e529a9930e75391d2c4c0c9ae3f91a1aa45d69d9`:

- `minimal` supplies only the four maps required by each of the 18 contractions.
  Each CPU reference succeeds. The GPU path must also succeed, with residency
  both enabled and disabled; it must not read an unrelated `a0b0` map.
- `copy_c`, `copy_v`, `assignment`, and `free_reload` warm object A's resident
  cache, copy A to B, change B's inputs, then evaluate B followed by A. Both
  objects must match their own CPU references. `density` changes only D and
  provides a control for inputs outside the resident C/V cache.

The fixture uses real and complex double precision, unequal atom dimensions,
two periodic cells, and one or four OpenMP threads. Every test asserts normal
correctness; there are no expected-failure assertions. GPU errors are compared
with `256 * epsilon * (1 + abs(CPU reference))`.

## Build and run

Use a CUDA build of DDLA 0.0.4, LibComm, cereal, MPI, OpenMP, BLAS and LAPACK.
This branch uses PR #17's existing DDLA API; testing DDLA 0.0.6 is separate.

```sh
cmake -S unittests/gpu_regressions -B build-gpu-regressions \
  -DCMAKE_BUILD_TYPE=Release \
  -DLIBCOMM_ROOT=/path/to/LibComm -DCEREAL_ROOT=/path/to/cereal \
  -DDDLA_ROOT=/path/to/DDLA
cmake --build build-gpu-regressions --parallel 2 --verbose
ctest --test-dir build-gpu-regressions --verbose --output-on-failure
```

The default matrix has 48 tests and needs one GPU. To run a single reproducer:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  mpirun -np 1 build-gpu-regressions/gpu_regressions_real minimal off
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  mpirun -np 1 build-gpu-regressions/gpu_regressions_real copy_c on
```

Configure with `-DENABLE_MPI_REGRESSIONS=ON` to add four two-rank tests. These
need two visible GPUs. Only rank zero keeps an extra LRI copy before a collective
C update and V free/reload. A cache separation must not create an MPI context
on just one rank. CTest's timeout also detects a collective mismatch.

## Compare the same fixture before and after the fix

`LIBRI_ROOT` selects the tested headers independently from the test source:

```sh
git worktree add --detach ../libri-before e529a9930e75391d2c4c0c9ae3f91a1aa45d69d9
cmake -S unittests/gpu_regressions -B build-before \
  -DLIBRI_ROOT="$PWD/../libri-before" -DCMAKE_BUILD_TYPE=Release \
  -DLIBCOMM_ROOT=/path/to/LibComm -DCEREAL_ROOT=/path/to/cereal \
  -DDDLA_ROOT=/path/to/DDLA
cmake --build build-before --parallel 2 --verbose
ctest --test-dir build-before --verbose --output-on-failure
```

Use a separate `build-after` directory and point `LIBRI_ROOT` at the fixed tree.
Keep both build and CTest logs. The baseline must report real failures, while
the fixed version must satisfy the same assertions and tolerance.
