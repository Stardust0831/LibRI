import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

root = Path(os.environ['RI_CHECK_ROOT'])
out = root / 'results'
out.mkdir(exist_ok=False)
deps = root.parent / 'exx-device-20261018-3'
steps = []


def run(name, command, env=None, cwd=None):
    command = list(map(str, command))
    directory = out / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'command.txt').write_text(shlex.join(command) + '\n')
    print('START', name, flush=True)
    with (directory / 'output.log').open('wb') as log:
        result = subprocess.run(command, cwd=cwd or root, env=env, stdout=log, stderr=subprocess.STDOUT)
    (directory / 'exit-code.txt').write_text(str(result.returncode) + '\n')
    steps.append({'name': name, 'command': command, 'exit_code': result.returncode})
    (out / 'steps.json').write_text(json.dumps(steps, indent=2) + '\n')
    print('END', name, result.returncode, flush=True)
    assert result.returncode == 0, name


run('environment/compiler', ['mpicxx', '--version'])
run('environment/gpu', ['nvidia-smi', '-q'])
launch = ['mpirun', '-np', '1', '--map-by', os.environ['MAP_OPT']]
for backend in ('cpu', 'gpu'):
    build = root / ('build-symmetry-' + backend)
    run(f'symmetry/{backend}/configure', ['cmake', '-S', root / 'source/unittests/gpu_symmetry', '-B', build,
        '-DCMAKE_BUILD_TYPE=Debug', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
        f'-DLIBRI_ROOT={root}/source', f'-DLIBCOMM_ROOT={deps}/build/hse-deps/libcomm',
        f'-DCEREAL_ROOT={deps}/build/hse-deps/cereal-install', f'-DDDLA_ROOT={deps}/install/ddla',
        '-DBLA_VENDOR=OpenBLAS', '-DENABLE_GPU=' + ('ON' if backend == 'gpu' else 'OFF')])
    run(f'symmetry/{backend}/build', ['cmake', '--build', build, '--verbose', '--parallel', '2'])
    for threads in (1, 4):
        run(f'symmetry/{backend}/omp{threads}', [*launch, build / 'test_lri_gpu_symmetry'],
            {**os.environ, 'OMP_NUM_THREADS': str(threads)})
run('callbacks/build', ['g++', '-std=c++11', '-I' + str(root / 'source/include'),
    root / 'source/unittests/physics/test_exx_gpu_symmetry.cpp', '-o', root / 'callback-test'])
run('callbacks/test', [root / 'callback-test'])

build = root / 'build-accumulation'
run('accumulation/configure', ['cmake', '-S', root / 'control', '-B', build,
    '-DCMAKE_BUILD_TYPE=Debug', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', f'-DRUN_ROOT={root}',
    f'-DLIBCOMM_ROOT={deps}/build/hse-deps/libcomm', f'-DCEREAL_ROOT={deps}/build/hse-deps/cereal-install',
    f'-DDDLA_ROOT={deps}/install/ddla', '-DTEST_BLAS=/opt/devtools/saiblas/2603-gnu-avx2/lib/libopenblas.so'])
run('accumulation/build', ['cmake', '--build', build, '--verbose', '--parallel', '2'])
for threads in (1, 4):
    env = {**os.environ, 'OMP_NUM_THREADS': str(threads)}
    for backend in ('cpu', 'gpu'):
        for scalar in ('float', 'double', 'complex_float', 'complex_double'):
            name = f'{backend}_{scalar}'
            run(f'accumulation/{name}/omp{threads}', [*launch, build / name], env)
    for name in ('hartree', 'atom_lists', 'gpu_physics'):
        run(f'physics/{name}/omp{threads}', [*launch, build / name], env, cwd=root / 'source')

source = root / 'abacus-source'
build = root / 'abacus-build'
run('abacus/configure', ['cmake', '-S', source, '-B', build,
    '-G', 'Unix Makefiles', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
    '-DENABLE_LIBXC=ON', '-DENABLE_LIBRI=ON', '-DENABLE_LIBRI_GPU=ON',
    '-DENABLE_ELPA=OFF', '-DENABLE_NCCL_PARALLEL_DEVICE=OFF', '-DBUILD_TESTING=OFF',
    '-DGIT_SUBMODULE=OFF', '-DCMAKE_CUDA_ARCHITECTURES=70',
    '-DUSE_CUDA=ON', '-DUSE_CUDA_MPI=ON', '-DENABLE_CUSOLVERMP=ON', '-DENABLE_CUBLASMP=ON',
    f'-DLIBRI_DIR={root}/source', f'-DLIBCOMM_DIR={deps}/build/hse-deps/libcomm',
    f'-Dcereal_DIR={deps}/build/hse-deps/cereal-install/lib/cmake/cereal', f'-DDDLA_ROOT={deps}/install/ddla'])
run('abacus/build', ['cmake', '--build', build, '--target', 'abacus_std_gpu', '--verbose', '--parallel', '12'])
binary = build / 'abacus_std_gpu'
run('abacus/version', [binary, '--version'])
run('abacus/help', [binary, '-h', 'device_exx'])
env = {**os.environ, 'RI_SYSTEM_MPIRUN': shutil.which('mpirun')}
env['PATH'] = str(root / 'control/bin') + ':' + env['PATH']
run('abacus/cases', ['python3', root / 'control/abacus_cases.py'], env)
headers = {str(p.relative_to(root / 'source')): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted((root / 'source/include').rglob('*')) if p.is_file()}
(out / 'libri-header-sha256.json').write_text(json.dumps(headers, indent=2) + '\n')
(out / 'summary.json').write_text(json.dumps({'passed': True, 'job_id': os.environ['SLURM_JOB_ID'],
    'manifest': json.loads((root / 'manifest.json').read_text()), 'steps': steps}, indent=2) + '\n')
print('ALL MERGED PR15/PR16 VALIDATION PASSED', flush=True)
