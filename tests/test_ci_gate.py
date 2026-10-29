"""Kontrollerar att kodändringar aldrig stänger av lint/test."""

import fnmatch
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/ci.yml'


def job_sections(text):
    starts = list(re.finditer(r'^  ([\w-]+):\n', text, re.MULTILINE))
    return {
        match[1]: text[match.end():starts[index + 1].start() if index + 1 < len(starts) else len(text)]
        for index, match in enumerate(starts)
    }


def should_run(condition, outputs, event='pull_request'):
    prefix = "github.event_name == 'workflow_dispatch' || "
    if condition.startswith(prefix):
        if event == 'workflow_dispatch':
            return True
        condition = condition[len(prefix):]
    match = re.fullmatch(r"needs\.gate\.outputs\.(\w+)\s*(==|!=)\s*'([^']+)'", condition)
    if not match:
        raise ValueError('Unsupported gate condition: ' + condition)
    actual = outputs.get(match[1], '')
    return actual == match[3] if match[2] == '==' else actual != match[3]


def filter_outputs(gate, paths):
    block = gate.split('filters: |', 1)[1]
    name = re.search(r'^            (\w+):$', block, re.MULTILINE)[1]
    patterns = re.findall(r"^              - '([^']+)'$", block, re.MULTILINE)
    expanded = []
    for pattern in patterns:
        braces = re.search(r'\{([^}]+)\}', pattern)
        expanded.extend(
            [pattern[:braces.start()] + suffix + pattern[braces.end():] for suffix in braces[1].split(',')]
            if braces else [pattern]
        )
    matched = any(
        fnmatch.fnmatchcase(path, pattern)
        or (pattern.startswith('**/') and fnmatch.fnmatchcase(path, pattern[3:]))
        for path in paths for pattern in expanded
    )
    values = {name: str(matched).lower()}
    exports = re.findall(r'^      (\w+): \$\{\{ steps\.changes\.outputs\.(\w+) \}\}', gate, re.MULTILINE)
    return {output: values.get(source, '') for output, source in exports}


class WorkflowGateTests(unittest.TestCase):
    def setUp(self):
        self.jobs = job_sections(WORKFLOW.read_text())

    def assert_jobs_run(self, paths, expected, event='pull_request'):
        outputs = filter_outputs(self.jobs['gate'], paths)
        for name in ('lint', 'test'):
            condition = re.search(r'^    if: (.+)$', self.jobs[name], re.MULTILINE)[1]
            self.assertEqual(should_run(condition, outputs, event), expected, (name, paths, event))

    def test_application_changes_run_checks(self):
        for path in ('src/index.ts', 'index.js', 'worker/routes/mail.py', 'Cargo.lock', 'package.json'):
            with self.subTest(path=path):
                self.assert_jobs_run([path], True)

    def test_workflow_and_test_changes_run_checks(self):
        for path in ('.github/workflows/ci.yml', 'tests/fixture.json', 'test/example.txt'):
            with self.subTest(path=path):
                self.assert_jobs_run([path], True)

    def test_documentation_only_skips_checks(self):
        self.assert_jobs_run(['README.md', 'docs/design.md'], False)

    def test_mixed_changes_run_checks(self):
        self.assert_jobs_run(['docs/design.md', 'src/index.ts'], True)

    def test_manual_dispatch_runs_checks_even_without_code_changes(self):
        self.assert_jobs_run(['README.md'], True, event='workflow_dispatch')
        self.assert_jobs_run([], True, event='workflow_dispatch')

    def test_secret_scan_is_unconditional(self):
        self.assertIsNone(re.search(r'^    (if|needs):', self.jobs['secret-scan'], re.MULTILINE))

    def test_pull_request_file_filter_can_read_changed_files(self):
        permissions = re.search(r'^    permissions:\n((?:      .+\n)+)', self.jobs['gate'], re.MULTILINE)
        self.assertIsNotNone(permissions, 'dorny/paths-filter needs a job-scoped read grant')
        grants = dict(re.findall(r'^      ([\w-]+): (\w+)$', permissions[1], re.MULTILINE))
        self.assertEqual(grants, {'contents': 'read', 'pull-requests': 'read'})

    def test_empty_or_python_scaffold_does_not_require_npm_lockfile(self):
        for name in ('lint', 'test'):
            node_setup = self.jobs[name].split('uses: actions/setup-node@', 1)[1].split('      - ', 1)[0]
            self.assertIsNone(re.search(r'''^          cache: ['"]?npm['"]?$''', node_setup, re.MULTILINE), name)
            self.assertIsNotNone(re.search(r'^          package-manager-cache: false$', node_setup, re.MULTILINE), name)

    def test_gate_runs_only_its_own_contract_before_app_dependencies(self):
        command = re.search(
            r'name: Verify CI gate regression contracts\n        run: (.+)', self.jobs['gate']
        )[1]
        with tempfile.TemporaryDirectory() as root:
            tests = Path(root) / 'tests'
            tests.mkdir()
            (tests / 'test_ci_gate.py').write_text(
                'import unittest\nclass Gate(unittest.TestCase):\n'
                '    def test_gate(self): self.assertTrue(True)\n'
            )
            (tests / 'test_application.py').write_text(
                'raise ImportError("Application dependencies are not installed yet")\n'
            )
            result = subprocess.run(shlex.split(command), cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Ran 1 test', result.stderr)


if __name__ == '__main__':
    unittest.main()
