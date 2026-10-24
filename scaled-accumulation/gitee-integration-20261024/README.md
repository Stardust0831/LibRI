# LibRI #15: Gitee implementation and regression results

[PR #15](https://github.com/abacusmodeling/LibRI/pull/15) incorporates [PeizeLin](https://github.com/PeizeLin)'s `fac_add_Ds` implementation at Gitee commit `6534722c2c4925d521793b3d279052ef3c7be886`. Its two commits retain their original author metadata and source hashes. The tested GitHub commit is `2cf829054e2bbbc3a5ebd2bb9e2bb6d38e6060fa`; all 153 archived files match that commit byte for byte.

The GPU path previously accumulated every contribution with coefficient 1. The fix applies `fac_add_Ds` during download, removes the unused GPU intermediate result, and uses the tensor scalar type for coefficients, including complex coefficients. The imported OpenMP loops also keep declarations inside the innermost collapsed loop.

Three further corrections were needed: copy a const tensor when initializing a unit-coefficient accumulator so later additions cannot mutate its input or another result; use `list_J.size()` for the Hartree loop that indexes `list_J`; and select `mu` from `list_I` in the CVC Hartree loop. All other production code matches the pinned Gitee implementation.

| Check | Outcome |
| --- | --- |
| CPU-only and DDLA/CUDA; float, double, complex float/double; 1 and 4 OpenMP threads | 16/16 runs pass, covering both CPU modes and GPU execution |
| All 18 contraction labels individually and combined; seeded/empty outputs; signed, zero, fractional and complex coefficients | Pass in all 16 runs |
| Existing Hartree reference, unequal/distinct atom lists, periodic contractions and exchange matrix/force/stress comparisons | 6/6 runs pass at 1 and 4 threads |
| Exact Gitee version with const-input and two atom-list regressions | All three expose the defects; the final version passes |
| GPU coefficient deliberately omitted | Accumulation regression detects the error |
| LR checked-in reference test | Fails before and after import; see comparison below |
| LR complete output compared against pre-import #15, written with 17-digit precision | Identical at both 1 and 4 threads (maximum difference 0) |
| Full ABACUS GPU build, including BSE | Pass with GCC 13.3/OpenMP |
| ABACUS HSE: gamma/one rank and complex multi-k/two ranks, four backend configurations each | 8/8 pass unchanged repository reference checks |

The ABACUS configurations are CPU solver/CPU RI, GPU solver/default RI, GPU solver/explicit CPU RI, and GPU solver/GPU RI. Effective backend selections are checked in `INPUT.info`. Hardware: NVIDIA V100-SXM2 16 GB GPUs with DDLA v0.0.4/CUDA. ABACUS is the unmodified `b30b66a5a333a2667d618932f8430a80dd92146a`, without extra LibRI patches. These runs do not test MAGMA, BSE numerical results or real-space EXX symmetry; the symmetry fix is separate in #16.

The existing LR reference stores nine decimal places in scientific notation. The pre-import and updated calculations both differ from it by up to `1.2500368e-7` per real/imaginary component, exceeding its `1e-7` absolute tolerance. Their 17-digit output is identical. Only diagnostic copies of the output writer use higher precision; the checked-in tests, reference files and tolerances are unchanged. The original failures remain recorded and are not counted as passing reference tests.

Original failure excerpts (paths abbreviated):

```text
# Gitee code, unequal Hartree atom lists:
Assertion '__n < this->size()' failed.

# Gitee code, distinct CVC atom lists:
map::at

# Gitee code, const input shared between accumulators:
Accumulating a const tensor changed its input or another result

# GPU coefficient omitted:
Accumulation differs from the CPU reference

# Existing LR reference test, both before and after import:
Assertion `std::abs(a.ptr()[i] - b.ptr()[i]) < REF_TOLERANCE' failed.
```

Complete original records:

- ABACUS: [configuration](results/abacus/configure/output.log), [full verbose compilation and linking](results/abacus/build/output.log), [version](results/abacus/version/output.log), [gamma results](results/scf_hse_gamma/autotest.log), [complex multi-k results](results/scf_hse_complex_multik_mpi2/autotest.log).
- Test compilation: [initial complete build](attempts/1919726/results/tests/build/output.log), [subsequent builds and raw attempts](attempts), [final build](results/tests/build/output.log), [all CPU/GPU results](results/tests).
- Negative controls: [Hartree](results/negative/hartree/output.log), [CVC](results/negative/cvc/output.log), [const input](results/negative/const-input/output.log), [unscaled GPU](results/negative/unscaled/output.log).
- LR: [original parent failure](results/tests/lr/reference/parent/omp1/output.log), [updated failure](results/tests/lr/reference/candidate/omp1/output.log), [one-thread comparison](results/tests/lr/comparison/omp1/output.log), [four-thread comparison](results/tests/lr/comparison/omp4/output.log), [complete numerical output](results/tests/lr/precise).
- [Commands and exit codes](results/steps.json), [summary with the LR limitation](results/summary.json), [scheduler outcome](results/scheduler.txt), [drivers and scripts](control), [compilation databases](build-records).
- [Source revisions and archive hashes](manifest.json), [authorship and appended commits](commits.txt), [tested archive/commit comparison](commit-verification.json), [runtime header hashes](results/libri-header-sha256.json), [file checksums](SHA256SUMS).
- Exact source archives: [pre-import #15](parent.tar.gz), [Gitee](gitee.tar.gz), [final #15](source.tar.gz).
