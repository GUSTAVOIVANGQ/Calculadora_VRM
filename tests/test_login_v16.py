"""Pruebas v16: el login mantiene CSRF/Origin y muestra errores en el mismo formulario."""
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


class LoginV16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        salt = bytes.fromhex('cc'*16)
        digest = hashlib.pbkdf2_hmac('sha256', b'prueba-larga-segura-123', salt, 100001)
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

    def csrf(self):
        with urllib.request.urlopen(self.base + '/login') as response:
            html = response.read().decode('utf-8')
        self.assertIn('mailto:crt.bot.satys@gmail.com', html)
        self.assertNotIn('Registrarme', html)
        return re.search(r'name="csrf" value="([^"]+)"', html).group(1)

    def post(self, password, origin, csrf=None):
        payload = urllib.parse.urlencode({
            'username': 'user', 'password': password, 'csrf': csrf if csrf is not None else self.csrf()
        }).encode()
        req = urllib.request.Request(self.base + '/login', data=payload, headers={
            'Origin': origin,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Sec-Fetch-Site': 'same-origin',
        })
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, message, headers, target):
                return None
        try:
            return urllib.request.build_opener(NoRedirect).open(req)
        except urllib.error.HTTPError as response:
            return response

    def test_credentials_wrong_same_form_and_admin_contact(self):
        response = self.post('incorrecta', self.base)
        self.assertEqual(response.code, 401)
        page = response.read().decode()
        self.assertIn('Usuario o contraseña incorrectos', page)
        self.assertIn('<form action="/login" method="post"', page)
        self.assertIn('crt.bot.satys@gmail.com', page)
        self.assertNotIn('Solicitud no autorizada', page)

    def test_correct_credentials_redirect(self):
        response = self.post('prueba-larga-segura-123', self.base)
        self.assertEqual(response.code, 303)
        self.assertEqual(response.headers.get('Location'), '/')
        self.assertIn('HttpOnly', response.headers.get('Set-Cookie', ''))

    def test_external_origin_rejected_but_same_login_form(self):
        response = self.post('prueba-larga-segura-123', 'http://evil.example')
        self.assertEqual(response.code, 403)
        page = response.read().decode()
        self.assertIn('No pudimos validar el inicio de sesión', page)
        self.assertIn('name="csrf"', page)
        self.assertNotIn('Usuario o contraseña incorrectos', page)
        self.assertNotIn('Solicitud no autorizada', page)

    def test_fake_csrf_rejected_but_form_remains(self):
        response = self.post('prueba-larga-segura-123', self.base, 'falso')
        self.assertEqual(response.code, 403)
        page = response.read().decode()
        self.assertIn('El formulario venció', page)
        self.assertIn('name="password"', page)


if __name__ == '__main__':
    unittest.main()
