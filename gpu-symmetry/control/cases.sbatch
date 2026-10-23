#!/usr/bin/env bash
#SBATCH --job-name=libri-symmetry-cases
#SBATCH --partition=16V100
#SBATCH --qos=flood-1o2gpu
#SBATCH --account=abacus-group
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --gpus-per-node=2
#SBATCH --time=01:00:00
#SBATCH --output=cases-%j.log
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
RI_SYSTEM_MPIRUN=$(command -v mpirun)
export RI_SYSTEM_MPIRUN
export PATH="$RI_CHECK_ROOT/control/bin:$PATH"
python3 "$RI_CHECK_ROOT/control/abacus_cases.py"
python3 - <<'PY_SUMMARY'
import json,os
from pathlib import Path
root=Path(os.environ['RI_CHECK_ROOT'])
comparison=json.loads((root/'results/abacus-cases/comparison.json').read_text())
assert comparison['passed']
steps=json.loads((root/'results/steps.json').read_text())
assert all(s['exit_code']==0 for s in steps if not s['name'].startswith(('baseline/label','backport/label')) and s['name']!='abacus/cases')
result={'passed':True,'initial_job':'1913058','cases_job':os.environ['SLURM_JOB_ID'],
        'initial_cases_failure':'Harness regex skipped host (no underscore); the missing case and remaining groups were subsequently run with an explicit all-case regex.',
        'steps':steps,'abacus_case_count':20,'comparisons':comparison['comparisons']}
(root/'results/summary.json').write_text(json.dumps(result,indent=2)+'\n')
print('ALL VALIDATION PASSED')
PY_SUMMARY
