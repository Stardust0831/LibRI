import json
import math
from pathlib import Path
import sys

candidate, parent, reference = [
    [float(token) for token in Path(name).read_text().split()] for name in sys.argv[1:]
]
assert len(candidate) == len(parent) == len(reference)
assert all(math.isfinite(x) for values in (candidate, parent, reference) for x in values)
delta = max(abs(a-b) for a, b in zip(candidate, parent))
report = {
    'numeric_tokens': len(candidate),
    'maximum_candidate_parent_difference': delta,
    'maximum_candidate_reference_difference': max(abs(a-b) for a, b in zip(candidate, reference)),
    'maximum_parent_reference_difference': max(abs(a-b) for a, b in zip(parent, reference)),
    'candidate_parent_tolerance': 1e-7,
}
print(json.dumps(report, indent=2))
assert delta < 1e-7, 'LR differs from the pre-import implementation'
