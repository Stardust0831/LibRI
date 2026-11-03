# Before and after: GPU input and copied-cache regressions

The same regression fixture was built and run against two header revisions:

- Before: `b61088028fc65749786e42097a68f2b792e85972`, which adds tests to
  PR #17's `e529a9930e75391d2c4c0c9ae3f91a1aa45d69d9` without changing headers.
- After: `32d6d32dd32f48c12d6971456fb531baef7b1b73`, which applies the three-file
  input/cache fix. The tests and numerical tolerance are unchanged.

Both versions were configured in fresh build directories with Release settings.
The runs used NVIDIA V100 16 GB GPUs, GCC 13.3, CUDA Toolkit 12.9, Open MPI 5.0.10,
and the DDLA 0.0.4 installation used for this PR's API. Real and complex double
precision and one/four OpenMP threads were tested. The default matrix uses one
GPU; the additional MPI tests use two ranks and two GPUs.

| Case | Configurations | Before | After |
|---|---:|---|---|
| Only required maps, residency off/on | 8 | 14 of 18 GPU contractions fail in every configuration; all CPU references succeed | All 18 contractions pass in all 8 configurations |
| Copy then replace C/V, copy assignment, or free/reload; residency on | 16 | All fail when reevaluating the original object | All pass against each object's own CPU reference |
| Same copy/update cases; residency off | 16 | All pass | All pass |
| Change only D after copying; residency off/on | 8 | All pass | All pass |
| Only rank zero retains an extra copy, then collective C update and V free/reload | 4 | All pass | All pass, without an MPI hang |
| **Total CTest cases** | **52** | **28 pass, 24 fail** | **52 pass** |

The minimal-input test checks all 18 contractions within each CTest case. These
are correctness results; CTest elapsed times are not performance measurements.

## Missing input: previously valid contractions throw

`real_minimal_off_omp1_mpi1` first evaluates each contraction on the CPU, using
only the input maps required by that contraction. Before the fix:

```text
CPU_REFERENCE_OK a1b1_a2b2
FAIL a1b1_a2b2 exception=unordered_map::at
CPU_REFERENCE_OK a1b2_a2b1
FAIL a1b2_a2b1 exception=unordered_map::at
...
minimal failures=14/18
```

After the fix:

```text
CPU_REFERENCE_OK a1b1_a2b2
PASS a1b1_a2b2 max_abs_error=0
CPU_REFERENCE_OK a1b2_a2b1
PASS a1b2_a2b1 max_abs_error=0
...
minimal failures=0/18
```

The call to `resident_for()` evaluated its `a0b0` argument before it could decide
that residency was disabled or the input was irrelevant. The fix looks up this
map only when residency is active and a requested contraction needs it.

## Copied cache: evaluating B changes A's answer

`real_copy_c_on_omp1_mpi1` warms A, copies it to B, replaces B's C tensors,
evaluates B, then evaluates A again. Before the fix, A's CPU tensors still have
their original values, but its shared GPU cache contains B's replacement:

```text
original-after-copy-update actual=17.856614884368764 expected=17.568977175689167 error=0.28763770867959693 tolerance=1.0555241474144831e-12
FAIL original-after-copy-update max_abs_error=1.2042265372824659
FAIL GPU result differs from the independent CPU calculation
```

After the fix, the same comparison reports:

```text
PASS original-after-copy-update max_abs_error=3.5527136788005009e-15
```

An LRI copy initially shares its resident cache. Replacing or freeing a resident
C/V input now separates that cache before changing it. The replacement cache
starts empty and shares the existing GPU/MPI context. This preserves the other
object's data without introducing a new MPI collective on only some ranks.
Changing D alone continues to reuse the resident C/V cache.

## Complete evidence

[raw-logs.tar.gz](raw-logs.tar.gz) contains the complete configure, verbose build,
and verbose CTest output for both versions, plus JUnit summaries, compiler/CUDA/
MPI and GPU details, loaded-library paths, source and executable hashes,
compile commands, runner scripts, and scheduler accounting. The original CTest
failures remain intact. `results-single/*-ctest.log` is the full test output;
CTest may shorten individual passing-test output in its JUnit files.

The single-GPU job was `2153425`; the two-GPU job was `2153582`. Both completed
with exit status zero because the runner records the baseline CTest failure
(exit code 8) and continues to the fixed version. Individual test outcomes are
preserved in the logs and `summary.json`; the tests do not invert expectations.

```text
SHA256(raw-logs.tar.gz)
a8d339d4216d16fcb81537ee8343bb89bd8c03af524819315217c6b51c85258a
```

The archive's `SHA256SUMS.json` covers each contained evidence file. The applied
source patch has SHA256
`f6c2c685c8767c4cf40660efe777604e9423a69cc525f016ce9957573d7c8a80`.
