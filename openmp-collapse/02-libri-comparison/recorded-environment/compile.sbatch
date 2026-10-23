#!/usr/bin/env bash
#SBATCH --job-name=libri-collapse-build
#SBATCH --partition=16V100
#SBATCH --qos=flood-1o2gpu
#SBATCH --account=abacus-group
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gpus-per-node=1
#SBATCH --time=00:15:00
#SBATCH --output=build-%j.log
#SBATCH --export=ALL

set -euo pipefail
export USER=${SLURM_JOB_USER:?}
export LOGNAME=$USER
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ri_run=$SLURM_SUBMIT_DIR
source "$ri_run/modules.sh"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
ri_deps=/org/abacus-group/abacususer01/abacus_hse_gpu_experiment/runs/lcao-hse/exx-device-20261018-3
module -t list > "$ri_run/modules.log" 2>&1
python3 "$ri_run/run.py" \
  --libcomm-root "$ri_deps/build/hse-deps/libcomm" \
  --cereal-root "$ri_deps/build/hse-deps/cereal-install" \
  --blas-library /opt/devtools/saiblas/2603-gnu-avx2/lib/libopenblas.so
