"""Pruebas reales de registro con invitación, login y persistencia SQLite."""
import hashlib
import http.cookiejar
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import accounts
import server


class RegistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dist_dir = tempfile.TemporaryDirectory()
        cls._original_dist = server.DIST
        server.DIST = Path(cls._dist_dir.name)
        server.DIST.joinpath('index.html').write_text('<div id="root">Calculadora React</div>')
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / 'users.sqlite3'
        salt = bytes.fromhex('ab' * 16)
        rounds = 100001
        digest = hashlib.pbkdf2_hmac('sha256', b'prueba-segura-12345', salt, rounds)
        stored = f'pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}'
        cls.auth = server.Auth('administrador', stored, cookie_secure=False)
        cls.auth.users = accounts.UserStore(cls.path)
        cls.auth.registration_hash = hashlib.sha256(b'invitacion de prueba 123456789').hexdigest()
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.srv.auth = cls.auth
        cls.base = f'http://127.0.0.1:{cls.srv.server_address[1]}'
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.temp.cleanup()
        server.DIST = cls._original_dist
        cls._dist_dir.cleanup()

    def setUp(self):
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))
        self.auth.registration_failures.clear()

    def req(self, path, data=None, method=None):
        encoded = urllib.parse.urlencode(data).encode() if data is not None else None
        request = urllib.request.Request(self.base + path, data=encoded, method=method)
        try:
            return self.opener.open(request)
        except urllib.error.HTTPError as exc:
            return exc

    def token(self, page):
        content = self.req(page).read().decode()
        found = re.search(r'name="csrf" value="([^\"]+)"', content)
        self.assertIsNotNone(found)
        return found.group(1)

    def register(self, username, password='nueva-contrasena-12345', code='invitacion de prueba 123456789', confirm=None):
        return self.req('/crear-cuenta', {
            'csrf': self.token('/crear-cuenta'), 'username': username,
            'password': password, 'confirm_password': password if confirm is None else confirm,
            'invite_code': code
        })

    def test_01_registration_requires_code(self):
        self.assertEqual(self.register('usuario_invalid', code='invalido').status, 400)
        self.assertFalse(self.auth.users.verify('usuario_invalid', 'nueva-contrasena-12345'))
        self.assertEqual(self.req('/assets/model.js').status, 401)

    def test_02_registration_logs_in_and_private_data(self):
        self.assertEqual(self.register('nuevo_usuario').status, 200)
        self.assertEqual(self.req('/assets/model.js').status, 200)
        self.assertEqual(self.req('/api/v1/metadata').status, 200)
        self.assertTrue(self.auth.users.verify('nuevo_usuario', 'nueva-contrasena-12345'))
        self.assertEqual(self.auth.users.path.stat().st_mode & 0o777, 0o600)

    def test_03_login_existing_registered_user_new_session(self):
        self.assertEqual(self.auth.users.verify('nuevo_usuario', 'nueva-contrasena-12345'), True)
        response = self.req('/login', {'csrf': self.token('/login'), 'username': 'nuevo_usuario',
                                        'password': 'nueva-contrasena-12345'})
        self.assertEqual(response.status, 200)
        self.assertEqual(self.req('/api/v1/defaults').status, 200)

    def test_04_admin_account_not_overwritten(self):
        self.assertEqual(self.register('administrador').status, 400)
        self.assertEqual(self.req('/login', {'csrf': self.token('/login'),
                                             'username': 'administrador',
                                             'password': 'prueba-segura-12345'}).status, 200)

    def test_05_registration_rejects_duplicate_and_password(self):
        self.assertEqual(self.register('nuevo_usuario').status, 400)
        self.assertEqual(self.register('otrousuario', password='corta').status, 400)
        self.assertEqual(self.register('otrousuario', confirm='otra-clave-1234').status, 400)
        self.assertEqual(self.register('usuario mal').status, 400)

    def test_06_csrf_and_registration_switch(self):
        self.assertEqual(self.req('/register', {'csrf': 'falso', 'username': 'nuevo'}, 'POST').status, 403)
        self.auth.registration_hash = ''
        try:
            self.assertEqual(self.req('/register').status, 200)
            self.assertIn('no ha habilitado', self.req('/register').read().decode())
            self.assertEqual(self.register('nuevo_usuario_2').status, 403)
            self.assertEqual(self.req('/api/v1/auth/status').status, 200)
        finally:
            self.auth.registration_hash = hashlib.sha256(b'invitacion de prueba 123456789').hexdigest()

    def test_07_status_and_routes(self):
        import json
        s=json.load(self.req('/api/v1/auth/status'))
        self.assertEqual(s, {'authenticated':False,'registrationEnabled':True})
        self.assertEqual(self.req('/register').status, 200)
        self.assertEqual(self.req('/crear-cuenta', method='HEAD').status, 200)
        self.assertEqual(self.req('/register.html').status, 404)
        self.assertEqual(self.req('/accounts.py').status, 404)
        self.assertEqual(self.req('/var/lib/crt-vmr-5g/users.sqlite3').status, 404)
        login_html = self.req('/login').read().decode()
        self.assertNotIn('>Registrarme</a>', login_html)
        self.assertNotIn('href="/crear-cuenta"', login_html)
        self.assertNotIn('¿No tiene una cuenta?', login_html)
        self.assertNotIn('Crear cuenta con invitación', login_html)

    def test_08_rate_limit(self):
        for n in range(5):
            self.assertEqual(self.register('otro'+str(n), code='mal').status, 400)
        self.assertEqual(self.register('valid-user').status, 429)
        self.auth.registration_failures.clear()

    def test_09_sqlite_survives_new_store(self):
        fresh = accounts.UserStore(self.path)
        self.assertTrue(fresh.verify('nuevo_usuario', 'nueva-contrasena-12345'))
        self.assertFalse(fresh.verify('nuevo_usuario', 'clave-incorrecta'))


if __name__ == '__main__':
    unittest.main()

class JsonAuthenticationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dist_dir = tempfile.TemporaryDirectory()
        cls._original_dist = server.DIST
        server.DIST = Path(cls._dist_dir.name)
        server.DIST.joinpath('index.html').write_text('<div id="root">Calculadora React</div>')
        cls.t = tempfile.TemporaryDirectory()
        auth_salt = bytes.fromhex('aa' * 16)
        iters = 100001
        digest = hashlib.pbkdf2_hmac('sha256', b'admin-password-1234', auth_salt, iters)
        cls.auth = server.Auth('admin', f'pbkdf2_sha256${iters}${auth_salt.hex()}${digest.hex()}',cookie_secure=False)
        cls.auth.users = accounts.UserStore(Path(cls.t.name) / 'users.sqlite3')
        cls.auth.registration_hash = hashlib.sha256(b'codigo-permitido-123').hexdigest()
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0),server.Handler)
        cls.srv.auth = cls.auth
        cls.base = f'http://127.0.0.1:{cls.srv.server_address[1]}'
        threading.Thread(target=cls.srv.serve_forever,daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.t.cleanup()
        server.DIST = cls._original_dist
        cls._dist_dir.cleanup()

    def setUp(self):
        import json
        self.json = json
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def get(self,path):
        return self.opener.open(self.base+path)

    def post(self,path,data):
        req=urllib.request.Request(self.base+path,self.json.dumps(data).encode(),{'Content-Type':'application/json'})
        try:
            return self.opener.open(req)
        except urllib.error.HTTPError as e:
            return e

    def csrf(self):
        return self.json.load(self.get('/api/v1/auth/csrf'))['csrf']

    def test_01_json_login(self):
        response=self.post('/api/v1/auth/login',{'csrf':self.csrf(),'username':'admin','password':'admin-password-1234'})
        self.assertEqual(response.status,200)
        self.assertTrue(self.json.load(self.get('/api/v1/auth/status'))['authenticated'])
        self.assertEqual(self.get('/api/v1/defaults').status,200)

    def test_02_json_registration(self):
        response=self.post('/api/v1/auth/register',{'csrf':self.csrf(), 'username':'json_usuario',
            'password':'test-contrasena-123','confirmPassword':'test-contrasena-123', 'inviteCode':'codigo-permitido-123'})
        self.assertEqual(response.status,201)
        self.assertTrue(self.json.load(response)['ok'])
        self.assertEqual(self.get('/').status,200)

    def test_03_json_bad_csrf(self):
        response=self.post('/api/v1/auth/login',{'csrf':'false','username':'admin','password':'admin-password-1234'})
        self.assertEqual(response.status,403)

    def test_04_json_no_invitation(self):
        response=self.post('/api/v1/auth/register',{'csrf':self.csrf(), 'username':'json_usuario_2',
            'password':'test-contrasena-123','confirmPassword':'test-contrasena-123', 'inviteCode':'mala'})
        self.assertEqual(response.status,400)
