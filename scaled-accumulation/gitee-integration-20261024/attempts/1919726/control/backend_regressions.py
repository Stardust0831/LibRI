import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--abacus', type=Path, required=True)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--case', required=True)
args = parser.parse_args()
source_name = args.case[:-5] if args.case.endswith('_mpi2') else args.case
source_case = args.source / 'tests/08_RI' / source_name
tests = args.output / 'tests'
suite = tests / '08_RI'
suite.mkdir(parents=True)
(tests / 'PP_ORB').symlink_to(args.source / 'tests/PP_ORB')
(tests / 'integrate').symlink_to(args.source / 'tests/integrate')
ranks = os.environ['RI_TEST_RANKS']
summary = []


def set_input(path, updates):
    text = path.read_text()
    for key, value in updates.items():
        pattern = r'(?m)^\s*' + re.escape(key) + r'\s+[^\n]*$'
        if re.search(pattern, text):
            text = re.sub(pattern, key + ' ' + str(value), text)
        else:
            text += '\n' + key + ' ' + str(value) + '\n'
    path.write_text(text)


try:
    variants = [('host', {'device': 'cpu', 'ks_solver': 'scalapack_gvx'}),
                ('default', {'device': 'gpu', 'ks_solver': 'cusolver'}),
                ('cpu', {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'cpu'})]
    if source_name == 'scf_hse_symm_multik':
        variants += [('cpu_full', {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'cpu', 'exx_symmetry_realspace': '0'}),
                     ('gpu_full', {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'gpu', 'exx_symmetry_realspace': '0'})]
    else:
        variants.append(('gpu', {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'gpu'}))

    names = []
    for variant, settings in variants:
        name = source_name + '_' + variant
        shutil.copytree(source_case, suite / name)
        set_input(suite / name / 'INPUT', settings)
        names.append(name)
    (suite / 'CASES.task.txt').write_text('\n'.join(names) + '\n')
    command = ['bash', str(tests / 'integrate/Autotest.sh'), '-a', str(args.abacus), '-n', ranks, '-o', '1', '-f', 'CASES.task.txt']
    with (args.output / 'autotest.log').open('w') as log:
        run = subprocess.run(command, cwd=suite, stdout=log, stderr=subprocess.STDOUT)
    print((args.output / 'autotest.log').read_text(), flush=True)
    if run.returncode:
        raise SystemExit(run.returncode)

    for (variant, settings), name in zip(variants, names):
        info = (suite / name / 'OUT.autotest/INPUT.info').read_text()
        match = re.search(r'(?m)^\s*device_exx\s+(\w+)', info)
        assert match and match[1] == settings.get('device_exx', 'cpu'), (name, match)
        summary.append({'case': name, 'ranks': int(ranks), 'device_exx': match[1], 'result': 'PASS'})

    if source_name == 'scf_hse_gamma':
        checks = [
            ('valid_cpu', {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'cpu'}, None),
            ('valid_gpu', {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'gpu'}, None),
            ('bad_value', {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'ddla'}, 'device_exx must be cpu or gpu'),
            ('bad_device', {'device': 'cpu', 'ks_solver': 'scalapack_gvx', 'device_exx': 'gpu'}, 'device_exx=gpu requires basis_type=lcao and device=gpu'),
            ('bad_symmetry', {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'gpu', 'symmetry': '1', 'exx_symmetry_realspace': '1'}, 'LibRI GPU contractions do not support real-space EXX symmetry'),
        ]
        for name, settings, expected_error in checks:
            case = suite / name
            shutil.copytree(source_case, case)
            set_input(case / 'INPUT', settings)
            check = subprocess.run([str(args.abacus), '--check-input'], cwd=case, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
            (args.output / (name + '.log')).write_text(check.stdout)
            if expected_error:
                assert check.returncode != 0 and expected_error in check.stdout, (name, check.returncode, check.stdout)
            else:
                assert check.returncode == 0 and 'successfully checked' in check.stdout, (name, check.returncode, check.stdout)
            summary.append({'check': name, 'result': 'PASS', 'expected_error': expected_error})
finally:
    (tests / 'PP_ORB').unlink(missing_ok=True)
    (tests / 'integrate').unlink(missing_ok=True)

(args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2), flush=True)
