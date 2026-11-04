import unittest
from prepare_static import ROOT, public_asset


class PublicStaging(unittest.TestCase):
    def test_pull_requests_use_the_same_public_staging_command_as_render(self):
        workflow = (ROOT / '.github/workflows/pages.yml').read_text(encoding='utf-8')
        self.assertRegex(workflow, r'(?m)^  pull_request:\n    branches: \[main\]$')
        self.assertRegex(workflow, r'(?m)^        run: python3 tools/prepare_static\.py$')

    def test_only_manual_main_runs_can_upload_and_deploy(self):
        workflow = (ROOT / '.github/workflows/pages.yml').read_text(encoding='utf-8')
        build, deploy = workflow.split('\n  deploy:\n', 1)
        manual_main = "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'"
        upload_step = build.split('uses: actions/upload-pages-artifact@', 1)[1]
        self.assertIn(f'\n        if: {manual_main}\n', upload_step)
        self.assertIn(f'\n    if: {manual_main}\n', deploy)
        self.assertRegex(upload_step, r'(?m)^          include-hidden-files: true$')

    def test_private_and_build_files_cannot_be_published(self):
        for name in ['.git/config', '.github/workflows/pages.yml', '.env', 'tools/paddle.json',
                     'tests/customer.json', '_site/index.html', 'backup.sqlite3', 'owner.pem',
                     'workspace/core.test.mjs', 'desk/index.html']:
            self.assertFalse(public_asset(ROOT / name), name)

    def test_public_routes_assets_and_security_contact_are_retained(self):
        for name in ['index.html', 'start/index.html', 'brand.css', 'fonts/public-sans.woff2',
                     'workspace/core.mjs', 'data/cleaning_bids.json', '.well-known/security.txt']:
            self.assertTrue(public_asset(ROOT / name), name)


if __name__ == '__main__':
    unittest.main()
