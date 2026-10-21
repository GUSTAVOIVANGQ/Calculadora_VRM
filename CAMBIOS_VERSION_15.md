# Cambios v15 — 21 octubre 2026

- Agrega `login-error.html` para mensajes visuales de contraseña inválida (`401`), origen incorrecto (`403`), CSRF expirado (`403`) e intentos excesivos (`429`).
- Oculta el enlace «Registrarme» y el separador «o» del login; no modifica endpoints de registro.
- Conserva el bloqueo de `Origin` y CSRF, sin abrirlos para resolver el rechazo.
- Añade generador interactivo `scripts/configurar_prueba_http.py` para usuario `user` y contraseña temporal `password` **únicamente en laboratorio interno**, guardando solo PBKDF2 SHA256 en archivo privado del host. No hay contraseña incrustada en imagen ni GitLab.
- Actualiza README y guía de despliegue con pasos que reflejan Podman y Quadlet usados en RHEL 9.7, junto a pruebas y riesgos pendientes.
- Imagen versionada como `localhost/portal-crt-vmr5g:15`; mismo servicio `portal-crt-vmr5g` y puerto 8084.
