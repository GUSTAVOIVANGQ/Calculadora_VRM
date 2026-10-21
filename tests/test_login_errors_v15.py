"""Pruebas de páginas de error y de la comprobación de Origin real."""
import hashlib
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import server


class LoginErrorV15Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        salt=bytes.fromhex('aa'*16)
        digest=hashlib.pbkdf2_hmac('sha256',b'clave-valida-prueba',salt,100001)
        cls.auth=server.Auth('usuario',f'pbkdf2_sha256$100001${salt.hex()}${digest.hex()}',cookie_secure=False)
        cls.srv=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.srv.auth=cls.auth
        cls.base=f'http://127.0.0.1:{cls.srv.server_address[1]}'
        cls.thread=threading.Thread(target=cls.srv.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown();cls.srv.server_close();cls.thread.join(timeout=3)
    def setUp(self):
        self.auth.failures.clear()
        self.env=patch.dict('os.environ',{'VMR_PUBLIC_ORIGIN':self.base,'VMR_COOKIE_SECURE':'0'})
        self.env.start()
    def tearDown(self):
        self.env.stop()
    def token(self):
        with urllib.request.urlopen(self.base+'/login') as resp:
            html=resp.read().decode()
            self.assertNotIn('Registrarme',html)
        return re.search(r'name="csrf" value="([^"]+)"',html).group(1)
    def post(self,password,origin=None,csrf=None):
        data=urllib.parse.urlencode({'username':'usuario','password':password,'csrf':csrf or self.token()}).encode()
        headers={'Content-Type':'application/x-www-form-urlencoded'}
        if origin:
            headers['Origin']=origin
        req=urllib.request.Request(self.base+'/login',data=data,headers=headers)
        try:
            return urllib.request.urlopen(req)
        except urllib.error.HTTPError as err:
            return err
    def test_wrong_password_shows_styled_crt_error(self):
        r=self.post('incorrecta',self.base)
        self.assertEqual(r.status,401)
        page=r.read().decode()
        self.assertIn('Usuario o contraseña incorrectos',page)
        self.assertIn('data:image/png;base64,',page)
        self.assertIn('Iniciar sesión',page)
        self.assertNotIn('Traceback',page)
    def test_cross_origin_rejected_as_styled_page(self):
        r=self.post('clave-valida-prueba','http://untrusted.example')
        self.assertEqual(r.status,403)
        self.assertIn('No pudimos validar el inicio de sesión',r.read().decode())
    def test_bad_csrf_uses_styled_page(self):
        r=self.post('clave-valida-prueba',self.base,csrf='mala')
        self.assertEqual(r.status,403)
        self.assertIn('El formulario venció',r.read().decode())
    def test_ip_origin_valid_redirect_and_session(self):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        data=urllib.parse.urlencode({'username':'usuario','password':'clave-valida-prueba','csrf':self.token()}).encode()
        request=urllib.request.Request(self.base+'/login',data=data,
                                        headers={'Origin':self.base,'Content-Type':'application/x-www-form-urlencoded'})
        opener=urllib.request.build_opener(NoRedirect)
        try:
            opener.open(request)
        except urllib.error.HTTPError as err:
            self.assertEqual(err.status,303)
            self.assertEqual(err.headers['Location'],'/')
            self.assertIn('HttpOnly',err.headers['Set-Cookie'])
        else:
            self.fail('Debió redirigir después de autenticarse')

