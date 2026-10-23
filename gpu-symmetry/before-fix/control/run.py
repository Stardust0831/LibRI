import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time


root = Path(os.environ['RI_CHECK_ROOT'])
work = root / 'before-fix'
out = work / 'results'
out.mkdir(exist_ok=True)
source = root / 'abacus-source'
deps = Path('/org/abacus-group/abacususer01/abacus_hse_gpu_experiment/runs/lcao-hse/exx-device-20261018-3')
build = work / 'abacus-build'
binary = build / 'abacus_std_gpu'
steps = []


def run(name, command, cwd=work, env=None, required=True, timeout=None):
    command = list(map(str, command))
    directory = out / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'command.txt').write_text(shlex.join(command) + '\n')
    print('START', name, flush=True)
    started = time.time()
    with (directory / 'output.log').open('wb') as stream:
        process = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                 stderr=subprocess.STDOUT, timeout=timeout)
    (directory / 'exit-code.txt').write_text(str(process.returncode) + '\n')
    step = {'name': name, 'command': command, 'cwd': str(cwd),
            'exit_code': process.returncode, 'elapsed_seconds': time.time() - started}
    steps.append(step)
    (out / 'steps.json').write_text(json.dumps(steps, indent=2) + '\n')
    print('END', name, process.returncode, flush=True)
    if required and process.returncode != 0:
        raise RuntimeError('Failed: ' + name)
    return process.returncode, directory / 'output.log'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def values(path):
    text = path.read_text()
    number = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?'
    energies = re.findall(r'!FINAL_ETOT_IS\s+(' + number + r')\s+eV', text)
    assert len(energies) == 1 and '#SCF IS CONVERGED#' in text, path
    force = text.split('#TOTAL-FORCE (eV/Angstrom)#')[1].split('#TOTAL-STRESS')[0]
    force_rows = re.findall(r'^\s*[A-Z][a-z]?\d+\s+(' + number + r')\s+('
                            + number + r')\s+(' + number + r')\s*$', force, re.M)
    stress = text.split('#TOTAL-STRESS (kbar)#')[1].split('#TOTAL-PRESSURE')[0]
    stress_rows = re.findall(r'^\s*(' + number + r')\s+(' + number + r')\s+('
                             + number + r')\s*$', stress, re.M)
    assert len(force_rows) == 2 and len(stress_rows) == 3, path
    result = {'energy_ev': [float(energies[0])],
              'force_ev_angstrom': [float(v) for row in force_rows for v in row],
              'stress_kbar': [float(v) for row in stress_rows for v in row]}
    assert all(math.isfinite(v) for vals in result.values() for v in vals), path
    return result


run('environment/compiler', ['mpicxx', '--version'])
run('environment/gpu', ['nvidia-smi', '-q'])
run('abacus/configure', ['cmake', '-S', source, '-B', build,
    '-G', 'Unix Makefiles', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
    '-DENABLE_LIBXC=ON', '-DENABLE_LIBRI=ON', '-DENABLE_LIBRI_GPU=ON',
    '-DENABLE_ELPA=OFF', '-DENABLE_NCCL_PARALLEL_DEVICE=OFF', '-DBUILD_TESTING=OFF',
    '-DGIT_SUBMODULE=OFF', '-DCMAKE_CUDA_ARCHITECTURES=70',
    '-DUSE_CUDA=ON', '-DUSE_CUDA_MPI=ON', '-DENABLE_CUSOLVERMP=ON', '-DENABLE_CUBLASMP=ON',
    f'-DLIBRI_DIR={work}/libri', f'-DLIBCOMM_DIR={deps}/build/hse-deps/libcomm',
    f'-Dcereal_DIR={deps}/build/hse-deps/cereal-install/lib/cmake/cereal',
    f'-DDDLA_ROOT={deps}/install/ddla'])
run('abacus/build', ['cmake', '--build', build, '--target', 'abacus_std_gpu',
                     '--verbose', '--parallel', '12'])
run('abacus/version', [binary, '--version'])
run('abacus/help', [binary, '-h', 'device_exx'])
records = work / 'build-records'
records.mkdir(exist_ok=True)
for name in ['CMakeCache.txt', 'compile_commands.json']:
    shutil.copy2(build / name, records / name)
(records / 'binary-sha256.txt').write_text(digest(binary) + '  abacus_std_gpu\n')
headers = {str(p.relative_to(work / 'libri')): digest(p)
           for p in sorted((work / 'libri/include').rglob('*')) if p.is_file()}
(records / 'libri-header-sha256.json').write_text(json.dumps(headers, indent=2) + '\n')

variants = ['host', 'cpu_sym', 'gpu_sym', 'cpu_full', 'gpu_full']
input_files = ['INPUT', 'STRU', 'KPT', 'result.ref', 'threshold', 'README']
checks_expected = {'etotref', 'etotperatomref', 'totalforceref', 'totalstressref',
                   'pointgroupref', 'spacegroupref', 'nksibzref'}
fixed = json.loads((root / 'results/abacus-cases/comparison.json').read_text())
all_cases = {}
comparisons = []
input_hashes = {}
for ranks in (1, 2):
    for scalar in ['real', 'complex']:
        group = f'{scalar}-mpi{ranks}'
        tests = out / 'abacus-cases' / group / 'tests'
        suite = tests / '08_RI'
        suite.mkdir(parents=True, exist_ok=True)
        for name in ['PP_ORB', 'integrate']:
            (tests / name).symlink_to(source / 'tests' / name)
        all_cases[group] = {}
        for variant in variants:
            case = suite / variant
            case.mkdir()
            original = root / 'results/abacus-cases' / group / 'tests/08_RI' / variant
            for name in input_files:
                shutil.copy2(original / name, case / name)
                assert digest(original / name) == digest(case / name)
                input_hashes[f'{group}/{variant}/{name}'] = digest(case / name)
            (suite / 'CASES.one.txt').write_text(variant + '\n')
            env = {**os.environ, 'RI_TEST_RANKS': str(ranks)}
            command = ['bash', tests / 'integrate/Autotest.sh', '-a', binary,
                       '-n', str(ranks), '-o', '1', '-f', 'CASES.one.txt', '-r', '.*']
            code, log = run(f'autotest/{group}/{variant}', command, cwd=suite,
                            env=env, required=False, timeout=180)
            shutil.copy2(suite / 'test.sum', case / 'test.sum')
            text = re.sub(r'\x1b\[[0-9;]*m', '', log.read_text())
            assert re.findall(r'\[ RUN\s*\]\s*(\w+)\n', text) == [variant]
            passed_checks = sorted(set(re.findall(r'\[\s*OK\s*\]\s*(\w+)', text)))
            info = (case / 'OUT.autotest/INPUT.info').read_text()
            for key in ['device', 'ks_solver', 'device_exx', 'exx_symmetry_realspace', 'exx_real_number']:
                pattern = r'(?m)^\s*' + key + r'\s+(\S+)'
                before = re.search(pattern, info)
                after = re.search(pattern, (original / 'OUT.autotest/INPUT.info').read_text())
                assert before and after and before[1] == after[1], (group, variant, key)
            scf = case / 'OUT.autotest/running_scf.log'
            scf_text = scf.read_text()
            record = {'harness_exit_code': code,
                      'converged': '#SCF IS CONVERGED#' in scf_text,
                      'reference_checks': passed_checks,
                      'repository_passed': code == 0 and set(passed_checks) == checks_expected,
                      'numerical_result': None,
                      'exception': None}
            error = re.search(r'label \S+ error in [^\r\n]*Filter_Atom_Symmetry.h[^\r\n]*', text)
            if error:
                record['exception'] = error[0]
            if record['converged']:
                record['numerical_result'] = values(scf)
                delta = {key: max(abs(a - b) for a, b in zip(vals, fixed['cases'][group][variant][key]))
                         for key, vals in record['numerical_result'].items()}
                limits = {'energy_ev': 1e-6, 'force_ev_angstrom': 1e-4, 'stress_kbar': 1e-3}
                comparisons.append({'group': group, 'variant': variant,
                                    'reference': 'fixed ' + variant,
                                    'max_errors': delta,
                                    'passed': all(delta[key] <= limit for key, limit in limits.items())})
            all_cases[group][variant] = record
            (out / 'case-results.json').write_text(json.dumps(all_cases, indent=2) + '\n')
        for name in ['PP_ORB', 'integrate']:
            (tests / name).unlink()

expected = all(
    (not record['converged'] and not record['repository_passed']
     and record['exception'] is not None and record['harness_exit_code'] != 0)
    if variant == 'gpu_sym' else (record['converged'] and record['repository_passed'])
    for cases in all_cases.values() for variant, record in cases.items())
summary = {'baseline_commit': 'f68342122e4d23007142028bf2d017ce026835eb',
           'fixed_commit': '2781215e73813de9d58fc45a6087b7b857659f45',
           'job_id': os.environ['SLURM_JOB_ID'],
           'case_count': sum(len(cases) for cases in all_cases.values()),
           'cases': all_cases, 'comparisons_with_fixed': comparisons,
           'matched_expected_regression': expected,
           'unaffected_comparisons_passed': len(comparisons) == 16 and all(c['passed'] for c in comparisons)}
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
(out / 'input-reference-sha256.json').write_text(json.dumps(input_hashes, indent=2) + '\n')
assert summary['matched_expected_regression'] and summary['unaffected_comparisons_passed'], summary
print('REPRODUCED: 4 GPU symmetry failures; 16 control runs passed references and match fixed results.', flush=True)
