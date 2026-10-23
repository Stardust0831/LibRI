import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess

root = Path(os.environ['RI_CHECK_ROOT'])
source = root / 'abacus-source'
binary = root / 'abacus-build/abacus_std_gpu'
out = root / 'results/abacus-cases'
number = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?'
all_records = {}
comparisons = []


def set_input(path, settings):
    text = path.read_text()
    for key, value in settings.items():
        pattern = r'(?m)^\s*' + re.escape(key) + r'\s+[^\n]*$'
        line = key + ' ' + str(value)
        text = re.sub(pattern, line, text) if re.search(pattern, text) else text + '\n' + line + '\n'
    path.write_text(text)


def values(path):
    text = path.read_text()
    energies = re.findall(r'!FINAL_ETOT_IS\s+(' + number + r')\s+eV', text)
    assert len(energies) == 1, path
    states = re.findall(r'#SCF IS (.*?)#', text)
    assert states and all(state == 'CONVERGED' for state in states), (path, states)
    force = text.split('#TOTAL-FORCE (eV/Angstrom)#')[1].split('#TOTAL-STRESS')[0]
    force_rows = re.findall(r'^\s*[A-Z][a-z]?\d+\s+(' + number + r')\s+(' + number
                            + r')\s+(' + number + r')\s*$', force, re.M)
    assert len(force_rows) == 2, path
    stress = text.split('#TOTAL-STRESS (kbar)#')[1].split('#TOTAL-PRESSURE')[0]
    stress_rows = re.findall(r'^\s*(' + number + r')\s+(' + number + r')\s+('
                             + number + r')\s*$', stress, re.M)
    assert len(stress_rows) == 3, path
    result = {'energy_ev': [float(energies[0])],
              'force_ev_angstrom': [float(v) for row in force_rows for v in row],
              'stress_kbar': [float(v) for row in stress_rows for v in row]}
    assert all(math.isfinite(v) for vals in result.values() for v in vals), path
    return result


variants = {
    'host': {'device': 'cpu', 'ks_solver': 'scalapack_gvx', 'device_exx': 'cpu', 'exx_symmetry_realspace': 1},
    'cpu_sym': {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'cpu', 'exx_symmetry_realspace': 1},
    'gpu_sym': {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'gpu', 'exx_symmetry_realspace': 1},
    'cpu_full': {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'cpu', 'exx_symmetry_realspace': 0},
    'gpu_full': {'device': 'gpu', 'ks_solver': 'cusolver', 'device_exx': 'gpu', 'exx_symmetry_realspace': 0},
}
for ranks in (1, 2):
    for scalar, real in [('real', 1), ('complex', 0)]:
        group = f'{scalar}-mpi{ranks}'
        directory = out / group
        tests = directory / 'tests'
        suite = tests / '08_RI'
        suite.mkdir(parents=True, exist_ok=True)
        for name in ['PP_ORB', 'integrate']:
            link = tests / name
            if not link.is_symlink():
                link.symlink_to(source / 'tests' / name)
        for variant, settings in variants.items():
            case = suite / variant
            if not case.exists():
                shutil.copytree(source / 'tests/08_RI/scf_hse_symm_multik', case)
                set_input(case / 'INPUT', {**settings, 'exx_real_number': real})
        (suite / 'CASES.symmetry.txt').write_text('\n'.join(variants) + '\n')
        pending = [name for name in variants if not (suite / name / 'OUT.autotest/INPUT.info').exists()]
        if pending:
            (suite / 'CASES.pending.txt').write_text('\n'.join(pending) + '\n')
            env = {**os.environ, 'RI_TEST_RANKS': str(ranks)}
            command = ['bash', str(tests / 'integrate/Autotest.sh'), '-a', str(binary),
                       '-n', str(ranks), '-o', '1', '-f', 'CASES.pending.txt', '-r', '.*']
            logname = 'autotest-resume.log' if (directory / 'autotest.log').exists() else 'autotest.log'
            with (directory / logname).open('wb') as log:
                p = subprocess.run(command, cwd=suite, env=env, stdout=log, stderr=subprocess.STDOUT)
            (directory / (logname + '.exit-code')).write_text(str(p.returncode) + '\n')
            assert p.returncode == 0, (group, 'repository reference comparison failed')
            executed = dict(line.split() for line in (suite / 'test.sum').read_text().splitlines())
            assert all(executed.get(name) == '1' for name in pending), (group, executed)
        records = {}
        for variant, settings in variants.items():
            case = suite / variant
            info = (case / 'OUT.autotest/INPUT.info').read_text()
            for key in ['device_exx', 'exx_symmetry_realspace', 'exx_real_number']:
                match = re.search(r'(?m)^\s*' + key + r'\s+(\S+)', info)
                assert match, (case, key)
                wanted = {**settings, 'exx_real_number': real}[key]
                if isinstance(wanted, int):
                    assert match[1].lower() in ({'1', 'true'} if wanted else {'0', 'false'}), (case, key, match[1])
                else:
                    assert match[1] == wanted, (case, key, match[1])
            records[variant] = values(case / 'OUT.autotest/running_scf.log')
        for variant in variants:
            if variant == 'cpu_sym':
                continue
            delta = {key: max(abs(a-b) for a,b in zip(records['cpu_sym'][key], records[variant][key]))
                     for key in records['cpu_sym']}
            passed = delta['energy_ev'] <= 1e-6 and delta['force_ev_angstrom'] <= 1e-4 and delta['stress_kbar'] <= 1e-3
            comparisons.append({'group': group, 'reference': 'cpu_sym', 'variant': variant,
                                'max_errors': delta, 'passed': passed})
        all_records[group] = records
        (tests / 'PP_ORB').unlink()
        (tests / 'integrate').unlink()
        print('PASS repository references:', group, flush=True)
        result = {'cases': all_records, 'comparisons': comparisons,
                  'passed': all(row['passed'] for row in comparisons)}
        (out / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
assert all(row['passed'] for row in comparisons), comparisons
print('PASS all 20 HSE symmetry runs and 16 component comparisons', flush=True)
