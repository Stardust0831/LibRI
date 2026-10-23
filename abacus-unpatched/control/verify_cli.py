#!/usr/bin/env python3
"""Verify the renamed INPUT keyword's CLI and generated metadata."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

root = Path(os.environ['RI_CHECK_ROOT'])
binary = root / 'install/bin/abacus'
out = root / 'results'
for label, args in [('version', ['--version']), ('abacus-info', ['--info']),
                    ('device-exx-help', ['-h', 'device_exx']),
                    ('parameters', ['--generate-parameters-yaml'])]:
    result = subprocess.run([str(binary), *args], text=True, capture_output=True, check=True, timeout=120)
    (out / (label + '.txt')).write_text(result.stdout)
help_text = (out / 'device-exx-help.txt').read_text()
assert 'device_exx' in help_text and 'exx_device' not in help_text
assert 'Independent LR and RDMFT' in ' '.join(help_text.split())
metadata = (out / 'parameters.txt').read_text()
assert re.search(r'\bdevice_exx\b', metadata)
assert not re.search(r'\bexx_device\b', metadata)
case = out / 'old-keyword'
shutil.copytree(root / 'source/tests/08_RI/scf_hse_gamma', case)
with (case / 'INPUT').open('a') as stream:
    stream.write('\nexx_device cpu\n')
result = subprocess.run([str(binary), '--check-input'], cwd=case, text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
(out / 'old-keyword-rejected.log').write_text(result.stdout)
assert result.returncode != 0 and "PARAMETER NAME 'exx_device' IS INCORRECT" in result.stdout
summary = {'new_help_passed': True, 'new_metadata_passed': True, 'old_keyword_rejected': True,
           'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
           'source_sha': json.loads((root / 'manifest.json').read_text())['source_sha']}
(out / 'cli-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
