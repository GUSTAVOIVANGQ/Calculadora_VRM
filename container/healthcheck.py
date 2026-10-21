#!/usr/bin/env python3
"""Sondeo local de disponibilidad; NO sustituye la verificación TLS externa."""
import os
import ssl
import sys
from urllib.request import urlopen

scheme = 'https' if os.environ.get('VMR_CONTAINER_TLS') == '1' else 'http'
url = scheme + '://127.0.0.1:8084/api/v1/readiness'
# TLS directo: el certificado institucional habitualmente no incluye 127.0.0.1.
# Esta comprobación de loopback es solo de disponibilidad; TLS público se valida
# por separado mediante curl al FQDN con su CA de confianza.
context = ssl._create_unverified_context() if scheme == 'https' else None
try:
    with urlopen(url, timeout=3, context=context) as response:
        sys.exit(0 if response.status == 200 else 1)
except Exception:
    sys.exit(1)
