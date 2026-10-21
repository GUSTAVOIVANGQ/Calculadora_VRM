"""Regresión v17: impedir Origin null generado por Referrer-Policy no-referrer."""
import hashlib
import re
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import server


class LoginV17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        salt = bytes.fromhex('dd'*16)
        digest = hashlib.pbkdf2_hmac('sha256', b'clave-de-prueba-segura-xyz', salt, 100001)
        cls.auth = server.Auth('user', f'pbkdf2_sha256$100001${salt.hex()}${digest.hex()}', cookie_secure=False)
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.http.auth = cls.auth
        cls.base = f'http://127.0.0.1:{cls.http.server_address[1]}'
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        self.auth.failures.clear()
        self.env = patch.dict('os.environ', {'VMR_PUBLIC_ORIGIN': self.base, 'VMR_COOKIE_SECURE': '0'})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def token(self):
        with urllib.request.urlopen(self.base + '/login') as response:
            self.assertEqual(response.headers['Referrer-Policy'], 'same-origin')
            page = response.read().decode('utf-8')
        return re.search(r'name="csrf" value="([^"]+)"', page).group(1)

    def post(self, origin, password='clave-de-prueba-segura-xyz'):
        fields = urllib.parse.urlencode({'csrf': self.token(), 'username': 'user', 'password': password}).encode()
        req = urllib.request.Request(self.base + '/login', data=fields, headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': origin,
            'Sec-Fetch-Site': 'same-origin',
        })
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, message, headers, location):
                return None
        try:
            return urllib.request.build_opener(NoRedirect).open(req)
        except urllib.error.HTTPError as error:
            return error

    def test_policy_preserves_same_origin_form_post(self):
        response = self.post(self.base)
        self.assertEqual(response.status, 303)
        self.assertEqual(response.headers.get('Location'), '/')

    def test_null_origin_still_denied(self):
        response = self.post('null')
        self.assertEqual(response.status, 403)
        self.assertIn('No pudimos validar el inicio de sesión', response.read().decode())

    def test_other_domain_still_denied(self):
        response = self.post('https://evil.example')
        self.assertEqual(response.status, 403)

    def test_wrong_password_returns_401_not_origin_error(self):
        response = self.post(self.base, password='incorrecta')
        self.assertEqual(response.status, 401)
        self.assertIn('Usuario o contraseña incorrectos', response.read().decode())


if __name__ == '__main__':
    unittest.main()
