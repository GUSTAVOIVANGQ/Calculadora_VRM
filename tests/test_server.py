"""Pruebas end-to-end de login y rutas protegidas sin paquetes externos."""
import hashlib
import json
import http.cookiejar
import re
import sys
import threading
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        salt = bytes.fromhex('ab' * 16)
        iterations = 100001
        digest = hashlib.pbkdf2_hmac('sha256', b'prueba-segura-12345', salt, iterations)
        stored = f'pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}'
        cls._dist_temp = tempfile.TemporaryDirectory()
        cls._original_dist = server.DIST
        server.DIST = Path(cls._dist_temp.name)
        server.DIST.joinpath('index.html').write_text('<html><body><div id="root">Calculadora React</div></body></html>')
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.srv.auth = server.Auth('administrador', stored, cookie_secure=False)
        cls.base = 'http://127.0.0.1:%d' % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        server.DIST = cls._original_dist
        cls._dist_temp.cleanup()

    def setUp(self):
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, path, method='GET', data=None):
        if data is not None:
            data = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(self.base + path, data=data, method=method)
        try:
            return self.opener.open(req)
        except urllib.error.HTTPError as exc:
            return exc

    def raw(self, path, method='GET', data=None):
        if data is not None:
            data = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(self.base + path, data=data, method=method)
        opener = urllib.request.build_opener(urllib.request.HTTPHandler)
        # La respuesta 302 es observada antes del login.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener(NoRedirect)
        try:
            return opener.open(req)
        except urllib.error.HTTPError as exc:
            return exc

    def login(self):
        html = self.request('/login').read().decode()
        token = re.search(r'name="csrf" value="([^"]+)"', html).group(1)
        return self.request('/login', 'POST', {'csrf': token, 'username': 'administrador',
                                               'password': 'prueba-segura-12345'})

    def test_01_anonymous_redirects_to_login(self):
        r = self.raw('/')
        self.assertEqual(r.status, 302)
        self.assertEqual(r.headers['Location'], '/login')
        self.assertIn('Iniciar sesión', self.request('/login').read().decode())

    def test_02_private_assets_restricted(self):
        for path in ('/assets/model.js', '/assets/data.js', '/assets/ui.js',
                     '/assets/controls.js', '/assets/styles.css',
                     '/archivos/Calculadora_VMR_5G_actualizada_15_oct.xlsx'):
            self.assertEqual(self.request(path).status, 401, path)
        for path in ('/assets/login.css', '/assets/logo-crt.png', '/assets/favicon.svg'):
            self.assertEqual(self.request(path).status, 200, path)

    def test_03_login_success_private_app_and_cookie(self):
        r = self.login()
        self.assertEqual(r.status, 200)  # urllib sigue el redirect a la calculadora
        html = r.read().decode()
        self.assertIn('Calculadora', html)
        self.assertIn('id="root"', html)
        info = json.load(self.request('/api/v1/auth/session'))
        self.assertTrue(info['authenticated'])
        self.assertTrue(info['csrf'])
        self.assertNotIn('<!-- SERVER_LOGOUT -->', html)
        self.assertTrue(any(c.name == 'vmr_session' for c in self.cookies))
        for path in ('/assets/model.js', '/assets/data.js', '/assets/ui.js',
                     '/assets/styles.css', '/archivos/Calculadora_VMR_5G_actualizada_15_oct.xlsx'):
            self.assertEqual(self.request(path).status, 200, path)

    def test_04_wrong_password(self):
        page = self.request('/login').read().decode()
        token = re.search(r'name="csrf" value="([^"]+)"', page).group(1)
        r = self.request('/login', 'POST', {'csrf': token, 'username': 'administrador',
                                           'password': 'mal'})
        self.assertEqual(r.status, 401)
        self.assertIn('incorrectos', r.read().decode())
        self.assertEqual(self.raw('/assets/model.js').status, 401)
        self.srv.auth.failures.clear()

    def test_05_csrf_and_logout(self):
        self.login().read()
        html = self.request('/').read().decode()
        token = json.load(self.request('/api/v1/auth/session'))['csrf']
        self.assertEqual(self.request('/logout', 'POST', {'csrf': 'invalid'}).status, 403)
        self.assertEqual(self.request('/assets/model.js').status, 200)
        r = self.request('/logout', 'POST', {'csrf': token})
        self.assertIn('Iniciar sesión', r.read().decode())
        self.assertEqual(self.request('/assets/model.js').status, 401)

    def test_06_invalid_paths_and_methods(self):
        for path in ('/server.py', '/create_login.py', '/login.html', '/DESPLIEGUE.md',
                     '/etc/crt-vmr-5g.env', '/tests/test_server.py',
                     '/assets/', '/..%2fserver.py', '/%2e%2e/server.py'):
            self.assertEqual(self.request(path).status, 404, path)
        for method in ('PUT', 'DELETE', 'PATCH', 'OPTIONS'):
            self.assertEqual(self.request('/', method).status, 405, method)
        self.assertEqual(self.request('/', 'POST').status, 405)
        self.assertEqual(self.request('/login', 'HEAD').status, 200)

    def test_07_security_headers(self):
        headers = self.request('/login').headers
        self.assertIn("form-action 'self'", headers['Content-Security-Policy'])
        self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(headers['X-Frame-Options'], 'DENY')
        self.assertIn('no-store', headers['Cache-Control'])

    def test_08_health(self):
        self.assertEqual(self.request('/healthz').read(), b'ok\n')

    def test_09_bad_or_missing_token(self):
        self.assertEqual(self.request('/login', 'POST', {'csrf': '', 'username': 'administrador',
                                                       'password': 'prueba-segura-12345'}).status, 403)
        self.assertEqual(self.request('/login', 'POST', {'csrf': 'fake'}).status, 403)

    def test_10_unicode_username_does_not_crash(self):
        page = self.request('/login').read().decode()
        token = re.search(r'name="csrf" value="([^"]+)"', page).group(1)
        response = self.request('/login', 'POST', {'csrf': token, 'username': 'ñá', 'password': 'incorrecta'})
        self.assertEqual(response.status, 401)
        self.srv.auth.failures.clear()

    def test_11_secure_cookie_option(self):
        other_auth = server.Auth(self.srv.auth.user,
                    'pbkdf2_sha256$100001$' + ('ab'*16) + '$' + self.srv.auth.digest.hex(),
                    cookie_secure=True)
        self.assertIn('Secure', other_auth.cookie('token'))
        self.assertIn('HttpOnly', other_auth.cookie('token'))
        self.assertIn('SameSite=Strict', other_auth.cookie('token'))
        self.assertIn('Max-Age=0', other_auth.cookie('', delete=True))


if __name__ == '__main__':
    unittest.main()
