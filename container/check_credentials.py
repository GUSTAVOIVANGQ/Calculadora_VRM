#!/usr/bin/env python3
"""Comprobar una cuenta interactivamente dentro del contenedor.

No se imprime contraseña, hash ni secretos; no modifica usuarios.
Ejemplo: sudo podman exec -it portal-crt-vmr5g python container/check_credentials.py
"""
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Auth


def main():
    username = input('Usuario que desea verificar: ').strip()
    password = getpass.getpass('Contraseña (no se mostrará): ')
    try:
        auth = Auth.from_env()
        ok = auth.verify(username, password)
    except (ValueError, OSError) as exc:
        print('Configuración o acceso a base de datos no disponible. Revise el servicio.')
        return 2
    print('Credenciales válidas en este contenedor.' if ok else
          'Credenciales no válidas en este contenedor. Revise la cuenta y el último cambio de configuración.')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
