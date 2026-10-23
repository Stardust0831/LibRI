import json
import os
from pathlib import Path
import shlex
import subprocess

root = Path(os.environ['RI_CHECK_ROOT'])
out = root / 'probe-results'
out.mkdir(exist_ok=True)
deps = Path('/org/abacus-group/abacususer01/abacus_hse_gpu_experiment/runs/lcao-hse/exx-device-20261018-3')
steps = []


def run(name, command, env=None):
    command = list(map(str, command))
    directory = out / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'command.txt').write_text(shlex.join(command) + '\n')
    print('START', name, flush=True)
    with (directory / 'output.log').open('wb') as stream:
        p = subprocess.run(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT)
    (directory / 'exit-code.txt').write_text(str(p.returncode) + '\n')
    steps.append({'name': name, 'command': command, 'exit_code': p.returncode})
    (out / 'steps.json').write_text(json.dumps(steps, indent=2) + '\n')
    print('END', name, p.returncode, flush=True)
    return p.returncode


run('compiler', ['mpicxx', '--version'])
run('gpu', ['nvidia-smi', '-q'])
for variant, gpu in [('baseline', True), ('backport', True), ('cpu', False)]:
    source = root / ('baseline' if variant == 'cpu' else variant)
    build = root / ('build-' + variant)
    args = ['cmake', '-S', root / 'control/test', '-B', build,
            '-DCMAKE_BUILD_TYPE=Debug', f'-DLIBRI_ROOT={source}',
            f'-DLIBCOMM_ROOT={deps}/build/hse-deps/libcomm',
            f'-DCEREAL_ROOT={deps}/build/hse-deps/cereal-install',
            f'-DDDLA_ROOT={deps}/install/ddla',
            '-DBLA_VENDOR=OpenBLAS', '-DENABLE_GPU=' + ('ON' if gpu else 'OFF')]
    assert run(variant + '/configure', args) == 0
    assert run(variant + '/build', ['cmake', '--build', build, '--verbose', '--parallel', '2']) == 0
    binary = build / 'test_lri_gpu_symmetry'
    if variant == 'cpu':
        assert run('cpu/check', ['mpirun', '-np', '1', '--map-by', os.environ['MAP_OPT'], binary]) == 0
    else:
        for label in range(18):
            run(f'{variant}/label-{label:02}',
                ['mpirun', '-np', '1', '--map-by', os.environ['MAP_OPT'], binary, str(label), 'gpu', 'real'])
print('PROBE COMPLETED', flush=True)
