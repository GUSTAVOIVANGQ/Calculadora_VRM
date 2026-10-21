"""Almacén local de usuarios para CRT VMR 5G, sin dependencias externas.

La cuenta administrativa ya existente continúa en VMR_AUTH_USER/VMR_PASSWORD_HASH.
Las cuentas nuevas se guardan en una base SQLite privada (0600) fuera de /opt.
"""
import hashlib
import hmac
import re
import sqlite3
from contextlib import contextmanager
import time
from pathlib import Path

USER_RE = re.compile(r'^[A-Za-z0-9_.@-]{3,64}$')
HASH_RE = re.compile(r'^pbkdf2_sha256\$(\d{5,8})\$([a-f0-9]{32})\$([a-f0-9]{64})$')
ITERATIONS = 310000


def hash_password(password, salt=None):
    import secrets
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password, stored):
    match = HASH_RE.fullmatch(stored or '')
    if not match:
        return False
    iters, salt, digest = match.groups()
    candidate = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), int(iters))
    return hmac.compare_digest(candidate, bytes.fromhex(digest))


class UserStore:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        if not self.path.parent.exists():
            raise ValueError(f'No existe el directorio privado de usuarios: {self.path.parent}')
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )''')

    @contextmanager
    def _connect(self):
        # Crear el archivo con 0600 sin alterar el umask global del servidor multihilo.
        import os
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        db = sqlite3.connect(str(self.path), timeout=5)
        # No sobrescribir permisos existentes; un archivo en 0644 es inseguro.
        import stat
        if stat.S_IMODE(self.path.stat().st_mode) & 0o077:
            db.close()
            raise ValueError('La base de usuarios debe tener permisos 0600; ejecute chmod 600')
        try:
            with db:
                yield db
        finally:
            db.close()

    def verify(self, username, password):
        if not USER_RE.fullmatch(username):
            return False
        with self._connect() as db:
            row = db.execute('SELECT password_hash FROM users WHERE username = ?', (username,)).fetchone()
        if not row:
            return False
        return verify_password(password, row[0])

    def add(self, username, password, reserved_username):
        if not USER_RE.fullmatch(username) or username.casefold() == reserved_username.casefold():
            return False
        with self._connect() as db:
            try:
                db.execute('INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)',
                           (username, hash_password(password), int(time.time())))
            except sqlite3.IntegrityError:
                return False
        return True
