# ABACUS #8169: upstream LibRI integration before release

ABACUS `1bd79c473134b366fa45f422e0efd0c54491c43c` accepts GPU RI with real-space EXX symmetry and updates its input test, help and installation guidance. LibRI is the exact merged upstream commit `a0661cbb4b4f89ceeb23e040d49accb00943093f`; neither source tree has additional patches.

The ABACUS PR remains a draft. LibRI `v0.2.1.1` does not contain the required fixes. This is development validation; the published LibRI release must be selected and validated before the PR is marked ready.

Hardware: NVIDIA V100-SXM2 16 GB GPUs, GCC 13.3/OpenMP and DDLA `v0.0.4`/CUDA. ABACUS runs use one OpenMP thread; selected LibRI tests also run with four threads.

| Validation | Result |
| --- | --- |
| Full ABACUS GPU compilation and linking, including BSE | Pass |
| ABACUS input tests, GPU RI enabled and disabled | 16/16 in each build |
| Version/info, parameter help/metadata and nine INPUT checks | Pass |
| CPU and GPU dependency consumers, including real/complex signed accumulation | All three CTest checks pass |
| HSE with real/complex RI tensors and one/two MPI ranks | 20/20 pass unchanged repository checks; 16/16 backend comparisons pass |
| LibRI symmetry: both CPU modes and GPU, all 18 labels and combined, selected/empty output and seeded accumulation | All four runs pass, at one and four threads |
| LibRI scalar accumulation: real/complex float/double, CPU/GPU, one/four threads | 16/16 pass |
| Hartree, distinct/unequal atom lists, exchange matrix/force/stress comparisons | 6/6 pass |
| C++11 symmetry callback build and assertions | Pass |

The five HSE configurations are CPU solver/CPU RI with symmetry, GPU solver/CPU RI with symmetry, GPU solver/GPU RI with symmetry, and GPU solver with either RI backend without symmetry. Each runs with real/complex tensors and one/two ranks. Effective INPUT settings are checked in the output. The fixture has zero forces by symmetry, so these runs do not establish nonzero-force behavior with symmetry enabled. BSE numerical results, MAGMA, NCCL and multi-node execution are not covered.

## Original logs and inputs

- ABACUS: [complete verbose build](results/abacus/build/output.log), [configure](results/abacus/configure/output.log), [version](results/abacus/version/output.log).
- Input tests: [GPU RI enabled](results/abacus/input-gpu/test/output.log), [GPU RI disabled](results/abacus/input-cpu/test/output.log), [CLI inputs and logs](results/cli).
- Dependency consumers: [CPU](results/consumer/cpu/test/output.log), [GPU](results/consumer/gpu/test/output.log).
- HSE: [real/one rank](results/abacus-cases/real-mpi1/autotest.log), [complex/one rank](results/abacus-cases/complex-mpi1/autotest.log), [real/two ranks](results/abacus-cases/real-mpi2/autotest.log), [complex/two ranks](results/abacus-cases/complex-mpi2/autotest.log), [all comparisons](results/abacus-cases/comparison.json).
- LibRI: [symmetry](results/symmetry), [accumulation](results/accumulation), [Hartree/atom-list/physics](results/physics), [callbacks](results/callbacks).
- [Every command and exit code](results/steps.json), [job completion](results/scheduler.txt), [raw job output](validation.log), [summary](results/summary.json), [build configuration and compile commands](build-records).
- [Source revisions and archive hashes](manifest.json), [actual LibRI header hashes](results/libri-header-sha256.json), [LibRI source archive](source.tar.gz), [ABACUS preparation diff](abacus-preparation.patch), [drivers](control), [file checksums](SHA256SUMS).

The full ABACUS source is available at [its exact commit](https://github.com/Stardust0831/abacus-develop/tree/1bd79c473134b366fa45f422e0efd0c54491c43c). The source archive checksum used for testing is recorded in the manifest. The [release checklist](RELEASE_CHECKLIST.md) records what remains before review.
