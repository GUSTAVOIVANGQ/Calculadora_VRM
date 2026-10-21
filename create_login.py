#!/usr/bin/env python3
"""Genera /etc/crt-vmr-5g.env sin contraseñas en claro y sin dependencias pip."""
import argparse
import getpass
import hashlib
import os
import re
import secrets
import tempfile
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--username', required=True, help='Usuario que ingresará en el login')
    ap.add_argument('--output', default='/etc/crt-vmr-5g.env', help='Ruta absoluta del archivo privado')
    ap.add_argument('--replace', action='store_true', help='Reemplazar credenciales existentes')
    args = ap.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.@-]{3,64}', args.username):
        ap.error('El usuario debe tener entre 3 y 64 caracteres: letras, números, _ . @ -')
    dest = Path(args.output)
    if not dest.is_absolute():
        ap.error('--output debe ser una ruta absoluta')
    if dest.exists() and not args.replace:
        ap.error('El archivo ya existe. Para rotar la clave agregue --replace.')
    pw1 = getpass.getpass('Contraseña nueva (mínimo 12 caracteres): ')
    pw2 = getpass.getpass('Confirmar contraseña: ')
    if pw1 != pw2 or len(pw1) < 12 or len(pw1) > 1024:
        ap.error('Las contraseñas deben coincidir y tener entre 12 y 1024 caracteres.')
    rounds = 310000
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac('sha256', pw1.encode('utf-8'), salt, rounds)
    data = ('VMR_AUTH_USER=' + args.username + '\n' +
            "VMR_PASSWORD_HASH='pbkdf2_sha256$" + str(rounds) + '$' + salt.hex() + '$' + hashed.hex() + "'\n" +
            'VMR_COOKIE_SECURE=1\nVMR_SESSION_HOURS=8\n')
    # Escritura atómica y modo privado incluso si la instalación ya estaba activa.
    fd, temporary = tempfile.mkstemp(prefix='.crt-vmr-', dir=str(dest.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            output.write(data)
        os.replace(temporary, str(dest))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print('Credenciales cifradas mediante hash guardadas en ' + str(dest))
    print('No hay contraseña inicial en el ZIP. Reinicie crt-vmr-5g para aplicar los cambios.')


if __name__ == '__main__':
    main()
