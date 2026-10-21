# Versión 17 — corrección raíz del formulario de login

**Evidencia del servidor en Red Hat (21/10/2026):** `Origen rechazado path=/login host='172.17.42.163:8084' origin='null' esperado='http://172.17.42.163:8084'`. La autenticación local del usuario de pruebas respondió `Credenciales válidas en este contenedor.`

## Ajuste realizado

- `server.py`: `Referrer-Policy: no-referrer` → `Referrer-Policy: same-origin`. Este era el origen del problema al hacer POST desde el formulario HTML, según la documentación del protocolo en MDN.
- `container/quadlet/portal-crt-vmr5g.container`: imagen `localhost/portal-crt-vmr5g:17`.
- `README.md`, `DESPLIEGUE.md` y `SEGURIDAD.md`: causa y procedimiento de instalación actualizado.
- `tests/test_login_v17.py`: regresión del encabezado, rechazo de origen null y externo, y aceptación de autenticación same-origin.

**No** se cambian las credenciales, ni se elimina validación de `Origin`, CSRF o control de intentos; no se modifica el frontend React ni el modelo VMR. El enlace de registro continúa oculto y se conserva el correo `crt.bot.satys@gmail.com`.

**Nota de producción:** el acceso HTTP con `user/password` es exclusivamente de laboratorio. Infraestructura debe establecer HTTPS, credenciales seguras y control de acceso antes de DNS.
