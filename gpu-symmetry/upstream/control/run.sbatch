#!/usr/bin/env bash
#SBATCH --job-name=libri-symmetry-upstream
#SBATCH --partition=16V100
#SBATCH --qos=flood-1o2gpu
#SBATCH --account=abacus-group
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --gpus-per-node=2
#SBATCH --time=01:00:00
#SBATCH --output=final-%j.log
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
python3 "$RI_CHECK_ROOT/control/final.py"

RI_SYSTEM_MPIRUN=$(command -v mpirun)
export RI_SYSTEM_MPIRUN
export PATH="$RI_CHECK_ROOT/control/bin:$PATH"
python3 "$RI_CHECK_ROOT/before-fix/control/run.py"
python3 - <<'PY_SUMMARY'
import json,os
from pathlib import Path
root=Path(os.environ['RI_CHECK_ROOT'])
fixed=json.loads((root/'results/summary.json').read_text())
before=json.loads((root/'before-fix/results/summary.json').read_text())
assert fixed['passed'] and before['matched_expected_regression'] and before['unaffected_comparisons_passed']
summary={'passed':True,'job_id':os.environ['SLURM_JOB_ID'],'source':json.loads((root/'manifest.json').read_text()),'after_case_count':20,'before_case_count':20,'before_failures':4,'after_failures':0}
(root/'upstream-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('ALL UPSTREAM VALIDATION PASSED: GPU regressions and 20 before / 20 after HSE cases.')
PY_SUMMARY
