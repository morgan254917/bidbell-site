"""Actual committed-source replay catches cross-day generated-page drift."""
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import check_live_site
import prepare_static

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)


class BuildDatePolicy(unittest.TestCase):
    def test_build_clock_is_utc_and_explicit_replay_date_is_preserved(self):
        resolver = getattr(prepare_static, 'get_build_date', None)
        self.assertTrue(callable(resolver), 'Staging must capture one UTC build date.')
        local = datetime(2026, 11, 1, 22, 30, tzinfo=timezone(timedelta(hours=-4)))
        self.assertEqual(resolver({}, now=local), '2026-11-02')
        self.assertEqual(resolver({'BUILD_DATE': '2026-11-01'}, now=NOW), '2026-11-01')

    def test_release_metadata_records_the_date_used_for_staged_bytes(self):
        stage = getattr(prepare_static, 'stage_public_assets', None)
        self.assertTrue(callable(stage), 'Staging must record its exact content build date.')
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'index.html').write_bytes(b'<p>Reviewed homepage</p>')
            stage('f' * 40, '2026-11-02', root=root)
            self.assertEqual((root / '_site/index.html').read_bytes(), b'<p>Reviewed homepage</p>')
            self.assertEqual(json.loads((root / '_site/release.json').read_bytes()), {
                'commit': 'f' * 40, 'service': 'bidbell-public-site', 'build_date': '2026-11-02'})

    def test_remote_build_date_is_canonical_and_bounded_by_commit_and_today(self):
        validate = getattr(check_live_site, 'validated_build_date', None)
        self.assertTrue(callable(validate), 'Untrusted build dates must be bounded before replay.')
        committed = int(datetime(2026, 11, 1, 12, tzinfo=timezone.utc).timestamp())
        self.assertEqual(validate('2026-11-02', committed, now=NOW), '2026-11-02')
        for invalid in [None, '20261102', '2026-11-02;echo bad', '2026-11-03', '2026-10-31']:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate(invalid, committed, now=NOW)

    def test_expanded_release_mode_is_recorded_and_staging_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root/'index.html').write_text('<html><head></head><body>Sample</body></html>', encoding='utf-8')
            with patch.dict(os.environ, BIDBELL_STAGING='0', BIDBELL_CONSTRUCTION_ENABLED='1'):
                prepare_static.stage_public_assets('f'*40, '2026-11-02', root=root)
            self.assertEqual(json.loads((root/'_site/release.json').read_bytes())['mode'], 'expanded')
            with patch.dict(os.environ, BIDBELL_STAGING='1', BIDBELL_CONSTRUCTION_ENABLED='0'):
                prepare_static.stage_public_assets('f'*40, '2026-11-02', root=root)
            self.assertEqual(json.loads((root/'_site/release.json').read_bytes())['mode'], 'staging')
        self.assertEqual(check_live_site.validated_release_mode('expanded', 'expanded'), 'expanded')
        for mode, expected in [('staging','auto'),('other','auto'),(None,'expanded')]:
            with self.subTest(mode=mode,expected=expected), self.assertRaises(ValueError):
                check_live_site.validated_release_mode(mode, expected)


class CommittedBuildReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.repo = Path(cls.temp.name) / 'trusted-site'
        cls.repo.mkdir()
        archive = subprocess.check_output(['git', '-c', 'core.autocrlf=false', 'archive', '--format=zip', 'HEAD'], cwd=ROOT)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            for name in bundle.namelist():
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
            bundle.extractall(cls.repo)
        # Commit the builder under test, then reproduce a Windows-style checkout.
        shutil.copyfile(ROOT / 'tools/build.py', cls.repo / 'tools/build.py')
        if (ROOT / '.gitattributes').exists():
            shutil.copyfile(ROOT / '.gitattributes', cls.repo / '.gitattributes')
        data_path = cls.repo / 'data/cleaning_bids.json'
        data = json.loads(data_path.read_text(encoding='utf-8'))
        base = data['bids'][0]
        data['updated'] = '2026-11-01'
        data['bids'] = [dict(base, title='Fixture expired janitorial', sol='FIX-EXPIRED', type='Solicitation',
                             due='2026-11-02', due_at='2026-11-02T14:00:00Z', due_precision='time',
                             state='TX', link='https://sam.gov/opp/fixture-expired/view'),
                        dict(base, title='Fixture active janitorial', sol='FIX-ACTIVE', type='Solicitation',
                             due='2026-11-03', due_at='2026-11-03T14:00:00Z', due_precision='time',
                             state='TX', link='https://sam.gov/opp/fixture-active/view')]
        data_path.write_text(json.dumps(data), encoding='utf-8')
        env = dict(os.environ, GIT_AUTHOR_DATE='2026-11-01T12:00:00Z', GIT_COMMITTER_DATE='2026-11-01T12:00:00Z')
        for args in [['init', '-q'], ['-c', 'core.autocrlf=false', 'add', '-A'],
                     ['-c', 'user.name=BidBell fixture', '-c', 'user.email=fixture@example.test',
                      '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic dated site source']]:
            subprocess.run(['git', *args], cwd=cls.repo, env=env, check=True, capture_output=True)
        cls.commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cls.repo, text=True).strip()
        (cls.repo / 'index.html').unlink()
        subprocess.run(['git', '-c', 'core.autocrlf=true', 'checkout-index', '--all', '--force'],
                       cwd=cls.repo, check=True, capture_output=True)

    def replay(self, day):
        builder = getattr(check_live_site, 'trusted_build', None)
        self.assertTrue(callable(builder), 'Verify generated bytes from trusted committed source at the deployment date.')
        return builder(self.commit, day, repository=self.repo)

    def test_expanded_replay_uses_committed_native_signup_projection(self):
        with check_live_site.trusted_build(self.commit, '2026-11-02', repository=self.repo, mode='expanded') as built:
            start = (built/'start/index.html').read_text(encoding='utf-8')
            subscribe = (built/'subscribe/index.html').read_text(encoding='utf-8')
            self.assertIn('https://bidbell-workspace.onrender.com/app?industry=construction#register', start)
            self.assertNotIn('https://docs.google.com/forms/', start)
            self.assertNotIn('127.0.0.1', start)
            self.assertTrue((built/'expansion.css').is_file())
            self.assertIn('https://cdn.paddle.com/paddle/v2/paddle.js', subscribe)

    def test_same_commit_later_build_date_matches_generated_page_and_expires_bids(self):
        with self.replay('2026-11-01') as first:
            old_subscribe = (first / 'subscribe/index.html').read_bytes()
            old_bids = (first / 'cleaning-bids/texas/index.html').read_bytes()
            legal = (first / 'terms/index.html').read_bytes()
        with self.replay('2026-11-02') as second:
            new_subscribe = (second / 'subscribe/index.html').read_bytes()
            new_bids = (second / 'cleaning-bids/texas/index.html').read_bytes()
            self.assertEqual((second / 'terms/index.html').read_bytes(), legal)
        self.assertIn(b'Page updated November 1, 2026', old_subscribe)
        self.assertIn(b'Page updated November 2, 2026', new_subscribe)
        self.assertNotEqual(old_subscribe, new_subscribe)
        self.assertIn(b'Fixture expired janitorial', old_bids)
        self.assertNotIn(b'Fixture expired janitorial', new_bids)
        self.assertIn(b'Fixture active janitorial', new_bids)

    def test_repeated_replay_matches_every_html_page_and_authored_home_is_exact(self):
        with self.replay('2026-11-02') as first:
            before = {p.relative_to(first).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in first.rglob('*.html')}
        with self.replay('2026-11-02') as second:
            after = {p.relative_to(second).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in second.rglob('*.html')}
            committed_home = subprocess.check_output(['git', 'show', self.commit + ':index.html'], cwd=self.repo)
            self.assertEqual((second / 'index.html').read_bytes(), committed_home)
        self.assertGreaterEqual(len(before), 65)
        self.assertEqual(after, before)

    def test_tampered_generated_price_and_body_are_rejected(self):
        with self.replay('2026-11-02') as expected:
            page = (expected / 'subscribe/index.html').read_bytes()
            self.assertIn(b'US$39', page)
            self.assertFalse(check_live_site.asset_matches(page.replace(b'US$39', b'US$1'), page, 'subscribe/index.html'))
            self.assertFalse(check_live_site.asset_matches(page + b'<p>Injected copy</p>', page, 'subscribe/index.html'))

    def test_generated_pages_use_lf_bytes_on_every_platform(self):
        with self.replay('2026-11-02') as expected:
            for path in expected.rglob('*.html'):
                self.assertFalse(b'\r\n' in path.read_bytes(), str(path.relative_to(expected)))

    def test_windows_checkout_stages_authored_home_as_exact_git_bytes(self):
        prepare_static.stage_public_assets(self.commit, '2026-11-02', root=self.repo)
        committed_home = subprocess.check_output(['git', 'show', self.commit + ':index.html'], cwd=self.repo)
        self.assertTrue((self.repo / '_site/index.html').read_bytes() == committed_home,
                        'Fresh Windows checkout must stage the exact authored Git bytes.')

    def test_dirty_working_tree_cannot_change_trusted_authored_content(self):
        path = self.repo / 'index.html'
        original = path.read_bytes()
        try:
            path.write_bytes(b'<p>Uncommitted content must not become expected</p>')
            with self.replay('2026-11-02') as expected:
                self.assertEqual((expected / 'index.html').read_bytes(), original)
        finally:
            path.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
