#!/usr/bin/env bash
#SBATCH --job-name=libri-pr15-diagnose
#SBATCH --partition=16V100
#SBATCH --qos=flood-1o2gpu
#SBATCH --account=abacus-group
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --gpus-per-node=2
#SBATCH --time=00:15:00
#SBATCH --output=diagnostic-%j.log
#SBATCH --export=ALL

set -euo pipefail
export USER=${SLURM_JOB_USER:?}
export LOGNAME=$USER
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export RI_CHECK_ROOT=$SLURM_SUBMIT_DIR
source "$RI_CHECK_ROOT/control/modules.sh"
source /opt/sai_config/mps_mapping.d/${SLURM_JOB_PARTITION}.bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export SLURM_EXPORT_ENV=ALL
export OMPI_MCA_plm_slurm_args=--external-launcher
export PRTE_MCA_plm_slurm_args=--external-launcher
ri_deps=/org/abacus-group/abacususer01/abacus_hse_gpu_experiment/runs/lcao-hse/exx-device-20261018-3
export LD_LIBRARY_PATH="$ri_deps/install/ddla/lib:${LD_LIBRARY_PATH:-}"
ulimit -c 0
python3 "$RI_CHECK_ROOT/control/diagnose.py"
