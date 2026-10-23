#!/usr/bin/env python3
"""Test ABACUS with f683421 plus only the recorded declaration-movement patch."""

import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

root = Path(os.environ['RI_CHECK_ROOT'])
source = root / 'source'
libri = root / 'libri'
out = root / 'results'
deps = Path('/org/abacus-group/abacususer01/abacus_hse_gpu_experiment/runs/lcao-hse/exx-device-20261018-3')
steps = []
manifest = json.loads((root / 'manifest.json').read_text())
for name, digest in manifest['archive_sha256'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
headers = {str(p.relative_to(libri)): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted((libri / 'include').rglob('*')) if p.is_file()}
assert headers == manifest['expected_header_sha256'], 'Unexpected LibRI header changes'
assert hashlib.sha256((root / 'move-declarations.patch').read_bytes()).hexdigest() == manifest['patch_sha256']
(out / 'libri-header-sha256.json').write_text(json.dumps(headers, indent=2) + '\n')


def run(name, command, env=None):
    command = list(map(str, command))
    directory = out / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'command.txt').write_text(shlex.join(command) + '\n')
    print('START', name, flush=True)
    with (directory / 'output.log').open('wb') as log:
        result = subprocess.run(command, cwd=root, stdout=log,
                                stderr=subprocess.STDOUT, env=env)
    (directory / 'exit-code.txt').write_text(str(result.returncode) + '\n')
    steps.append({'step': name, 'command': command, 'exit_code': result.returncode})
    (out / 'steps.json').write_text(json.dumps(steps, indent=2) + '\n')
    print('END', name, 'exit', result.returncode, flush=True)
    return result.returncode == 0


def finish(status, reason, code):
    result = {**manifest, 'status': status, 'reason': reason, 'job_id': os.environ.get('SLURM_JOB_ID'),
              'steps': steps}
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(status, reason, flush=True)
    sys.exit(code)


run('environment/compiler', ['mpicxx', '--version'])
run('environment/gpu', ['nvidia-smi', '-q'])
run('environment/allocation', ['scontrol', 'show', 'job', os.environ['SLURM_JOB_ID']])
dependencies = [f'-DLIBRI_DIR={libri}', f'-DLIBCOMM_DIR={deps}/build/hse-deps/libcomm',
                f'-Dcereal_DIR={deps}/build/hse-deps/cereal-install/lib/cmake/cereal']
consumer_passed = True
for backend in ('cpu', 'gpu'):
    enable = 'ON' if backend == 'gpu' else 'OFF'
    build = root / ('consumer-' + backend)
    configured = run(f'consumer-{backend}/configure', ['cmake', '-S', source / 'tests/lcao_hse_gpu/cmake',
        '-B', build, *dependencies, f'-DENABLE_LIBRI_GPU={enable}',
        f'-DENABLE_LIBRI_GPU_TESTS={enable}', f'-DDDLA_ROOT={deps}/install/ddla'])
    built = configured and run(f'consumer-{backend}/build', ['cmake', '--build', build, '--verbose', '--parallel', '2'])
    tested = built and run(f'consumer-{backend}/test', ['ctest', '--test-dir', build, '-V'])
    consumer_passed = consumer_passed and tested

build = root / 'build-gpu'
configured = run('abacus/configure', ['cmake', '-S', source, '-B', build,
    '-G', 'Unix Makefiles', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
    '-DENABLE_LIBXC=ON', '-DENABLE_LIBRI=ON', '-DENABLE_LIBRI_GPU=ON',
    '-DENABLE_ELPA=OFF', '-DENABLE_NCCL_PARALLEL_DEVICE=OFF',
    '-DBUILD_TESTING=OFF', '-DGIT_SUBMODULE=OFF', '-DCMAKE_CUDA_ARCHITECTURES=70',
    '-DUSE_CUDA=ON', '-DUSE_CUDA_MPI=ON', '-DENABLE_CUSOLVERMP=ON', '-DENABLE_CUBLASMP=ON',
    *dependencies, f'-DDDLA_ROOT={deps}/install/ddla'])
if not configured:
    finish('BLOCKED', 'ABACUS configuration failed with the declaration-movement patch.', 2)

# BSE is a mandatory dependency of the LCAO/LibRI executable. Compile it first
# because the same LibRI branch changed its LRI_k headers.
if not run('abacus/bse-build', ['cmake', '--build', build, '--target', 'bse', '--verbose', '--parallel', '2']):
    finish('BLOCKED', 'The required ABACUS BSE target still fails; no executable or SCF result was produced.', 2)
if not run('abacus/full-build', ['cmake', '--build', build, '--target', 'abacus_std_gpu', '--verbose', '--parallel', '12']):
    finish('BLOCKED', 'The full ABACUS executable failed to build.', 2)

binary = build / 'abacus_std_gpu'
installed = root / 'install/bin/abacus'
installed.parent.mkdir(parents=True, exist_ok=True)
installed.symlink_to(binary)
version_passed = run('abacus/version', [binary, '--version'])
cli_passed = run('abacus/cli', ['python3', root / 'control/verify_cli.py'])
passed = consumer_passed and version_passed and cli_passed
for case, ranks in [('scf_hse_gamma', '1'), ('scf_hse_complex_multik_mpi2', '2')]:
    env = {**os.environ, 'RI_TEST_RANKS': ranks}
    ok = run('abacus/' + case, ['python3', root / 'control/backend_regressions.py',
        '--abacus', binary, '--source', source, '--output', out / case, '--case', case], env=env)
    passed = passed and ok
finish('PASSED' if passed else 'FAILED', 'See individual dependency and ABACUS regression results.', 0 if passed else 1)
