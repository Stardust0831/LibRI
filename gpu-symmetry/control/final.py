import json
import os
from pathlib import Path
import shlex
import subprocess

root = Path(os.environ['RI_CHECK_ROOT'])
out = root / 'results'
out.mkdir(exist_ok=True)
deps = Path('/org/abacus-group/abacususer01/abacus_hse_gpu_experiment/runs/lcao-hse/exx-device-20261018-3')
steps = []


def run(name, command, env=None, required=True):
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
    if required:
        assert p.returncode == 0, name
    return p.returncode


run('environment/compiler', ['mpicxx', '--version'])
run('environment/gpu', ['nvidia-smi', '-q'])
for variant, gpu in [('fixed-cpu', False), ('fixed-gpu', True), ('backport', True), ('baseline', True)]:
    source = root / ('fixed' if variant.startswith('fixed') else variant)
    build = root / ('final-build-' + variant)
    args = ['cmake', '-S', root / 'fixed/unittests/gpu_symmetry', '-B', build,
            '-DCMAKE_BUILD_TYPE=Debug', f'-DLIBRI_ROOT={source}',
            f'-DLIBCOMM_ROOT={deps}/build/hse-deps/libcomm',
            f'-DCEREAL_ROOT={deps}/build/hse-deps/cereal-install',
            f'-DDDLA_ROOT={deps}/install/ddla',
            '-DBLA_VENDOR=OpenBLAS', '-DENABLE_GPU=' + ('ON' if gpu else 'OFF')]
    run(variant + '/configure', args)
    run(variant + '/build', ['cmake', '--build', build, '--verbose', '--parallel', '2'])
    binary = build / 'test_lri_gpu_symmetry'
    if variant.startswith('fixed'):
        for threads in (1, 4):
            env = {**os.environ, 'OMP_NUM_THREADS': str(threads)}
            run(f'{variant}/omp{threads}', ['mpirun', '-np', '1', '--map-by', os.environ['MAP_OPT'], binary], env)
    else:
        failures = []
        for label in range(18):
            code = run(f'{variant}/label-{label:02}', ['mpirun', '-np', '1', '--map-by',
                       os.environ['MAP_OPT'], binary, str(label), 'gpu', 'real'], required=False)
            if code:
                failures.append(label)
        expected = [1, 3, 7, 9] if variant == 'backport' else [0, 1, 2, 3, 6, 7, 8, 9, 12, 13, 14, 15, 16, 17]
        assert failures == expected, (variant, failures)
run('callbacks/build', ['g++', '-std=c++11', '-I' + str(root / 'fixed/include'),
                      root / 'fixed/unittests/physics/test_exx_gpu_symmetry.cpp', '-o', root / 'callback-test'])
run('callbacks/test', [root / 'callback-test'])

build = root / 'abacus-build'
source = root / 'abacus-source'
run('abacus/configure', ['cmake', '-S', source, '-B', build,
    '-G', 'Unix Makefiles', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
    '-DENABLE_LIBXC=ON', '-DENABLE_LIBRI=ON', '-DENABLE_LIBRI_GPU=ON',
    '-DENABLE_ELPA=OFF', '-DENABLE_NCCL_PARALLEL_DEVICE=OFF', '-DBUILD_TESTING=OFF',
    '-DGIT_SUBMODULE=OFF', '-DCMAKE_CUDA_ARCHITECTURES=70',
    '-DUSE_CUDA=ON', '-DUSE_CUDA_MPI=ON', '-DENABLE_CUSOLVERMP=ON', '-DENABLE_CUBLASMP=ON',
    f'-DLIBRI_DIR={root}/fixed', f'-DLIBCOMM_DIR={deps}/build/hse-deps/libcomm',
    f'-Dcereal_DIR={deps}/build/hse-deps/cereal-install/lib/cmake/cereal', f'-DDDLA_ROOT={deps}/install/ddla'])
run('abacus/build', ['cmake', '--build', build, '--target', 'abacus_std_gpu', '--verbose', '--parallel', '12'])
binary = build / 'abacus_std_gpu'
run('abacus/version', [binary, '--version'])
run('abacus/help', [binary, '-h', 'device_exx'])
env = {**os.environ, 'RI_SYSTEM_MPIRUN': subprocess.check_output(['which', 'mpirun'], text=True).strip()}
env['PATH'] = str(root / 'control/bin') + ':' + env['PATH']
run('abacus/cases', ['python3', root / 'control/abacus_cases.py'], env)
(out / 'summary.json').write_text(json.dumps({'passed': True, 'steps': steps}, indent=2) + '\n')
print('ALL VALIDATION PASSED', flush=True)
