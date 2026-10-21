# Despliegue CRT VMR 5G React v16 — Red Hat 9.7, Podman, puerto 8084

## Estado verificado en los registros recibidos

- Host: `srvmbcudaqa01` (`172.17.42.163`), RHEL 9.7, Podman 5.8.2.
- v15 se **construyó correctamente**, con React/Vite en imagen multi-etapa; no es necesario tener `npm` instalado en Red Hat.
- `portal-crt-vmr5g.service` fue desplegado con Quadlet y se vio `active (running)`.
- La prueba `curl` con `Origin: http://172.17.42.163:8084` y `csrf=incorrecto` retornó **403 «Formulario vencido»**, demostrando que el encabezado de origen probado sí era válido.
- **No se comprobó un inicio de sesión exitoso desde el navegador**; había una pantalla de error de origen. v16 mantiene el rechazo de orígenes ajenos, pero deja el error dentro de la misma página de login.

## 1. Copiar el ZIP desde Windows PowerShell

```powershell
cd C:\Users\gustavo.garcia\Downloads
scp .\portal-crt-vmr5g-react-contenedor-v16-login-mejorado.zip gustavo.garcia@172.17.42.163:/depi/dgp/DEI_DATOS/SATyS/
ssh gustavo.garcia@172.17.42.163
```

**Los siguientes comandos se ejecutan en la terminal SSH de RED HAT, no en Windows.**

## 2. Construir sin afectar todavía el servicio

```bash
cd /depi/dgp/DEI_DATOS/SATyS
mkdir -p crt_vmr5g_v16_build
unzip -oq portal-crt-vmr5g-react-contenedor-v16-login-mejorado.zip -d crt_vmr5g_v16_build
cd crt_vmr5g_v16_build/portal_crt_vmr5g_react
sudo podman build --format docker -t localhost/portal-crt-vmr5g:16 .
```

`--format docker` preserva la instrucción HEALTHCHECK en Podman; el servicio Quadlet realiza sus propios controles de operación.

## 3. Respaldar el Quadlet anterior y actualizar la imagen

```bash
sudo cp -a /etc/containers/systemd/portal-crt-vmr5g.container \
  /etc/containers/systemd/portal-crt-vmr5g.container.bak-v15
sudo cp container/quadlet/portal-crt-vmr5g.container \
  /etc/containers/systemd/portal-crt-vmr5g.container
sudo systemctl daemon-reload
sudo systemctl restart portal-crt-vmr5g.service
sudo systemctl status portal-crt-vmr5g.service --no-pager
```

No se reemplaza el archivo privado `/etc/crt-vmr-5g.env` ni la base de datos SQLite persistente.

## 4. Diagnosticar `user` / `password` sin publicarla

```bash
sudo podman exec -it portal-crt-vmr5g python container/check_credentials.py
```

Cuando lo solicite, escribir `user` y después `password` mediante el indicador interactivo. El script **no muestra ni almacena** la clave. Posibles resultados:

- **Credenciales válidas:** la cuenta y el hash son correctos en el backend. Si Edge rechaza el formulario, revisar `Origin`, `Sec-Fetch-Site` y el CSRF del navegador, sin compartir cookies ni contraseñas.
- **Credenciales no válidas:** volver a establecer una única vez las credenciales del entorno **solo en la LAN aislada de pruebas** y reiniciar (la última ejecución del configurador prevalece):

```bash
sudo /usr/bin/python3 scripts/configurar_prueba_http.py \
  --origin http://172.17.42.163:8084 \
  --username user --accept-insecure-http-test
sudo systemctl restart portal-crt-vmr5g.service
sudo podman exec -it portal-crt-vmr5g python container/check_credentials.py
```

**No guardar `password` en scripts, historial, GitLab ni Dockerfile.** No se proporciona ninguna contraseña inicial en el ZIP. `crt.bot.satys@gmail.com` es el **contacto del administrador**, no sustituye el usuario `user`.

## 5. Verificaciones de operación y permanencia

```bash
curl -fsS http://127.0.0.1:8084/healthz
curl -fsS http://127.0.0.1:8084/api/v1/readiness
sudo podman ps --filter name=portal-crt-vmr5g
sudo systemctl is-active portal-crt-vmr5g.service
sudo journalctl -u portal-crt-vmr5g.service -n 40 --no-pager
```

Entrar en ventana privada a `http://172.17.42.163:8084/login`. Probar usuario correcto e incorrecto; ante rechazo 403 ahora se muestra el formulario con un mensaje visible. No se eliminó la protección de origen ni los tokens CSRF.

Si la contraseña se verifica dentro del contenedor pero Edge sigue rechazando, abrir **F12 → Red → petición POST /login → Encabezados de solicitud** y verificar `Origin` y `Sec-Fetch-Site` (sin compartir `Cookie`, cuerpo POST, contraseña o `csrf`). El servicio registra únicamente el origen y host (sin contraseña/cookies/CSRF) al bloquear una petición. Consultar `sudo journalctl -u portal-crt-vmr5g.service -n 80 --no-pager` para ver la diferencia; nunca desactivar la validación para evitar la falla.

Quadlet permanece activo tras cerrar SSH y, con `WantedBy=multi-user.target`, se inicia tras reiniciar Red Hat.

## 6. Reversión a v15 si es necesario

```bash
sudo cp -a /etc/containers/systemd/portal-crt-vmr5g.container.bak-v15 \
  /etc/containers/systemd/portal-crt-vmr5g.container
sudo systemctl daemon-reload
sudo systemctl restart portal-crt-vmr5g.service
```

No modificar ni borrar `/var/lib/crt-vmr-5g-container`.

## Seguridad previa a DNS

La configuración HTTP y la contraseña de prueba son inadecuadas para producción. Infraestructura debe proporcionar HTTPS con certificado, `VMR_PUBLIC_ORIGIN=https://DOMINIO_FINAL` (con el puerto real), `VMR_COOKIE_SECURE=1`, rotación de credenciales, restricciones de red, revisión de dependencias y copia de seguridad de SQLite. El correo de contacto no habilita recuperación automática por correo.

## Herramientas utilizadas

Windows PowerShell; OpenSSH (`scp`, `ssh`); Red Hat Enterprise Linux 9.7; Podman 5.8.2; systemd y Quadlet; Node.js 22; npm; Vite; React; Python 3.13; SQLite; curl; GitLab (código/CI).
