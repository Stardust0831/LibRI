from pathlib import Path
import json
import os
import shutil
import subprocess

root = Path(os.environ['RI_CHECK_ROOT'])
out = root / 'diagnostic'
out.mkdir(exist_ok=True)
parent = root.parent / 'libri-gpu-symmetry-20261023/upstream-validation/baseline'
commands = json.loads((root / 'build-tests/compile_commands.json').read_text())
command = next(c['command'] for c in commands if c['file'].endswith('/lr_driver.cpp'))
import shlex
args = shlex.split(command)
args = [a.replace(str(root / 'source/include'), str(parent / 'include')) for a in args]
args[args.index('-o') + 1] = str(out / 'parent-lr.o')
with (out / 'build.log').open('w') as log:
    subprocess.run(args, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
    link = shlex.split((root / 'build-tests/CMakeFiles/lr.dir/link.txt').read_text())
    link = [str(out / 'parent-lr.o') if a.endswith('lr_driver.cpp.o') else a for a in link]
    link[link.index('-o') + 1] = str(out / 'parent-lr')
    subprocess.run(link, cwd=root / 'build-tests', stdout=log, stderr=subprocess.STDOUT, check=True)
launch = ['mpirun', '-np', '1', '--map-by', os.environ['MAP_OPT']]
for version, binary in [('parent', out / 'parent-lr'), ('candidate', root / 'build-tests/lr')]:
    work = out / version
    refs = work / 'unittests/physics'
    refs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / 'source/unittests/physics/LR-ref', refs / 'LR-ref')
    for name, extra in [('reference', []), ('values', ['--write-ref'])]:
        with (work / (name + '.log')).open('w') as log:
            run = subprocess.run([*launch, binary, *extra], cwd=work, stdout=log, stderr=subprocess.STDOUT)
        print(version, name, run.returncode, flush=True)
    shutil.move(refs / 'LR-ref', work / 'actual.txt')
for name, binary, extra in [('atom_lists', 'atom_lists', []), ('gitee-hartree', 'gitee_atom_lists', ['hartree']),
                            ('gitee-cvc', 'gitee_atom_lists', ['cvc']), ('gitee-input', 'gitee_const_input', [])]:
    with (out / (name + '.log')).open('w') as log:
        run = subprocess.run([*launch, root / 'build-tests' / binary, *extra], cwd=root, stdout=log, stderr=subprocess.STDOUT)
    print(name, run.returncode, flush=True)
actual = [float(x) for x in (out / 'candidate/actual.txt').read_text().split()]
baseline = [float(x) for x in (out / 'parent/actual.txt').read_text().split()]
reference = [float(x) for x in (root / 'source/unittests/physics/LR-ref').read_text().split()]
assert len(actual) == len(baseline) == len(reference)
print('Maximum serialized candidate/parent difference:', max(abs(a-b) for a,b in zip(actual, baseline)), flush=True)
print('Maximum serialized parent/reference difference:', max(abs(a-b) for a,b in zip(baseline, reference)), flush=True)
