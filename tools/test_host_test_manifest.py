"""The committed host test manifest matches a fresh static classification."""
import json
import unittest

from tools import run_host_tests


class HostTestManifestTests(unittest.TestCase):
    def test_committed_manifest_matches_static_classification(self):
        # Reuses build/host-test-manifest-cache.json only while the stat
        # fingerprint of every classifier input (tools/ sources) is unchanged.
        expected = run_host_tests.current_manifest()
        committed = json.loads(run_host_tests.MANIFEST_PATH.read_text())
        if committed == expected:
            return
        old, new = committed.get('tests', {}), expected['tests']
        added = sorted(set(new) - set(old))
        removed = sorted(set(old) - set(new))
        changed = sorted(t for t in set(old) & set(new) if old[t] != new[t])
        self.fail('tools/host_test_manifest.json is out of date '
                  f'(added {added[:8]}, removed {removed[:8]}, reclassified {changed[:8]}); '
                  f'regenerate with: {run_host_tests.REGENERATE_COMMAND}')

    def test_committed_manifest_uses_canonical_formatting(self):
        text = run_host_tests.MANIFEST_PATH.read_text()
        self.assertEqual(text, run_host_tests.manifest_text(json.loads(text)),
                         f'regenerate with: {run_host_tests.REGENERATE_COMMAND}')

    def test_known_failure_entries_are_well_formed(self):
        data = json.loads(run_host_tests.KNOWN_FAILURES_PATH.read_text())
        modules = {entry['module'] for entry in
                   json.loads(run_host_tests.MANIFEST_PATH.read_text())['tests'].values()}
        for item in data['known_failures']:
            self.assertTrue(item.get('reason'), item)
            module = item['id'] if item['id'] in modules else None
            if module is None:
                prefix = item['id'].split('.')
                module = next(('.'.join(prefix[:n]) for n in range(len(prefix), 0, -1)
                               if '.'.join(prefix[:n]) in modules), None)
            self.assertIsNotNone(module, f'known failure names no test module: {item["id"]}')


if __name__ == '__main__':
    unittest.main()
