#!/usr/bin/env bash
#SBATCH --job-name=pr8169-merged-libri
#SBATCH --partition=16V100
#SBATCH --qos=flood-1o2gpu
#SBATCH --account=abacus-group
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --gpus-per-node=2
#SBATCH --time=01:00:00
#SBATCH --output=validation-%j.log
#SBATCH --export=ALL

set -euo pipefail
export USER=${SLURM_JOB_USER:?}
export LOGNAME=$USER
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export RI_CHECK_ROOT=$SLURM_SUBMIT_DIR
source "$RI_CHECK_ROOT/control/modules.sh"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export SLURM_EXPORT_ENV=ALL
export OMPI_MCA_plm_slurm_args=--external-launcher
export PRTE_MCA_plm_slurm_args=--external-launcher
ri_deps=/org/abacus-group/abacususer01/abacus_hse_gpu_experiment/runs/lcao-hse/exx-device-20261018-3
export LD_LIBRARY_PATH="$ri_deps/install/ddla/lib:${LD_LIBRARY_PATH:-}"
RI_SYSTEM_MPIRUN=$(command -v mpirun)
export RI_SYSTEM_MPIRUN
export PATH="$RI_CHECK_ROOT/control/bin:$PATH"
mkdir -p "$RI_CHECK_ROOT/results"
module -t list > "$RI_CHECK_ROOT/results/modules.txt" 2>&1
python3 "$RI_CHECK_ROOT/control/run.py"
