#!/usr/bin/env python3
"""Habilita o deshabilita registro con invitación SIN cambiar usuario/password actuales.

Ejemplo: sudo python3 setup_registration.py --env /etc/crt-vmr-5g.env
El código de invitación se imprime una sola vez y solo se guarda su SHA-256.
"""
import argparse
import hashlib
import os
import secrets
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env', default='/etc/crt-vmr-5g.env', help='EnvironmentFile actual de systemd')
    parser.add_argument('--disable', action='store_true', help='Deshabilitar nuevos registros')
    args = parser.parse_args()
    dest = Path(args.env).resolve()
    if not dest.is_file():
        parser.error('No existe el archivo de entorno. Conserve el anterior y configure primero create_login.py.')
    lines = dest.read_text(encoding='utf-8').splitlines()
    lines = [line for line in lines if not line.startswith('VMR_REGISTRATION_CODE_HASH=')]
    code = None
    if not args.disable:
        code = secrets.token_urlsafe(32)
        digest = hashlib.sha256(code.encode('utf-8')).hexdigest()
        lines.append('VMR_REGISTRATION_CODE_HASH=' + digest)
    fd, tmp = tempfile.mkstemp(prefix='.vmr-registration-', dir=str(dest.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        os.replace(tmp, str(dest))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if code:
        print('Registro habilitado. Código de invitación (guárdelo, solo se muestra ahora):')
        print(code)
        print('Distribúyalo únicamente a personas autorizadas. Reinicie el servicio.')
    else:
        print('Registro de cuentas deshabilitado. Las cuentas existentes continúan funcionando.')


if __name__ == '__main__':
    main()
