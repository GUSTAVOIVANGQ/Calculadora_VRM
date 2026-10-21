#!/usr/bin/env python3
"""Calculadora CRT VMR 5G con login del lado del servidor.

Solo biblioteca estándar de Python. El backend escucha por defecto en
127.0.0.1:8084. Admite TLS directo; HTTP solo en red interna de prueba.
"""
import argparse
import hashlib
import hmac
import ipaddress
import json
import api
from accounts import UserStore, USER_RE
import logging
import os
import re
import secrets
import mimetypes
import ssl
import threading
import time
from collections import defaultdict, deque
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "frontend" / "dist"
COOKIE_NAME = 'vmr_session'
FILES = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/index.html': ('index.html', 'text/html; charset=utf-8'),
    '/assets/styles.css': ('assets/styles.css', 'text/css; charset=utf-8'),
    '/assets/model.js': ('assets/model.js', 'text/javascript; charset=utf-8'),
    '/assets/data.js': ('assets/data.js', 'text/javascript; charset=utf-8'),
    '/assets/controls.js': ('assets/controls.js', 'text/javascript; charset=utf-8'),
    '/assets/ui.js': ('assets/ui.js', 'text/javascript; charset=utf-8'),
    '/assets/logo-crt.png': ('assets/logo-crt.png', 'image/png'),
    '/assets/favicon.svg': ('assets/favicon.svg', 'image/svg+xml'),
    '/assets/login.css': ('assets/login.css', 'text/css; charset=utf-8'),
    '/archivos/Calculadora_VMR_5G_actualizada_15_oct.xlsx':
        ('archivos/Calculadora_VMR_5G_actualizada_15_oct.xlsx',
         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    '/robots.txt': ('robots.txt', 'text/plain; charset=utf-8'),
}
API_GET = {'/api/v1/health': 'health', '/api/v1/metadata': 'metadata', '/api/v1/defaults': 'defaults'}
API_POST = {'/api/v1/calculate': 'all', '/api/v1/calculate/vmr': 'vmr', '/api/v1/calculate/discounts': 'discounts'}
PUBLIC = {'/assets/login.css', '/assets/logo-crt.png', '/assets/favicon.svg', '/robots.txt'}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
       "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")

def frontend_asset(path):
    """Only serve Vite artifacts under frontend/dist/assets after npm run build."""
    if not path.startswith('/assets/') or not re.fullmatch(r'/assets/[a-zA-Z0-9._/-]+', path):
        return None
    candidate = (DIST / path.lstrip('/')).resolve()
    if not candidate.is_relative_to(DIST.resolve()) or not candidate.is_file():
        return None
    if candidate.suffix not in ('.js', '.css', '.svg', '.png', '.webp', '.woff2', '.jpg', '.jpeg'):
        return None
    ctype = mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream'
    if candidate.suffix in ('.js', '.css'):
        ctype += '; charset=utf-8'
    return candidate, ctype

def allowed_origin(value, host):
    """Verify cross-origin browser requests without trusting arbitrary forwarded headers."""
    if not value or value == 'null':
        return False
    try:
        u = urlsplit(value)
        if u.scheme not in ('http', 'https') or u.username or u.password or u.path not in ('', '/') or u.query or u.fragment:
            return False
        configured = os.getenv('VMR_PUBLIC_ORIGIN', '').strip()
        if configured:
            return value.rstrip('/') == configured.rstrip('/')
        expected_scheme = 'https' if os.getenv('VMR_COOKIE_SECURE', '0') == '1' else 'http'
        return bool(u.netloc and u.netloc.lower() == host.lower() and u.scheme == expected_scheme)
    except ValueError:
        return False

_HASH_RE = re.compile(r'^pbkdf2_sha256\$(\d{5,8})\$([a-fA-F0-9]{32})\$([a-fA-F0-9]{64})$')


class Auth:
    def __init__(self, user, stored_hash, cookie_secure=True, hours=8):
        match = _HASH_RE.fullmatch(stored_hash)
        if not user or not match or not (100000 <= int(match.group(1)) <= 3000000):
            raise ValueError('Configure VMR_AUTH_USER y VMR_PASSWORD_HASH válidos antes de iniciar.')
        self.user = user
        self.iterations = int(match.group(1))
        self.salt = bytes.fromhex(match.group(2))
        self.digest = bytes.fromhex(match.group(3))
        self.cookie_secure = cookie_secure
        self.ttl = max(1, min(24, int(hours))) * 3600
        self.sessions = {}
        self.login_tokens = {}
        self.failures = defaultdict(deque)
        self.lock = threading.RLock()
        self.csrf_key = secrets.token_bytes(32)
        self.users = None
        self.registration_hash = ''
        self.registration_failures = defaultdict(deque)

    @classmethod
    def from_env(cls):
        # El EnvironmentFile de systemd admite comillas exteriores; algunos
        # runtimes OCI las preservan al importar el archivo mediante --env-file.
        # Aceptar solo las comillas de envoltura, sin alterar el hash validado.
        stored_hash = os.getenv('VMR_PASSWORD_HASH', '').strip()
        if len(stored_hash) >= 2 and stored_hash[0] == stored_hash[-1] and stored_hash[0] in ('\"', "'"):
            stored_hash = stored_hash[1:-1]
        auth = cls(os.getenv('VMR_AUTH_USER', ''), stored_hash,
                   os.getenv('VMR_COOKIE_SECURE', '1') != '0',
                   os.getenv('VMR_SESSION_HOURS', '8'))
        db_path = os.getenv('VMR_USERS_DB', '/var/lib/crt-vmr-5g/users.sqlite3')
        auth.users = UserStore(db_path)
        reg_hash = os.getenv('VMR_REGISTRATION_CODE_HASH', '').strip()
        if reg_hash and not re.fullmatch(r'[a-f0-9]{64}', reg_hash):
            raise ValueError('VMR_REGISTRATION_CODE_HASH debe ser un SHA-256 hexadecimal.')
        auth.registration_hash = reg_hash
        return auth

    def verify(self, user, password):
        # El hash se calcula siempre, incluso si el nombre de usuario es incorrecto.
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                    self.salt, self.iterations)
        admin_valid = hmac.compare_digest(digest, self.digest) and hmac.compare_digest(user.encode('utf-8'), self.user.encode('utf-8'))
        if admin_valid:
            return True
        return bool(self.users and len(password) <= 1024 and self.users.verify(user, password))

    @property
    def can_register(self):
        return bool(self.users and self.registration_hash)

    def create_account(self, user, password, confirmation, invitation):
        if not self.can_register or not USER_RE.fullmatch(user) or len(password) < 12 or len(password) > 1024:
            return False
        if not hmac.compare_digest(password, confirmation) or len(invitation) > 256:
            return False
        invitation_hash = hashlib.sha256(invitation.encode('utf-8')).hexdigest()
        if not hmac.compare_digest(invitation_hash, self.registration_hash):
            return False
        return self.users.add(user, password, self.user)

    def new_login_token(self):
        now = time.time()
        with self.lock:
            self.login_tokens = {k: t for k, t in self.login_tokens.items() if now - t < 900}
            if len(self.login_tokens) > 2000:
                self.login_tokens.clear()
            token = secrets.token_urlsafe(32)
            self.login_tokens[token] = now
        return token

    def use_login_token(self, token):
        with self.lock:
            start = self.login_tokens.pop(token, None)
            return start is not None and time.time() - start < 900

    def too_many_attempts(self, ip):
        now = time.time()
        with self.lock:
            history = self.failures[ip]
            while history and now - history[0] > 600:
                history.popleft()
            return len(history) >= 5

    def record_failure(self, ip):
        with self.lock:
            self.failures[ip].append(time.time())

    def clear_failures(self, ip):
        with self.lock:
            self.failures.pop(ip, None)

    def new_session(self):
        now = time.time()
        with self.lock:
            for sid, expires in list(self.sessions.items()):
                if expires < now:
                    self.sessions.pop(sid, None)
            sid = secrets.token_urlsafe(48)
            self.sessions[sid] = now + self.ttl
        return sid

    def is_active(self, sid):
        if not sid:
            return False
        with self.lock:
            expiry = self.sessions.get(sid, 0)
            if expiry <= time.time():
                self.sessions.pop(sid, None)
                return False
            return True

    def revoke(self, sid):
        with self.lock:
            self.sessions.pop(sid, None)

    def logout_csrf(self, sid):
        return hmac.new(self.csrf_key, sid.encode('utf-8'), hashlib.sha256).hexdigest()

    def cookie(self, value, delete=False):
        parts = [COOKIE_NAME + '=' + value, 'Path=/', 'HttpOnly', 'SameSite=Strict']
        if self.cookie_secure:
            parts.append('Secure')
        if delete:
            parts.extend(['Max-Age=0', 'Expires=Thu, 01 Jan 1970 00:00:00 GMT'])
        else:
            parts.append('Max-Age=' + str(self.ttl))
        return '; '.join(parts)


class Handler(BaseHTTPRequestHandler):
    server_version = 'VMR5G'
    sys_version = ''

    @property
    def auth(self):
        return self.server.auth

    def _headers(self, status, ctype, length, cookie=None, location=None):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(length))
        self.send_header('Cache-Control', 'no-store, private')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        # 'no-referrer' hace que Chrome/Edge envíen Origin: null en POST de
        # formularios HTML. 'same-origin' preserva el origen en /login y
        # no comparte Referer con sitios externos. Origin y CSRF se validan igual.
        self.send_header('Referrer-Policy', 'same-origin')
        self.send_header('Permissions-Policy', 'geolocation=(), camera=(), microphone=()')
        self.send_header('Content-Security-Policy', CSP)
        if os.getenv('VMR_ENABLE_HSTS', '0') == '1' and os.getenv('VMR_COOKIE_SECURE', '0') == '1':
            self.send_header('Strict-Transport-Security', 'max-age=31536000')
        if location:
            self.send_header('Location', location)
        if cookie is not None:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()

    def _send(self, status, body=b'', ctype='text/plain; charset=utf-8', head=False,
              cookie=None, location=None):
        self._headers(status, ctype, len(body), cookie=cookie, location=location)
        if not head and body:
            self.wfile.write(body)

    def _redirect(self, target, cookie=None, status=303):
        self._send(status, cookie=cookie, location=target)

    def _session_id(self):
        try:
            cookie = SimpleCookie()
            cookie.load(self.headers.get('Cookie', ''))
            return cookie[COOKIE_NAME].value if COOKIE_NAME in cookie else ''
        except Exception:
            return ''

    def _remote_ip(self):
        peer = self.client_address[0]
        # Solo se confía en cabeceras del proxy cuando conecta desde loopback.
        if os.getenv('VMR_TRUST_PROXY', '0') == '1' and peer in ('127.0.0.1', '::1'):
            proposed = self.headers.get('X-Real-IP', '')
            try:
                return str(ipaddress.ip_address(proposed))
            except ValueError:
                pass
        return peer

    def _login_page(self, error=False, head=False, status=None, message=None):
        """Siempre mostrar el formulario original, también después de un error.

        Los rechazos de Origin y CSRF permanecen activos; no se presentan como
        credenciales incorrectas porque todavía no se intentó autenticación.
        """
        import html
        raw = (ROOT / 'login.html').read_text(encoding='utf-8')
        raw = raw.replace('__CSRF_TOKEN__', self.auth.new_login_token())
        if error and message is None:
            message = 'Usuario o contraseña incorrectos. Comprueba los datos e inténtalo nuevamente.'
        alert = ('<p class="auth-error" role="alert">' + html.escape(message, quote=True) + '</p>'
                 if message else '')
        raw = raw.replace('__LOGIN_ERROR__', alert)
        code = status if status is not None else (401 if error else 200)
        self._send(code, raw.encode('utf-8'), 'text/html; charset=utf-8', head=head)

    def _auth_failure_page(self, reason, head=False):
        """Errores en el mismo formulario con código HTTP y controles intactos."""
        presentations = {
            'credentials': (401, 'Usuario o contraseña incorrectos. Comprueba los datos e inténtalo nuevamente.'),
            'origin': (403, 'No pudimos validar el inicio de sesión. Abre el portal desde su dirección oficial y vuelve a intentarlo.'),
            'expired': (403, 'El formulario venció. Vuelve a ingresar tus datos en este formulario.'),
            'rate': (429, 'Demasiados intentos de acceso. Inténtalo más tarde.'),
        }
        status, message = presentations[reason]
        return self._login_page(head=head, status=status, message=message)

    def _register_page(self, error=False, head=False):
        raw = (ROOT / 'register.html').read_text(encoding='utf-8')
        raw = raw.replace('__CSRF_TOKEN__', self.auth.new_login_token())
        raw = raw.replace('__REGISTER_DISABLED__', '' if self.auth.can_register else
                          '<p class="auth-error" role="alert">El administrador todavía no ha habilitado las invitaciones.</p>')
        raw = raw.replace('__REGISTER_ERROR__',
                          '<p class="auth-error" role="alert">No se pudo crear la cuenta. Revisa el nombre de usuario, contraseña y código de invitación.</p>'
                          if error else '')
        raw = raw.replace('__REGISTER_BUTTON_DISABLED__', '' if self.auth.can_register else 'disabled')
        self._send(400 if error else 200, raw.encode('utf-8'), 'text/html; charset=utf-8', head=head)

    def _send_json(self, status, payload, head=False, cookie=None):
        body = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
        return self._send(status, body, 'application/json; charset=utf-8', head=head, cookie=cookie)

    def _api_auth_post(self, path):
        if self.headers.get('Content-Type', '').split(';', 1)[0].strip().lower() != 'application/json':
            return self._send_json(415, {'error': 'Se requiere application/json'})
        try:
            size = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            size = -1
        if not 0 < size <= 4096:
            return self._send_json(413, {'error': 'Cuerpo demasiado grande o vacio'})
        try:
            data = json.loads(self.rfile.read(size).decode('utf-8', 'strict'))
        except (ValueError, UnicodeDecodeError):
            return self._send_json(400, {'error': 'JSON invalido'})
        if not isinstance(data, dict):
            return self._send_json(400, {'error': 'Se esperaba un objeto JSON'})
        token = data.get('csrf')
        if not isinstance(token, str) or not self.auth.use_login_token(token):
            return self._send_json(403, {'error': 'Token CSRF invalido o expirado'})
        username = data.get('username')
        password = data.get('password')
        if not isinstance(username, str) or not isinstance(password, str):
            return self._send_json(400, {'error': 'Usuario y contrasena obligatorios'})
        ip = self._remote_ip()
        if path.endswith('/register'):
            if not self.auth.can_register:
                return self._send_json(403, {'error': 'Registro no habilitado'})
            now = time.time()
            with self.auth.lock:
                hits = self.auth.registration_failures[ip]
                while hits and now - hits[0] > 600:
                    hits.popleft()
                limited = len(hits) >= 5
            if limited:
                return self._send_json(429, {'error': 'Espere diez minutos'})
            confirm = data.get('confirmPassword')
            invitation = data.get('inviteCode')
            if not isinstance(confirm, str) or not isinstance(invitation, str) or not self.auth.create_account(username.strip(), password, confirm, invitation):
                with self.auth.lock:
                    self.auth.registration_failures[ip].append(time.time())
                return self._send_json(400, {'error': 'No se pudo crear la cuenta; revise datos e invitacion'})
            with self.auth.lock:
                self.auth.registration_failures.pop(ip, None)
            sid = self.auth.new_session()
            return self._send_json(201, {'ok': True, 'redirect': '/'}, cookie=self.auth.cookie(sid))
        if self.auth.too_many_attempts(ip):
            return self._send_json(429, {'error': 'Demasiados intentos; espere diez minutos'})
        if len(username) > 160 or len(password) > 1024 or not self.auth.verify(username, password):
            self.auth.record_failure(ip)
            return self._send_json(401, {'error': 'Usuario o contrasena incorrectos'})
        self.auth.clear_failures(ip)
        sid = self.auth.new_session()
        return self._send_json(200, {'ok': True, 'redirect': '/'}, cookie=self.auth.cookie(sid))

    def _api_post(self, path):
        sid = self._session_id()
        if not self.auth.is_active(sid):
            return self._send_json(401, {'error': 'Autenticacion necesaria'})
        # Mandatory session-bound CSRF header on cookie-authenticated JSON calculations.
        token = self.headers.get('X-VMR-CSRF', '')
        if not token or not hmac.compare_digest(token, self.auth.logout_csrf(sid)):
            return self._send_json(403, {'error': 'Token CSRF requerido'})
        ctype = self.headers.get('Content-Type', '').split(';', 1)[0].lower().strip()
        if ctype != 'application/json':
            return self._send_json(415, {'error':'Se requiere Content-Type: application/json'})
        try:
            size = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            size = -1
        if not 0 < size <= 131072:
            return self._send_json(413, {'error':'El cuerpo debe ocupar entre 1 y 131072 bytes'})
        try:
            obj = json.loads(self.rfile.read(size).decode('utf-8', 'strict'),
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Número no finito')))
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            return self._send_json(400, {'error':'JSON inválido'})
        try:
            if not isinstance(obj, dict) or set(obj.keys()) != {'scenario'}:
                raise api.BadScenario('Use un objeto JSON con la propiedad scenario.')
            result = api.response(API_POST[path], obj['scenario'])
            return self._send_json(200, result)
        except (api.BadScenario, ValueError, ZeroDivisionError, OverflowError) as exc:
            return self._send_json(422, {'error':str(exc)})

    def _serve(self, head=False):
        path = urlsplit(self.path).path
        if path == '/healthz':
            return self._send(200, b'ok\n', head=head)
        if path == '/api/v1/auth/csrf':
            return self._send_json(200, {'csrf': self.auth.new_login_token()}, head=head)
        if path == '/api/v1/auth/session':
            sid = self._session_id()
            if not self.auth.is_active(sid):
                return self._send_json(401, {'authenticated': False}, head=head)
            return self._send_json(200, {'authenticated': True,
                                         'csrf': self.auth.logout_csrf(sid)}, head=head)
        if path == '/api/v1/readiness':
            # Internal non-sensitive check: exists but never reveals credentials.
            return self._send_json(200 if DIST.joinpath('index.html').is_file() else 503,
                                   {'ready': DIST.joinpath('index.html').is_file()}, head=head)
        if path == '/api/v1/auth/status':
            return self._send_json(200, {'authenticated': self.auth.is_active(self._session_id()),
                                         'registrationEnabled': self.auth.can_register}, head=head)
        if path in API_GET:
            if path != '/api/v1/health' and not self.auth.is_active(self._session_id()):
                return self._send_json(401, {'error':'Autenticacion necesaria'}, head=head)
            return self._send_json(200, api.response(API_GET[path]), head=head)
        sid = self._session_id()
        logged_in = self.auth.is_active(sid)
        if path == '/login':
            if logged_in:
                return self._redirect('/')
            return self._login_page(head=head)
        if path in ('/register', '/crear-cuenta'):
            if logged_in:
                return self._redirect('/')
            return self._register_page(head=head)
        entry = FILES.get(path)
        artifact = frontend_asset(path)
        if path in ('/', '/index.html'):
            if not DIST.joinpath('index.html').is_file():
                return self._send(503, b'Frontend sin compilar: cd frontend && npm install && npm run build\n', head=head)
            entry = ('frontend/dist/index.html', 'text/html; charset=utf-8')
        elif artifact:
            entry = (str(artifact[0].relative_to(ROOT)), artifact[1])
        if not entry:
            return self._send(404, 'No encontrado\n'.encode('utf-8'), head=head)
        if not logged_in and path not in PUBLIC:
            if path in ('/', '/index.html'):
                return self._redirect('/login', status=302)
            return self._send(401, b'Autenticacion necesaria\n', head=head)
        name, ctype = entry
        try:
            body = (DIST / 'index.html').read_bytes() if path in ('/', '/index.html') else (ROOT / name).read_bytes()
        except OSError:
            return self._send(404, b'No encontrado\n', head=head)
        if name == 'legacy-index.html':
            csrf = self.auth.logout_csrf(sid)
            logout = ('<div class="session-actions"><span>Acceso autorizado</span>'
                      '<form action="/logout" method="post">'
                      '<input type="hidden" name="csrf" value="' + csrf + '">'
                      '<button class="logout-button" type="submit">Cerrar sesión</button>'
                      '</form></div>')
            body = body.replace(b'<!-- SERVER_LOGOUT -->', logout.encode('utf-8'))
        return self._send(200, body, ctype, head=head)

    def do_GET(self):
        self._serve(False)

    def do_HEAD(self):
        self._serve(True)

    def do_POST(self):
        path = urlsplit(self.path).path
        # Block cross-site POSTs (SameSite=Strict alone is not full CSRF protection).
        origin = self.headers.get('Origin')
        if origin is not None and not allowed_origin(origin, self.headers.get('Host', '')):
            # Se registran solo metadatos de la petición, nunca usuario, contraseña,
            # token CSRF ni Cookie. Resulta útil para distinguir errores de Edge/Chrome.
            logging.warning('Origen rechazado path=%s host=%r origin=%r esperado=%r',
                            path, self.headers.get('Host', '')[:128],
                            origin[:128], os.getenv('VMR_PUBLIC_ORIGIN', '')[:128])
            return (self._send_json(403, {'error': 'No fue posible validar la solicitud'}) if path.startswith('/api/') else
                    self._auth_failure_page('origin') if path in ('/login', '/logout', '/register', '/crear-cuenta') else
                    self._send(403, b'Solicitud no valida\n'))
        if self.headers.get('Sec-Fetch-Site', '').lower() == 'cross-site':
            logging.warning('Solicitud entre sitios rechazada path=%s site=cross-site', path)
            return (self._auth_failure_page('origin') if path in ('/login', '/logout', '/register', '/crear-cuenta')
                    else self._send(403, b'Solicitud no valida\n'))
        if path in ('/api/v1/auth/login', '/api/v1/auth/register'):
            return self._api_auth_post(path)
        if path in API_POST:
            return self._api_post(path)
        if path not in ('/login', '/logout', '/register', '/crear-cuenta'):
            return self._reject()
        ctype = self.headers.get('Content-Type', '').split(';', 1)[0].lower().strip()
        try:
            size = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            size = -1
        if ctype != 'application/x-www-form-urlencoded' or size < 0 or size > 4096:
            return self._send(400, b'Solicitud incorrecta\n')
        try:
            body = self.rfile.read(size).decode('utf-8', 'strict')
            params = parse_qs(body, keep_blank_values=True, max_num_fields=8)
        except (UnicodeDecodeError, ValueError):
            return self._send(400, b'Solicitud incorrecta\n')
        val = lambda key: params.get(key, [''])[0]
        if path == '/logout':
            sid = self._session_id()
            if not self.auth.is_active(sid):
                return self._redirect('/login', cookie=self.auth.cookie('', delete=True))
            if not hmac.compare_digest(val('csrf').encode('utf-8'), self.auth.logout_csrf(sid).encode('ascii')):
                return self._auth_failure_page('expired')
            self.auth.revoke(sid)
            return self._redirect('/login', cookie=self.auth.cookie('', delete=True))
        token = val('csrf')
        if not token or not self.auth.use_login_token(token):
            return self._auth_failure_page('expired')
        ip = self._remote_ip()
        if path in ('/register', '/crear-cuenta'):
            if not self.auth.can_register:
                return self._send(403, b'Creacion de cuentas no habilitada\n')
            now = time.time()
            with self.auth.lock:
                hits = self.auth.registration_failures[ip]
                while hits and now - hits[0] > 600:
                    hits.popleft()
                limited = len(hits) >= 5
            if limited:
                return self._send(429, b'Demasiados intentos; espere diez minutos\n')
            user = val('username').strip()
            password = val('password')
            success = self.auth.create_account(user, password, val('confirm_password'), val('invite_code'))
            if not success:
                with self.auth.lock:
                    self.auth.registration_failures[ip].append(time.time())
                return self._register_page(error=True)
            with self.auth.lock:
                self.auth.registration_failures.pop(ip, None)
            sid = self.auth.new_session()
            return self._redirect('/', cookie=self.auth.cookie(sid))
        if self.auth.too_many_attempts(ip):
            return self._auth_failure_page('rate')
        user, password = val('username'), val('password')
        if len(password) > 1024 or len(user) > 160 or not self.auth.verify(user, password):
            self.auth.record_failure(ip)
            return self._auth_failure_page('credentials')
        self.auth.clear_failures(ip)
        sid = self.auth.new_session()
        return self._redirect('/', cookie=self.auth.cookie(sid))

    def _reject(self):
        self.send_response(405)
        self.send_header('Allow', 'GET, HEAD, POST /login, POST /logout, POST /register')
        self.send_header('Content-Length', '0')
        self.end_headers()

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _reject

    def log_message(self, fmt, *args):
        logging.info('%s %s', self.address_string(), fmt % args)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bind', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8084)
    ap.add_argument('--tls-cert', help='Certificado PEM para HTTPS directo, sin proxy')
    ap.add_argument('--tls-key', help='Llave privada PEM correspondiente')
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    try:
        auth = Auth.from_env()
    except (ValueError, TypeError) as exc:
        ap.error(str(exc))
    srv = ThreadingHTTPServer((args.bind, args.port), Handler)
    if bool(args.tls_cert) != bool(args.tls_key):
        ap.error('Para habilitar HTTPS debe indicar ambos: --tls-cert y --tls-key')
    if args.tls_cert:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(args.tls_cert, args.tls_key)
        srv.socket = context.wrap_socket(srv.socket, server_side=True)
    srv.auth = auth
    srv.daemon_threads = True
    logging.info('Calculadora CRT en %s://%s:%d/', 'https' if args.tls_cert else 'http', args.bind, args.port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == '__main__':
    main()
