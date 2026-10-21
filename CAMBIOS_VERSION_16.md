# Cambios v16 — Acceso y mensajes (2026-10-21)

- Se conserva **el mismo formulario de login** en fallos de contraseña, CSRF, validación de origen y límite de intentos. **Ya no existe una página independiente** `login-error.html`.
- **401:** «Usuario o contraseña incorrectos. Comprueba los datos e inténtalo nuevamente.» Se evita confirmar si un usuario existe en la base.
- **403 por origen:** «No pudimos validar el inicio de sesión. Abre el portal desde su dirección oficial y vuelve a intentarlo.» **La solicitud continúa bloqueada** por seguridad; no se evalúan credenciales en ese caso.
- **403 por token:** «El formulario venció. Vuelve a ingresar tus datos en este formulario.»
- **429:** mensaje sobre espera por demasiados intentos.
- Contacto mostrado: `crt.bot.satys@gmail.com`, como correo de administrador para ayuda (no es un usuario nuevo ni configura correo saliente).
- El enlace «Registrarme» continúa oculto; se conserva la ruta de registro para instalaciones que la tienen habilitada.
- Se agrega `container/check_credentials.py`, diagnóstico interactivo sin mostrar contraseñas ni hashes.
- Actualizado `Dockerfile`, Quadlet e instrucciones a imagen `localhost/portal-crt-vmr5g:16`.
- Todos los cambios son de acceso/UI; sin alteración de cálculos, React ni endpoints.

## Diagnóstico basado en el despliegue mostrado

`VMR_PUBLIC_ORIGIN` estaba correctamente configurado como `http://172.17.42.163:8084` y una petición con ese encabezado superó el control de origen hasta ser rechazada por token CSRF incorrecto (lo esperado). Es decir, ese dato **no demuestra** que el inicio de sesión de Edge se acepte: el navegador puede enviar encabezados distintos; hay que comprobarlos. El archivo `.env` se escribió varias veces, por lo que la última contraseña ingresada es la que importa. La verificación interactiva del contenedor permite comprobarla sin exponerla.

**Prohibido para producción:** `user/password`, HTTP sin TLS, publicar el puerto a Internet.
