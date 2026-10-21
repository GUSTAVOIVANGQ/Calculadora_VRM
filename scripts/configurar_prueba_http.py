#!/usr/bin/env python3
"""CONFIGURACIÓN DE PRUEBAS EN LAN: credenciales interactivas, nunca en Git.

No usar en producción ni en redes sin aislamiento. Actualiza de forma atómica
/etc/crt-vmr-5g.env y conserva variables ajenas (p. ej. registro SQLite).
"""
import argparse
import getpass
import hashlib
import ipaddress
import os
import re
import secrets
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True,
                        help='HTTP de red privada, por ejemplo http://172.17.42.163:8084')
    parser.add_argument('--username', default='user')
    parser.add_argument('--env', default='/etc/crt-vmr-5g.env')
    parser.add_argument('--accept-insecure-http-test', action='store_true', required=True,
                        help='Acepto que HTTP y contraseñas débiles no son aptos para producción')
    args = parser.parse_args()
    try:
        url = urlsplit(args.origin)
        host = ipaddress.ip_address(url.hostname or '')
        assert url.scheme == 'http' and host.is_private and url.port == 8084
        assert not url.username and not url.password and url.path in ('', '/')
        assert not url.query and not url.fragment
    except (ValueError, AssertionError):
        parser.error('La URL debe ser http://IP-PRIVADA:8084 sin ruta, query ni credenciales')
    if not re.fullmatch(r'[A-Za-z0-9_.@-]{3,64}', args.username):
        parser.error('Usuario inválido')
    env_path = Path(args.env)
    if not env_path.is_absolute() or not env_path.parent.is_dir():
        parser.error('El archivo .env debe estar en un directorio existente y ser una ruta absoluta')
    p1 = getpass.getpass('Contraseña de PRUEBA (puede ser password; no para producción): ')
    p2 = getpass.getpass('Confirmar contraseña de PRUEBA: ')
    if p1 != p2 or not 1 <= len(p1) <= 1024:
        parser.error('Contraseñas diferentes o longitud inválida')
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac('sha256', p1.encode(), salt, 310000)
    value = f'pbkdf2_sha256$310000${salt.hex()}${hashed.hex()}'
    changes = {
        'VMR_AUTH_USER': args.username,
        'VMR_PASSWORD_HASH': "'" + value + "'",
        'VMR_PUBLIC_ORIGIN': args.origin.rstrip('/'),
        'VMR_COOKIE_SECURE': '0',
        'VMR_ENABLE_HSTS': '0',
        'VMR_TRUST_PROXY': '0',
    }
    current = env_path.read_text(encoding='utf-8').splitlines() if env_path.exists() else []
    if env_path.exists():
        if env_path.is_symlink():
            parser.error('No se modifica archivo .env enlazado')
        backup = env_path.with_name(env_path.name + '.bak-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        shutil.copy2(env_path, backup)
        backup.chmod(0o600)
    found = set()
    result = []
    for line in current:
        match = re.match(r'^([A-Za-z][A-Za-z0-9_]*)=', line)
        if match and match.group(1) in changes:
            key = match.group(1)
            if key not in found:
                result.append(key + '=' + changes[key])
            found.add(key)
        else:
            result.append(line)
    for key, val in changes.items():
        if key not in found:
            result.append(key + '=' + val)
    fd, tmp = tempfile.mkstemp(prefix='.vmr-private-', dir=env_path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            output.write('\n'.join(result) + '\n')
        os.replace(tmp, env_path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print('Configuración de PRUEBA guardada con permisos 0600 en', env_path)
    print('Usuario:', args.username, '| Origen:', args.origin.rstrip('/'))
    print('Contraseña no mostrada ni almacenada en texto claro.')
    print('Aplicar: sudo systemctl restart portal-crt-vmr5g.service')
    print('AVISO: cambie la contraseña y habilite HTTPS antes de publicar mediante DNS.')


if __name__ == '__main__':
    main()
