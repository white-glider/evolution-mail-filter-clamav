"""Harmless regression tests; ClamAV and desktop notifications are stubbed."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get('TEST_BASH', 'bash')


def shell_path(path):
    text = str(path.resolve())
    if os.name == 'nt':
        text = text.replace('\\', '/')
        return '/' + text[0].lower() + text[2:]
    return text


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='filter-tests-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.private = self.base / 'temporary files'
        self.private.mkdir()
        self.script = ROOT / 'clamav_evolution.sh'
        self.env = dict(os.environ, PATH=shell_path(self.bin) + ':/usr/bin:/bin',
                        TMPDIR=shell_path(self.private), TEST_DIR=shell_path(self.base))
        startup = self.base / 'bash-env'
        startup.write_text('export PATH="$TEST_PATH"\n', encoding='utf-8')
        self.env.update(BASH_ENV=shell_path(startup), TEST_PATH=self.env['PATH'])
        self.stub('clamscan', '''
printf '%s\\n' "$$" > "$TEST_DIR/scanner.pid"
file=${!#}
cat -- "$file" > "$TEST_DIR/message-copy"
stat -c '%a' -- "${file%/*}" > "$TEST_DIR/directory-mode"
stat -c '%a' -- "$file" > "$TEST_DIR/file-mode"
printf '%s\\n' "$file" > "$TEST_DIR/message-path"
if [[ ${BLOCK_SCAN:-0} == 1 ]]; then exec sleep 30; fi
if [[ ${SCAN_STATUS:-0} == 1 ]]; then printf '%s: Test.Signature FOUND\\n' "$file"; fi
exit "${SCAN_STATUS:-0}"
''')
        self.stub('notify-send', '''
printf '%s\\n' "$@" >> "$TEST_DIR/notifications"
exit "${NOTIFY_STATUS:-0}"
''')

    def stub(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/bash\n' + body, encoding='utf-8', newline='\n')
        path.chmod(0o700)

    def run_filter(self, status=0, message=b'From: real@example.invalid\nSubject: test\n\nbody\n'):
        self.env['SCAN_STATUS'] = str(status)
        return subprocess.run([BASH, shell_path(self.script)], input=message,
                              env=self.env, capture_output=True, timeout=10)

    def notifications(self):
        path = self.base / 'notifications'
        return path.read_text() if path.exists() else ''

    def assert_cleaned(self):
        self.assertEqual(list(self.private.iterdir()), [])

    def test_clean_and_stdin_preserved(self):
        message = b'From: a@example.invalid\r\nSubject: test\r\n\r\nbytes\x00after\n'
        result = self.run_filter(message=message)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.base / 'message-copy').read_bytes(), message)
        self.assertEqual(self.notifications(), '')
        self.assert_cleaned()

    def test_infected(self):
        result = self.run_filter(1)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('Test.Signature', self.notifications())
        self.assertIn('From: real@example.invalid', self.notifications())
        self.assert_cleaned()

    def test_errors_never_return_clean(self):
        for status in (2, 127):
            with self.subTest(status=status):
                result = self.run_filter(status)
                self.assertEqual(result.returncode, 2)
                self.assertIn(b'not verified clean', result.stderr)
                self.assertIn('scan failed', self.notifications())
                self.assert_cleaned()

    def test_notification_failure_preserves_detection(self):
        self.env['NOTIFY_STATUS'] = '1'
        result = self.run_filter(1)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'notification failed', result.stderr)

    def test_markup_is_escaped(self):
        self.run_filter(1, b'From: A <a@example.invalid>\nSubject: <b>fake</b> & text\n\n')
        self.assertIn('&lt;b&gt;fake&lt;/b&gt; &amp; text', self.notifications())

    def test_install_path_with_spaces(self):
        location = self.base / 'installed scripts'
        location.mkdir()
        for name in ('clamav_evolution.sh', 'clamav_evolution.awk'):
            shutil.copyfile(ROOT / name, location / name)
        self.script = location / 'clamav_evolution.sh'
        self.assertEqual(self.run_filter(1).returncode, 1)
        self.assertIn('Subject: test', self.notifications())

    def test_missing_counterpart(self):
        self.script = self.base / 'missing.sh'
        shutil.copyfile(ROOT / 'clamav_evolution.sh', self.script)
        self.assertEqual(self.run_filter().returncode, 2)
        self.assertIn('Missing AWK', self.notifications())
        self.assert_cleaned()

    def test_temp_creation_failure(self):
        self.stub('mktemp', 'exit 1\n')
        self.assertEqual(self.run_filter().returncode, 2)
        self.assert_cleaned()

    def test_message_write_failure(self):
        self.stub('cat', 'exit 1\n')
        self.assertEqual(self.run_filter().returncode, 2)
        self.assert_cleaned()

    def test_missing_scanner(self):
        (self.bin / 'clamscan').unlink()
        self.env['TEST_PATH'] = shell_path(self.bin)
        result = self.run_filter()
        self.assertEqual(result.returncode, 2)
        self.assertIn(b'Missing command: clamscan', result.stderr)

    @unittest.skipIf(os.name == 'nt', 'POSIX file modes required')
    def test_private_permissions(self):
        self.run_filter()
        self.assertEqual((self.base / 'directory-mode').read_text().strip(), '700')
        self.assertEqual((self.base / 'file-mode').read_text().strip(), '600')

    @unittest.skipIf(os.name == 'nt', 'POSIX signals required')
    def test_term_cleans_message_and_child(self):
        self.env['BLOCK_SCAN'] = '1'
        process = subprocess.Popen([BASH, shell_path(self.script)], env=self.env,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        process.stdin.write(b'private message\n')
        process.stdin.close()
        deadline = time.monotonic() + 5
        while not (self.base / 'scanner.pid').exists():
            if time.monotonic() > deadline:
                self.fail('Scanner did not start')
            time.sleep(0.02)
        child = int((self.base / 'scanner.pid').read_text())
        process.send_signal(signal.SIGTERM)
        self.assertEqual(process.wait(timeout=5), 143)
        process.stdout.close()
        process.stderr.close()
        self.assert_cleaned()
        with self.assertRaises(ProcessLookupError):
            os.kill(child, 0)

    def test_header_cases(self):
        cases = [
            (b'From: real\n\nSubject: body\n', b'From: real\n'),
            (b'from: real\r\nsUbJeCt:\tfirst\r\n\tsecond\r\n\r\nSubject: body\r\n',
             b'From: real\nSubject: first second\n'),
            (b'Subject: first\nSubject: second\n folded duplicate\nFrom: real\n\n',
             b'From: real\nSubject: first\n'),
            (b'\nFrom: body\nSubject: body\n', b''),
            (b'', b''),
        ]
        for message, expected in cases:
            with self.subTest(message=message):
                result = subprocess.run([BASH, '-c', 'awk -f "$1"', 'test',
                                         shell_path(ROOT / 'clamav_evolution.awk')],
                                        input=message, env=self.env, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)


if __name__ == '__main__':
    unittest.main()
