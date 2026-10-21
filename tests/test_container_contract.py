"""Checks offline for expected container build and deployment contracts."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ContainerContractTests(unittest.TestCase):
    def test_required_files(self):
        for name in ['Dockerfile', '.dockerignore', 'compose.yaml',
                     'compose.tls.yaml', 'container/healthcheck.py',
                     'container/quadlet/portal-crt-vmr5g.container']:
            with self.subTest(name=name):
                self.assertTrue((ROOT/name).is_file())
    def test_two_stage_build(self):
        contents=(ROOT/'Dockerfile').read_text()
        self.assertIn('FROM node:22-alpine AS frontend-builder', contents)
        self.assertIn('FROM python:3.13-slim-bookworm AS runtime', contents)
        self.assertIn('COPY --chown=10001:10001 --from=frontend-builder',contents)
        self.assertIn('USER 10001:10001',contents)
        self.assertIn('HEALTHCHECK', contents)
        self.assertIn('login-error.html', contents)
    def test_no_secrets_in_build_context(self):
        contents=(ROOT/'.dockerignore').read_text()
        self.assertIn('*.key',contents)
        self.assertIn('.env',contents)
        self.assertIn('*.sqlite3',contents)
    def test_persistent_db_and_8084(self):
        compose=(ROOT/'compose.yaml').read_text()
        quad=(ROOT/'container/quadlet/portal-crt-vmr5g.container').read_text()
        self.assertIn('8084:8084',compose)
        self.assertIn('/var/lib/crt-vmr-5g-container',compose)
        self.assertIn('EnvironmentFile=/etc/crt-vmr-5g.env',quad)
        self.assertIn('WantedBy=multi-user.target',quad)
        self.assertIn('8084:8084',quad)
    def test_server_expected_routes(self):
        code=(ROOT/'server.py').read_text()
        for endpoint in ['/login','/crear-cuenta','/healthz','/api/v1/readiness','/api/v1/calculate']:
            self.assertIn(endpoint,code)

if __name__ == '__main__':
    unittest.main()
