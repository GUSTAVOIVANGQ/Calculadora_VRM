# Revisión de seguridad — CRT VMR 5G React

**Alcance**: revisión de código y pruebas automatizadas de la entrega migrada. **No equivale a pentest ni certificación para producción.**

| Control | Situación | Acción |
|---|---|---|
| Sesión | Cookie `HttpOnly`, `SameSite=Strict`, caducidad y tokens aleatorios | Se conserva. `Secure` activado al desplegar con HTTPS. |
| Contraseñas | PBKDF2-SHA256 con salt; hashes no deben estar en Git | Se conserva. Rotar cuentas de prueba `user/password`. |
| CSRF formulario | Token de login/registro de un solo uso; logout ligado a sesión | Se conserva. |
| CSRF API | **Nuevo** `X-VMR-CSRF` obligatorio en `/api/v1/calculate*` | Se obtiene vía `GET /api/v1/auth/session`. |
| Origen | **Nuevo** bloqueo de `Origin` no autorizado + `Sec-Fetch-Site: cross-site` | Fijar `VMR_PUBLIC_ORIGIN=https://dominio-oficial:8084`. |
| Ficheros | Lista explícita y `dist/assets` con ruta normalizada y extensiones permitidas | Código fuente, claves y bases de datos no quedan servidos. |
| Encabezados | CSP, `nosniff`, `DENY`, `Referrer-Policy`, `Permissions-Policy` | HSTS configurable solo en HTTPS. |
| API | Validaciones de estructura/tipos/límites; JSON size <= 128 KiB | Se conserva; payloads inválidos se rechazan. |
| Fuerza bruta | Contador de intentos por IP, registro con invitación | En memoria: no compartido entre múltiples procesos/instancias. |
| DNS / TLS | HTTP directo anterior no cifra las credenciales | **Obligatorio resolver TLS antes de habilitar acceso por DNS público**. |
| SQLite | Usuarios en estado persistente externo al Git | Restringir 0700 carpeta y 0600 base. Respaldar. |
| Dependencias | React/Vite/npm añadidos | `npm audit` en GitLab; mantener versiones y `package-lock.json` actualizado. |

## Riesgos residuales importantes

1. La autenticación/sesiones y el rate-limit se mantienen en **memoria del proceso Python**; un reinicio cierra sesiones y múltiples workers no comparten estado. No escalar a varios workers sin rediseñar sesión/rate-limit.
2. Python `http.server` es adecuado para un entorno controlado de bajo tráfico, **no** una plataforma endurecida de alta concurrencia ni un WAF. Antes de publicar a Internet, el equipo de infraestructura debe aprobar capacidad y controles perimetrales.
3. Vistas React y lógica JS existente están integradas mediante un **adaptador legado**; falta migrar los controladores de entrada y resultados a hooks/estado React y realizar pruebas E2E después de `npm run build`.
4. Cookies `Secure=0` y credenciales predecibles solo sirven para pruebas internas de corta duración. Nunca subir secretos a GitLab ni enviar contraseñas por chat/correo.
5. CSRF por `Origin` compara con `VMR_PUBLIC_ORIGIN` si se configura. **Configurar obligatoriamente este origen** al publicar mediante DNS.
6. `GET /api/v1/health` y `/healthz` son públicos y no revelan detalles, y `/api/v1/readiness` indica únicamente si `frontend/dist` está compilado. Limitar el puerto con firewall/red institucional.
7. Revisar manualmente la procedencia de los valores Excel, licencias y política de publicación de los datos antes de abrir repositorio.

## Pruebas de seguridad ejecutadas

- Sin login se bloquea API privada.
- POST a cálculo sin `X-VMR-CSRF`: `403`.
- POST a cálculo con CSRF de sesión: `200`.
- `Origin` ajeno: `403`.
- Código `server.py`/rutas de Git/archivos de fuente: `404`.
- Alta de cuenta requiere invitación; límites de intentos.

**Por completar antes de DNS**: escaneo de SAST/DAST/secretos con el equipo de seguridad, pruebas en Chrome/Firefox móviles, análisis de cabeceras reales TLS, pruebas de recuperación y revisión de roles / autorización.


## Nota v15 sobre el error «Origen no autorizado»

El navegador debe acceder exactamente al origen declarado en `VMR_PUBLIC_ORIGIN` (esquema + hostname/IP + puerto). El sistema **no** desactiva este control para resolver el error. En la dirección HTTP de laboratorio `http://172.17.42.163:8084` solo puede probarse con `VMR_PUBLIC_ORIGIN=http://172.17.42.163:8084` y cookies no seguras, **exclusivamente en red privada aislada**. Con DNS institucional se obliga HTTPS y cookies `Secure`. Los rechazos HTML ahora presentan una página CRT (401/403/429); las APIs mantienen códigos HTTP/JSON.

El script `scripts/configurar_prueba_http.py` permite crear credenciales temporales débiles a petición del administrador y **no** es una función de bootstrap automático. No habilitarlo ni ejecutarlo en producción, y rotar `user/password` al finalizar pruebas. Ocultar el enlace de registro no deshabilita el endpoint: retirar el código de invitación si deben prohibirse altas.

## Inicio de sesión v16

Los errores de credenciales retornan HTTP 401 y un mensaje genérico, sin confirmar si la cuenta existe. Rechazos de Origin y CSRF devuelven HTTP 403 y un mensaje de validación, con el formulario renovado; nunca se reinterpretan como prueba de credenciales incorrectas. Los intentos repetidos reciben HTTP 429. Verificación interna de credenciales: `sudo podman exec -it portal-crt-vmr5g python container/check_credentials.py` (sin exposición de contraseña). El correo de administrador es informativo, no habilita SMTP ni crea cuenta.


### Corrección de formularios HTML (v17)

El encabezado HTTP `Referrer-Policy: no-referrer` hacía que Chrome/Edge enviaran
`Origin: null` al enviar el formulario `/login`. El backend rechazaba ese POST
aunque el usuario y la contraseña fueran correctos. La política ahora es
`Referrer-Policy: same-origin`: no revela URL de procedencia a dominios externos
y conserva el origen real en formularios del propio sitio. **Se conserva**
`Origin` estricto, comprobación `Sec-Fetch-Site`, tokens CSRF, cookies protegidas
y límite de intentos. No se admite `Origin: null` en el servidor.

Referencias: MDN, `Referrer-Policy` (sección 'Effect on the Origin header') y `Origin`.
