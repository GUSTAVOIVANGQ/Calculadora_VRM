# Despliegue v17 — React + Python en Podman/Quadlet, RHEL 9.7 (8084)

## Causa resuelta

La consola de 21/10/2026 registra: `origin='null'` en `POST /login` pese a que `VMR_PUBLIC_ORIGIN=http://172.17.42.163:8084`. Además, `container/check_credentials.py` mostró credenciales válidas. Causa: el servidor enviaba `Referrer-Policy: no-referrer`, que hace que el navegador emita `Origin: null` en envíos POST tradicionales. La v17 cambia a `same-origin` manteniendo las defensas CSRF/Origin. No desactive ninguna de estas protecciones.

## 1. Desde Windows (PowerShell/CMD): copiar y entrar al servidor

```powershell
cd C:\Users\gustavo.garcia\Downloads
scp .\portal-crt-vmr5g-react-contenedor-v17-origin-corregido.zip gustavo.garcia@172.17.42.163:/depi/dgp/DEI_DATOS/SATyS/
ssh gustavo.garcia@172.17.42.163
```

**El resto se ejecuta en Red Hat, no en Windows.**

## 2. Descomprimir en carpeta separada y construir imagen v17

```bash
cd /depi/dgp/DEI_DATOS/SATyS
mkdir -p crt_vmr5g_v17_build
unzip -oq portal-crt-vmr5g-react-contenedor-v17-origin-corregido.zip -d crt_vmr5g_v17_build
cd crt_vmr5g_v17_build/portal_crt_vmr5g_react
sudo podman build --format docker -t localhost/portal-crt-vmr5g:17 .
```

Si el servidor no tiene npm, no hace falta instalarlo: React se compila dentro del Dockerfile (Node 22). La imagen de ejecución utiliza Python 3.13 como usuario 10001.

## 3. Actualizar Quadlet, manteniendo credenciales y usuarios

```bash
sudo cp -a /etc/containers/systemd/portal-crt-vmr5g.container /etc/containers/systemd/portal-crt-vmr5g.container.bak-v16
sudo cp container/quadlet/portal-crt-vmr5g.container /etc/containers/systemd/
sudo systemctl daemon-reload
sudo systemctl restart portal-crt-vmr5g.service
```

No sustituir `/etc/crt-vmr-5g.env` ni borrar `/var/lib/crt-vmr-5g-container/`: contienen configuración privada y usuarios. No iniciar `crt-vmr-5g.service` a la vez, pues ya se usa 8084.

## 4. Comprobar servicio y login

```bash
sudo systemctl is-active portal-crt-vmr5g.service
sudo podman exec portal-crt-vmr5g python -c 'import os; print("Origen configurado:", os.getenv("VMR_PUBLIC_ORIGIN"))'
curl -sI http://127.0.0.1:8084/login | grep -iE '^HTTP/|^Referrer-Policy:'
curl -fsS http://127.0.0.1:8084/healthz
sudo podman exec -it portal-crt-vmr5g python container/check_credentials.py
```

En la respuesta del login debe aparecer `Referrer-Policy: same-origin`. En el chequeo de credenciales, escribir interactivamente el usuario de prueba y su contraseña (sin compartirla); la aplicación nunca debe mostrar la contraseña en el log. Abrir una nueva pestaña privada en `http://172.17.42.163:8084/login`, iniciar sesión y confirmar redirección a la calculadora. Una contraseña incorrecta debe mostrar un mensaje dentro del login, no «origen no autorizado».

Si falla: `sudo journalctl -u portal-crt-vmr5g.service -n 60 --no-pager`; comprobar que el navegador envía el origen correcto.

## 5. Mantenerlo siempre encendido

```bash
sudo systemctl is-active portal-crt-vmr5g.service
sudo systemctl status portal-crt-vmr5g.service --no-pager
exit
```

El archivo Quadlet en `/etc/containers/systemd/` tiene `WantedBy=multi-user.target`, de modo que arranca con Red Hat y permanece al cerrar la terminal.

## Reversión a v16

```bash
sudo cp -a /etc/containers/systemd/portal-crt-vmr5g.container.bak-v16 /etc/containers/systemd/portal-crt-vmr5g.container
sudo systemctl daemon-reload
sudo systemctl restart portal-crt-vmr5g.service
```

## Seguridad antes de DNS

La URL HTTP y las credenciales débiles de laboratorio no son apropiadas para producción. Configurar HTTPS directo o terminación TLS institucional, `VMR_PUBLIC_ORIGIN` HTTPS definitivo, `VMR_COOKIE_SECURE=1`, credenciales robustas, acceso restringido y respaldo de SQLite. No incluir secretos en GitLab. El administrador de contacto sigue siendo `crt.bot.satys@gmail.com`.
