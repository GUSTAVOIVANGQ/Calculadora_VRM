# Portal CRT VMR 5G React — distribución en contenedor v15

El frontend React de la v13, con pantalla de acceso corregida en v15 y el backend Python se publican como una sola imagen OCI mediante `Dockerfile` multi-etapa. Mantiene los endpoints, login y fórmulas de la versión base.

**Podman en Red Hat 9.7:** ver `docs/DESPLIEGUE_RHEL9_8084_V15.md`.

## Entradas principales

- `Dockerfile`: React Node 22 => imagen Python 3.13 sin Node en runtime.
- `compose.yaml`: alternativa Docker Compose.
- `compose.tls.yaml`: TLS directo sin Nginx con certificados fuera del repositorio.
- `container/quadlet/portal-crt-vmr5g.container`: servicio Podman persistente con `systemd`.
- `container/quadlet/portal-crt-vmr5g-tls.container.example`: variante HTTPS.
- `config/env.container.example`: contrato de configuración; no contiene claves válidas.

**Seguridad de referencia:** no publicar 8084 HTTP para acceso real; no usar `user/password` ni incluir secretos o SQLite en GitLab; mantener datos en volumen nuevo, revisar TLS, dependencias, SELinux y pruebas. Las sesiones viven en memoria y se cierran al recrear el contenedor.

## Compilación básica

```bash
podman build -t localhost/portal-crt-vmr5g:15 .
```

La imagen **no está precompilada en el ZIP**. El build requiere conexión al registro npm/autorización para instalar dependencias de Vite y React. Versionar `frontend/package-lock.json` cuando se genere desde un registro confiable para pasar de `npm install` a `npm ci` reproducible.


**v15:** Corrige páginas de error de login/origen/CSRF, oculta registro en el login, incluye `scripts/configurar_prueba_http.py` para pruebas internas y actualiza README del despliegue observado.
