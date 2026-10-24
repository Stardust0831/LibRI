import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

root = Path(os.environ['RI_CHECK_ROOT'])
source = root / 'abacus-source'
binary = root / 'abacus-build/abacus_std_gpu'
out = root / 'results/cli'
out.mkdir()


def run(name, args, cwd=None):
    command = [str(binary), *args]
    result = subprocess.run(command, cwd=cwd or root, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    (out / (name + '.command.txt')).write_text(shlex.join(command) + '\n')
    (out / (name + '.log')).write_text(result.stdout)
    (out / (name + '.exit-code.txt')).write_text(str(result.returncode) + '\n')
    return result


for name, args in [('version', ['--version']), ('info', ['--info']),
                   ('help', ['-h', 'device_exx']), ('metadata', ['--generate-parameters-yaml'])]:
    result = run(name, args)
    assert result.returncode == 0, name
help_text = ' '.join((out / 'help.log').read_text().split())
assert 'Real-space EXX symmetry reduction is supported' in help_text
assert 'do not support real-space' not in help_text
assert 'default: cpu' in help_text.lower() or 'cpu' in help_text
metadata = (out / 'metadata.log').read_text()
assert 'device_exx' in metadata
assert 'Real-space EXX symmetry reduction is supported' in metadata

tests = out / 'tests'
suite = tests / '08_RI'
suite.mkdir(parents=True)
(tests / 'PP_ORB').symlink_to(source / 'tests/PP_ORB')
common = {'basis_type': 'lcao', 'device': 'gpu', 'ks_solver': 'cusolver',
          'symmetry': 1, 'exx_symmetry_realspace': 1, 'device_exx': 'gpu'}
cases = [
    ('cpu_default', {'device': 'cpu', 'ks_solver': 'scalapack_gvx', 'device_exx': None}, None),
    ('gpu_default_cpu_ri', {'device_exx': None}, None),
    ('gpu_explicit_cpu_ri', {'device_exx': 'cpu'}, None),
    ('gpu_symmetry', {}, None),
    ('gpu_full', {'exx_symmetry_realspace': 0}, None),
    ('gpu_no_symmetry', {'symmetry': 0}, None),
    ('unknown_device_exx', {'device_exx': 'ddla'}, 'device_exx must be cpu or gpu'),
    ('gpu_ri_cpu_device', {'device': 'cpu', 'ks_solver': 'scalapack_gvx'},
     'device_exx=gpu requires basis_type=lcao and device=gpu'),
    ('gpu_ri_pw', {'basis_type': 'pw', 'ks_solver': 'cg'},
     'device_exx=gpu requires basis_type=lcao and device=gpu'),
]
records = []
for name, changes, diagnostic in cases:
    case = suite / name
    shutil.copytree(source / 'tests/08_RI/scf_hse_symm_multik', case)
    path = case / 'INPUT'
    content = path.read_text()
    for key, value in {**common, **changes}.items():
        pattern = r'(?m)^\s*' + re.escape(key) + r'\s+[^\n]*$'
        content = re.sub(pattern, '', content)
        if value is not None:
            content += '\n' + key + ' ' + str(value) + '\n'
    path.write_text(content)
    result = run(name, ['--check-input'], case)
    if diagnostic is None:
        assert result.returncode == 0, (name, result.stdout)
    else:
        assert result.returncode != 0 and diagnostic in result.stdout, (name, result.stdout)
    records.append({'case': name, 'expected': diagnostic or 'accepted',
                    'exit_code': result.returncode, 'passed': True})
(tests / 'PP_ORB').unlink()
(out / 'summary.json').write_text(json.dumps({'passed': True, 'cases': records}, indent=2) + '\n')
print('PASS help, metadata, version/info and all 9 INPUT checks')
