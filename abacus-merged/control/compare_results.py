#!/usr/bin/env python3
"""Compare energies and each force/stress component in the recorded regressions."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--results', type=Path, required=True)
parser.add_argument('--previous', type=Path)
args = parser.parse_args()
number = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?'
limits = {'energy_ev': 1e-7, 'forces_ev_angstrom': 1e-4, 'stress_kbar': 1e-3}


def read_case(directory, force_stress):
    path = directory / 'OUT.autotest/running_scf.log'
    text = path.read_text()
    energies = re.findall(r'!FINAL_ETOT_IS\s+(' + number + r')\s+eV', text)
    assert len(energies) == 1, (path, 'missing or repeated final energy')
    states = re.findall(r'#SCF IS (.*?)#', text)
    assert states and all(s == 'CONVERGED' for s in states), (path, states)
    values = {'energy_ev': [float(energies[0])]}
    if force_stress:
        assert text.count('#TOTAL-FORCE (eV/Angstrom)#') == 1, path
        force_block = text.split('#TOTAL-FORCE (eV/Angstrom)#')[1].split('#TOTAL-STRESS')[0]
        rows = re.findall(r'^\s*([A-Z][a-z]?\d+)\s+(' + number + r')\s+(' + number
                          + r')\s+(' + number + r')\s*$', force_block, re.M)
        assert len(rows) == 3, (path, 'expected the three-atom water case')
        values['atom_labels'] = [row[0] for row in rows]
        values['forces_ev_angstrom'] = [float(x) for row in rows for x in row[1:]]
        assert text.count('#TOTAL-STRESS (kbar)#') == 1, path
        stress_block = text.split('#TOTAL-STRESS (kbar)#')[1].split('#TOTAL-PRESSURE')[0]
        rows = re.findall(r'^\s*(' + number + r')\s+(' + number + r')\s+(' + number
                          + r')\s*$', stress_block, re.M)
        assert len(rows) == 3, (path, 'expected all three stress rows')
        values['stress_kbar'] = [float(x) for row in rows for x in row]
        assert max(map(abs, values['forces_ev_angstrom'])) > 1e-3, path
        assert max(map(abs, values['stress_kbar'])) > 1e-3, path
    assert all(math.isfinite(x) for key in limits if key in values for x in values[key]), path
    return {'values': values, 'log_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def compare(label, reference, actual):
    a, b = reference['values'], actual['values']
    assert a.keys() == b.keys(), label
    if 'atom_labels' in a:
        assert a['atom_labels'] == b['atom_labels'], label
    errors = {}
    for key, tolerance in limits.items():
        if key not in a:
            continue
        assert len(a[key]) == len(b[key]), (label, key)
        delta = max(abs(x - y) for x, y in zip(a[key], b[key]))
        errors[key] = delta
    passed = all(error <= limits[key] for key, error in errors.items())
    return {'comparison': label, 'max_absolute_differences': errors, 'passed': passed}


records, comparisons = {}, []
for case in ('scf_hse_gamma', 'scf_hse_complex_multik_mpi2'):
    source_case = case.removesuffix('_mpi2')
    force_stress = case == 'scf_hse_gamma'
    values = {}
    for variant in ('host', 'default', 'cpu', 'gpu'):
        relative = Path(case) / 'tests/08_RI' / (source_case + '_' + variant)
        values[variant] = read_case(args.results / relative, force_stress)
        if args.previous:
            old = read_case(args.previous / relative, force_stress)
            comparisons.append(compare(case + '/' + variant + ': previous -> current', old, values[variant]))
    for variant in ('default', 'cpu', 'gpu'):
        comparisons.append(compare(case + ': host -> ' + variant, values['host'], values[variant]))
    comparisons.append(compare(case + ': cpu RI -> gpu RI', values['cpu'], values['gpu']))
    records[case] = values

result = {'passed': all(row['passed'] for row in comparisons), 'absolute_tolerances': limits,
          'cases': records, 'comparisons': comparisons,
          'note': 'Tolerances match the existing integration harness; force and stress comparisons are componentwise.'}
(args.results / 'component-comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
