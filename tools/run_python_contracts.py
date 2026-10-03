"""Run every repository tool contract module, including namespace subfolders."""
import argparse
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, default=ROOT / 'build/python-contract-summary.json')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    modules = sorted('.'.join(path.relative_to(ROOT).with_suffix('').parts)
                     for path in (ROOT / 'tools').rglob('test_*.py'))
    suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps({
        'evidence_class': 'host', 'module_denominator': len(modules),
        'modules': modules, 'tests_run': result.testsRun,
        'failures': [name.id() for name, _ in result.failures],
        'errors': [name.id() for name, _ in result.errors],
        'skipped': [{'test': name.id(), 'reason': reason} for name, reason in result.skipped],
        'unexpected_successes': [name.id() for name in result.unexpectedSuccesses],
        'expected_failures': [name.id() for name, _ in result.expectedFailures],
        'passed': result.wasSuccessful()
    }, indent=2) + '\n')
    return int(not result.wasSuccessful())


if __name__ == '__main__':
    raise SystemExit(main())
