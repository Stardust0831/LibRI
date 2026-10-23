#!/usr/bin/env bash
#SBATCH --job-name=libri-fac-add-ds
#SBATCH --partition=16V100
#SBATCH --qos=flood-1o2gpu
#SBATCH --account=abacus-group
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --time=00:30:00
#SBATCH --output=validation-%j.log
#SBATCH --export=ALL

set -euo pipefail
export USER=${SLURM_JOB_USER:?}
export LOGNAME=$USER
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ri_run=$SLURM_SUBMIT_DIR
source "$ri_run/control/modules.sh"
source /opt/sai_config/mps_mapping.d/${SLURM_JOB_PARTITION}.bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export SLURM_EXPORT_ENV=ALL
export OMPI_MCA_plm_slurm_args=--external-launcher
export PRTE_MCA_plm_slurm_args=--external-launcher
ri_deps=/org/abacus-group/abacususer01/abacus_hse_gpu_experiment/runs/lcao-hse/exx-device-20261018-3
export LD_LIBRARY_PATH="$ri_deps/install/ddla/lib:${LD_LIBRARY_PATH:-}"
mkdir -p "$ri_run/results"
module -t list > "$ri_run/results/modules.txt" 2>&1
nvidia-smi -q > "$ri_run/results/gpu.txt"
mpicxx --version > "$ri_run/results/compiler.txt"
sha256sum "$ri_run/source.tar" > "$ri_run/results/source-sha256.txt"
cmake -S "$ri_run/control" -B "$ri_run/build" \
  -DRUN_ROOT="$ri_run" \
  -DLIBCOMM_ROOT="$ri_deps/build/hse-deps/libcomm" \
  -DCEREAL_ROOT="$ri_deps/build/hse-deps/cereal-install" \
  -DDDLA_ROOT="$ri_deps/install/ddla" \
  -DTEST_BLAS=/opt/devtools/saiblas/2603-gnu-avx2/lib/libopenblas.so \
  > "$ri_run/results/configure.log" 2>&1
cmake --build "$ri_run/build" --parallel 2 > "$ri_run/results/build.log" 2>&1
ri_failures=0
for ri_threads in 1 4; do
  export OMP_NUM_THREADS=$ri_threads
  for ri_backend in cpu gpu inrepo; do
    for ri_scalar in float double complex_float complex_double; do
      ri_case=${ri_backend}_${ri_scalar}
      if timeout 90s mpirun -np 1 --map-by "$MAP_OPT" "$ri_run/build/$ri_case" \
          > "$ri_run/results/$ri_case-omp$ri_threads.log" 2>&1; then
        echo "PASS $ri_case OMP=$ri_threads"
      else
        echo "FAIL $ri_case OMP=$ri_threads"
        ri_failures=$((ri_failures+1))
      fi
    done
  done
done
export OMP_NUM_THREADS=1
for ri_suite in contractions physics; do
  set +e
  timeout 90s mpirun -np 1 --map-by "$MAP_OPT" "$ri_run/build/negative_double" "$ri_suite" \
    > "$ri_run/results/negative-$ri_suite.log" 2>&1
  ri_status=$?
  set -e
  if [[ $ri_status -eq 1 ]] && grep -q 'Numerical comparison failed' "$ri_run/results/negative-$ri_suite.log"; then
    echo "PASS negative control: $ri_suite"
  else
    echo "FAIL negative control: $ri_suite status=$ri_status"
    ri_failures=$((ri_failures+1))
  fi
done
set +e
timeout 90s mpirun -np 1 --map-by "$MAP_OPT" "$ri_run/build/negative_inrepo" \
  > "$ri_run/results/negative-inrepo.log" 2>&1
ri_status=$?
set -e
if [[ $ri_status -eq 1 ]] && grep -q 'Accumulation differs from the CPU reference' "$ri_run/results/negative-inrepo.log"; then
  echo 'PASS negative control: inrepo'
else
  echo "FAIL negative control: inrepo status=$ri_status"
  ri_failures=$((ri_failures+1))
fi
echo "GPU_VALIDATION_FAILURES=$ri_failures"

# The branch also changes LRI_k. Check its existing tests against the parent.
for ri_variant in source baseline; do
  for ri_suite in hartree lr; do
    ri_case=${ri_variant}_${ri_suite}
    if cmake --build "$ri_run/build" --target "$ri_case" --parallel 2 \
        > "$ri_run/results/$ri_case-build.log" 2>&1; then
      echo "BUILD_PASS $ri_case"
      for ri_threads in 1 4; do
        export OMP_NUM_THREADS=$ri_threads
        if (cd "$ri_run/$ri_variant" && timeout 90s mpirun -np 1 --map-by "$MAP_OPT" \
            "$ri_run/build/$ri_case") > "$ri_run/results/$ri_case-omp$ri_threads.log" 2>&1; then
          echo "PASS $ri_case OMP=$ri_threads"
        else
          echo "FAIL $ri_case OMP=$ri_threads"
        fi
      done
    else
      echo "BUILD_FAIL $ri_case"
    fi
  done
done
echo VALIDATION_COMPLETE
test "$ri_failures" -eq 0
