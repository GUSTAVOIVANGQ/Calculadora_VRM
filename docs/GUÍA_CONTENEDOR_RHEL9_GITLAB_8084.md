# Despliegue y operación — Portal CRT VMR 5G React v15

> Documento para infraestructura (Red Hat 9.7, IP 172.17.42.163, puerto 8084). Basado en el registro de comandos ejecutados por el usuario el 21/10/2026. Entorno privado de pruebas, sin Nginx.

## Despliegue observado

- Se copió v14 con PowerShell `scp` hacia `/depi/dgp/DEI_DATOS/SATyS`.
- En Red Hat se extrajo el ZIP y se ejecutó `sudo podman build -t localhost/portal-crt-vmr5g:14 .` con éxito. Node 22/Vite se instalaron y ejecutaron **dentro del build**; `npm` no estaba disponible en el host, lo cual no impidió el build de la imagen.
- Se creó `/var/lib/crt-vmr-5g-container` para SQLite, manteniéndola fuera de la imagen.
- La prueba en `127.0.0.1:18084` devolvió conexión rechazada inicialmente; ese contenedor siguió ejecutándose posteriormente. No confundir este resultado con una prueba de salud pasada.
- Se deshabilitó el servicio Python original `crt-vmr-5g.service` después de respaldar datos.
- Se instaló `/etc/containers/systemd/portal-crt-vmr5g.container` y se arrancó `portal-crt-vmr5g.service`; se verificó `active (running)` y `curl 127.0.0.1:8084/healthz` devolvió `ok`.
- La pantalla se cargó, pero al enviar el login aparecía **«Origen no autorizado»**. Las capturas no demuestran una autenticación correcta. La causa probable es que `VMR_PUBLIC_ORIGIN` no coincide con el origen `http://172.17.42.163:8084` del navegador.

## Actualización correctiva v15

Ver `README.md`, apartado **Despliegue real** para comandos completos. Resumen de operación:

```bash
cd /depi/dgp/DEI_DATOS/SATyS
mkdir -p crt_vmr5g_v15_build
unzip -oq portal-crt-vmr5g-react-contenedor-v15.zip -d crt_vmr5g_v15_build
cd crt_vmr5g_v15_build/portal_crt_vmr5g_react
sudo podman build -t localhost/portal-crt-vmr5g:15 .
```

Para **prueba interna solamente**: configurar `user` y contraseña temporal `password` mediante el script de terminal interactivo (el password no se encuentra en Git ni en la imagen):

```bash
sudo /usr/bin/python3 scripts/configurar_prueba_http.py \
 --origin http://172.17.42.163:8084 --username user --accept-insecure-http-test
```

El script solicita la clave dos veces, guarda un hash, cambia `VMR_PUBLIC_ORIGIN` al origen HTTP usado, `VMR_COOKIE_SECURE=0`, `VMR_ENABLE_HSTS=0`, y realiza un respaldo con permisos restringidos. **No se debe habilitar esta configuración para usuarios reales ni redes públicas.** La política de `Origin` permanece activa y bloquea solicitudes de sitios terceros.

```bash
sudo podman rm -f portal-vmr-prueba 2>/dev/null || true
sudo cp container/quadlet/portal-crt-vmr5g.container /etc/containers/systemd/portal-crt-vmr5g.container
sudo systemctl daemon-reload
sudo systemctl restart portal-crt-vmr5g.service
sudo systemctl status portal-crt-vmr5g.service --no-pager
curl -fsS http://127.0.0.1:8084/healthz
curl -fsS http://127.0.0.1:8084/api/v1/readiness
```

Valida credenciales correctas, incorrectas, origen inválido, CSRF vencido, enlace «Registrarme» oculto y acceso a la calculadora. Las rutas `/register` y `/crear-cuenta` siguen disponibles si el administrador mantiene invitaciones; ocultar el enlace **no es una medida de control de registro**. Desactivar el código de invitación en configuración para prohibir registros por completo si esa es la política.

## Verificación de permanencia

`portal-crt-vmr5g.service` es generado a partir del Quadlet con `WantedBy=multi-user.target`. Utilizar `sudo systemctl status portal-crt-vmr5g.service --no-pager`, `sudo journalctl -u portal-crt-vmr5g.service -n 80 --no-pager`, `sudo podman ps`. Cerrar SSH con `exit` no detiene el servicio.

## Seguridad institucional (DNS)

- No publicar credenciales sobre HTTP. El origen final deberá ser HTTPS y DNS acordado; el equipo de red suministra certificado, restricciones de firewall y acceso.
- `VMR_PUBLIC_ORIGIN=https://FQDN:8084` (o URL definitiva), `VMR_COOKIE_SECURE=1`, `VMR_ENABLE_HSTS=1`. Reiniciar después de cambios. No eliminar validación de `Origin` o token CSRF.
- Sustituir `user/password` por clave fuerte. Usar `create_login.py --replace` mediante procedimiento de rotación verificado, **sin perder otras variables del `.env`**. No guardar contraseñas ni hashes en GitLab.
- Limitar puerto de administración 9090, habilitar escaneo de imagen y dependencias y registros de acceso. El backend usa `http.server` y mantiene sesiones y rate-limit en memoria; evaluar servidor de producción y pruebas adicionales antes de acceso público.
- Persistir SQLite en `/var/lib/crt-vmr-5g-container`, preservar permisos UID 10001 y respaldar antes de actualizar. Los reinicios cierran sesiones en memoria.

## Herramientas del despliegue

| Herramienta | Uso |
|---|---|
| Windows PowerShell | Consola para transferir archivos |
| OpenSSH (scp/ssh) | Copia segura ZIP y acceso al host |
| RHEL 9.7 | Sistema operativo anfitrión |
| Podman 5.8.2 | Construcción y ejecución del contenedor |
| systemd / Quadlet | Persistencia del contenedor y autoarranque |
| Node.js 22 + npm + Vite | Compilación React dentro de imagen multi-etapa |
| React | UI |
| Python 3.13 | Backend y API |
| SQLite | Usuarios persistentes |
| curl | Chequeos HTTP y endpoints |
| GitLab | Repositorio, CI, gobernanza |

## Rollback

Conservar imagen local v14. Si falla v15, apuntar la definición Quadlet a `localhost/portal-crt-vmr5g:14`, ejecutar `sudo systemctl daemon-reload` y `sudo systemctl restart portal-crt-vmr5g.service`. No tocar ni eliminar la base SQLite. Confirmar estado antes de cerrar SSH.
