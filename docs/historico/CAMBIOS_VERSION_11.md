# Versión 11 — Login anterior + Crear cuenta + API

- Login anterior preservado: diseño, ruta `/login`, cuenta administrativa y almacenamiento de su contraseña definido en `/etc/crt-vmr-5g.env`. Se añadió solo el enlace «Crear cuenta con invitación».
- Nuevo `/crear-cuenta` (`/register` es alias), valida usuario, contraseña, confirmación y código de invitación. El registro está deshabilitado hasta que el administrador configure la invitación. Los registrados pueden iniciar sesión desde el mismo login original.
- APIs de autenticación: `GET /api/v1/auth/csrf`, `GET /api/v1/auth/status`, `POST /api/v1/auth/login`, `POST /api/v1/auth/register`.
- Almacenamiento SQLite fuera del directorio web; hash PBKDF2-SHA256, permisos 0600, limitación de intentos, CSRF y cookies seguras.
- Nuevo `setup_registration.py` para habilitar/rotar/deshabilitar invitaciones sin sustituir el usuario original; `manage_users.py` para cuentas registradas.
- Se mantiene la interfaz clásica completa de v10: tabla descuentos, editor de modalidad, campos con comas y decimales, flechas de aumento/disminución y endpoints de cálculo.
- Puerto 8084 y configuración Nginx **no se modifican automáticamente**. La guía incluye las dos arquitecturas comunes, respaldo y comprobaciones.
- La aplicación no se integra ni envía credenciales al login externo que aparece en la imagen de referencia.
