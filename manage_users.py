#!/usr/bin/env python3
"""Administración local de cuentas registradas (no cambia la cuenta principal del .env)."""
import argparse
import getpass
import sqlite3
from accounts import UserStore, USER_RE, hash_password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='/var/lib/crt-vmr-5g/users.sqlite3')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true')
    group.add_argument('--reset-password', metavar='USUARIO')
    group.add_argument('--delete', metavar='USUARIO')
    args = parser.parse_args()
    store = UserStore(args.db)
    with store._connect() as db:
        if args.list:
            for row in db.execute('SELECT username FROM users ORDER BY username COLLATE NOCASE'):
                print(row[0])
        elif args.reset_password:
            user = args.reset_password
            if not USER_RE.fullmatch(user):
                parser.error('Nombre de usuario invalido')
            pwd1 = getpass.getpass('Nueva contrasena (12 a 1024 caracteres): ')
            pwd2 = getpass.getpass('Confirmar nueva contrasena: ')
            if len(pwd1) < 12 or len(pwd1) > 1024 or pwd1 != pwd2:
                parser.error('Contrasenas no validas o diferentes')
            result = db.execute('UPDATE users SET password_hash=? WHERE username=?', (hash_password(pwd1), user))
            if result.rowcount != 1:
                parser.error('La cuenta no existe en la base de registros')
            print('Contrasena actualizada para ' + user)
        else:
            user = args.delete
            if not USER_RE.fullmatch(user):
                parser.error('Nombre de usuario invalido')
            result = db.execute('DELETE FROM users WHERE username=?', (user,))
            print('Cuentas eliminadas:',result.rowcount)
            print('Reinicie el servicio para invalidar las sesiones ya iniciadas.')


if __name__ == '__main__':
    main()
