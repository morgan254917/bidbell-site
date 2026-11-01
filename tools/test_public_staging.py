import unittest
from prepare_static import ROOT, public_asset


class PublicStaging(unittest.TestCase):
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
