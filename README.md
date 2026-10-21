# Actualización v17 — login corregido en Red Hat/Podman

En las pruebas reales el navegador enviaba `Origin: null` al enviar el formulario. La causa era `Referrer-Policy: no-referrer` en `server.py`, no las credenciales. Ahora se envía `Referrer-Policy: same-origin`. Se conservan CSRF, controles de origen y validación del usuario. **No hay contraseñas incluidas** en este repositorio.

Despliegue permanente: ver [DESPLIEGUE.md](DESPLIEGUE.md). Historial de cambios: [CAMBIOS_VERSION_17.md](CAMBIOS_VERSION_17.md).

# Portal CRT VMR 5G — React + Python (migración progresiva)

> **Actualización v15:** el login ya no muestra «Registrarme»; los rechazos por credenciales, origen y CSRF tienen una página CRT. Se mantiene el control de acceso y los endpoints. La dirección autorizada debe coincidir con el navegador. La ruta de registro continúa disponible solamente si hay invitaciones habilitadas.


Proyecto privado de la Calculadora del Valor Mínimo de Referencia 5G. Basado en el ZIP de CRT entregado el 21/10/2026. Este repositorio está pensado para alojarse en **GitLab**.

## Arquitectura

- `frontend/src/main.jsx`: React, componentes para encabezado, 5 secciones, pie y controles de sesión.
- `frontend/src/view-schema.json`: vistas declarativas derivadas del HTML original, renderizadas como elementos React (no se ejecuta HTML remoto).
- `frontend/src/legacy/`: **adaptador transitorio** con el motor JavaScript de la calculadora, edición numérica, exportación, tabla, resultados y eventos. Se conserva para no alterar las fórmulas. **No es aún una reescritura 100 % idiomática a estado/hooks React**.
- `frontend/src/api-client.js`: cliente same-origin de API con CSRF de sesión.
- `frontend/src/styles.css`: CSS original preservado.
- `server.py`: servidor Python, login, registro, sesiones, protección de estáticos y API JSON.
- `api.py`, `accounts.py`: cálculo y almacenamiento de usuarios SQLite.
- `tests/`: pruebas del modelo, servidor, API y controles de seguridad.

## Desarrollo

Se requiere **Node.js 22.12+ (preferible 22 LTS), npm y Python 3.9+**. Vite compila el frontend, **no** se utiliza Vite como servidor de producción.

```bash
cd frontend
npm install
npm run build
cd ..
python3 -m unittest discover -s tests -p 'test_*.py' -q
node --test tests/model.test.mjs tests/ui-format.test.mjs
```

Para el servidor real necesitas credenciales en `/etc/crt-vmr-5g.env` cargadas por systemd. Nunca publicar ese archivo ni claves/cookies en GitLab. En producción se sirve `frontend/dist` compilado usando **el backend Python directamente**, sin que Node permanezca ejecutándose.

## GitLab

```bash
git init
git add .
git commit -m "Migra vistas a React y refuerza API VMR"
git branch -M main
git remote add origin git@gitlab.ejemplo.org:equipo/portal-crt-vmr5g.git
git push -u origin main
```

Sustituir el remoto de ejemplo por la URL que cree el equipo. **Antes del primer push** ejecutar `cd frontend && npm install` y confirmar `frontend/package-lock.json` para instalaciones reproducibles. La instalación de paquetes requiere conectividad al registro npm o un mirror de la organización.


## Ejecutar en contenedor (v15)

Ver `README_CONTENEDOR.md` y `docs/GUÍA_CONTENEDOR_RHEL9_GITLAB_8084.md` para Podman/Quadlet, Docker Compose, TLS directo sin Nginx y migración segura del servicio 8084.


## Despliegue real: Podman + systemd en Red Hat 9.7, sin Nginx (puerto 8084)

Este procedimiento refleja el despliegue realizado en `srvmbcudaqa01` el 21/10/2026, según los registros de terminal aportados. **No es una implementación ejecutada desde esta conversación.**

**Estado registrado:** Podman `5.8.2`, imagen `localhost/portal-crt-vmr5g:14` construida correctamente, frontend React compilado con Vite, servicio Quadlet `portal-crt-vmr5g.service` **active (running)** y `curl http://127.0.0.1:8084/healthz` => `ok`. Hubo un contenedor de prueba `portal-vmr-prueba` en `18084` que no respondió al primer `curl`; posteriormente quedó ejecutándose. El login en navegador mostró **«Origen no autorizado»** después del envío del formulario. No declarar ese acceso como validado.

### 1. Subir v15 (Windows PowerShell)

```powershell
cd C:\Users\gustavo.garcia\Downloads
scp .\portal-crt-vmr5g-react-contenedor-v15.zip gustavo.garcia@172.17.42.163:/depi/dgp/DEI_DATOS/SATyS/
ssh gustavo.garcia@172.17.42.163
```

### 2. Descomprimir sin sobreescribir otras versiones; construir nueva imagen

```bash
cd /depi/dgp/DEI_DATOS/SATyS
mkdir -p crt_vmr5g_v15_build
unzip -oq portal-crt-vmr5g-react-contenedor-v15.zip -d crt_vmr5g_v15_build
cd crt_vmr5g_v15_build/portal_crt_vmr5g_react
sudo podman build -t localhost/portal-crt-vmr5g:15 .
```

No se requiere `npm` en Red Hat: Node/Vite compilan dentro de la imagen durante `podman build`.

### 3. Corregir origen y configurar acceso **solamente para pruebas privadas**

La URL del navegador es `http://172.17.42.163:8084/login`. Si `/etc/crt-vmr-5g.env` conserva `VMR_PUBLIC_ORIGIN` distinto (por ejemplo un dominio HTTPS), el POST se rechaza; **no desactive la protección de origen**.

```bash
# Leer solo opciones no secretas, nunca imprimir el hash ni tokens
sudo grep -E '^(VMR_PUBLIC_ORIGIN|VMR_COOKIE_SECURE|VMR_ENABLE_HSTS)=' /etc/crt-vmr-5g.env || true

# Crea o actualiza el archivo privado sin guardar la contraseña en el repositorio.
sudo /usr/bin/python3 scripts/configurar_prueba_http.py \
  --origin http://172.17.42.163:8084 \
  --username user \
  --accept-insecure-http-test
```

Cuando el script pregunte, escribe **`password`** dos veces. Guardará solo un hash PBKDF2 con salt. **Estas credenciales son de DEMOSTRACIÓN, inseguras para Internet y transmitidas en claro por HTTP.** Solo ejecutar este paso en red privada temporal y cambiar clave por una fuerte (12+ caracteres), con HTTPS y `VMR_COOKIE_SECURE=1` antes de publicar DNS. El script conserva las demás variables como la configuración del registro y respalda el `.env` previo.

### 4. Sustituir la imagen v14 por v15 en el servicio permanente

El servicio anterior `crt-vmr-5g.service` debe permanecer deshabilitado, para no competir en el puerto 8084. El nuevo servicio ya existe como Quadlet `portal-crt-vmr5g`. **No hace falta deshabilitarlo ni parar el 8084 para construir.**

```bash
sudo systemctl is-enabled crt-vmr-5g.service || true
sudo podman rm -f portal-vmr-prueba 2>/dev/null || true
# Copiar SOLO la definición nueva después de construir correctamente la imagen
sudo cp container/quadlet/portal-crt-vmr5g.container /etc/containers/systemd/portal-crt-vmr5g.container
sudo systemctl daemon-reload
sudo systemctl restart portal-crt-vmr5g.service
sudo systemctl status portal-crt-vmr5g.service --no-pager
sudo podman ps --filter name=portal-crt-vmr5g
curl -fsS http://127.0.0.1:8084/healthz
curl -fsS http://127.0.0.1:8084/api/v1/readiness
```

Prueba manual: abrir `http://172.17.42.163:8084/login`, ingresar `user` / `password` en **red interna**, verificar redirección a la calculadora. Enviar contraseña equivocada y comprobar página CRT con botón «Volver a iniciar sesión». Si persiste «Origen no autorizado», revisar `/etc/crt-vmr-5g.env`, reiniciar la unidad y consultar registros (`sudo journalctl -u portal-crt-vmr5g -n 80 --no-pager`).

### 5. Permanencia sin terminal

```bash
sudo systemctl is-active portal-crt-vmr5g.service
sudo systemctl status portal-crt-vmr5g.service --no-pager
exit
```

Quadlet en `/etc/containers/systemd/portal-crt-vmr5g.container` tiene `[Install] WantedBy=multi-user.target`; `systemd` genera y arranca la unidad tras reiniciar Red Hat. No usar `nohup`, `screen` ni un servicio duplicado en el puerto 8084.

**Para GitLab / DNS:** mantener el `.env` y SQLite fuera del repositorio e imagen; usar DNS + certificado real, HTTPS directo o balanceador institucional, cambiar `VMR_PUBLIC_ORIGIN` al origen HTTPS definitivo, `VMR_COOKIE_SECURE=1` y `VMR_ENABLE_HSTS=1`; reconstruir/desplegar con revisión de seguridad. Los accesos `user/password` no son aptos para producción.

### Reversión a v14 sin borrar datos

```bash
sudo sed -i 's@localhost/portal-crt-vmr5g:15@localhost/portal-crt-vmr5g:14@' /etc/containers/systemd/portal-crt-vmr5g.container
sudo systemctl daemon-reload
sudo systemctl restart portal-crt-vmr5g.service
```

**Herramientas utilizadas:** Windows PowerShell, OpenSSH (`scp`, `ssh`), RHEL 9.7, Podman 5.8.2, systemd/Quadlet, Node 22/npm/Vite (build dentro de contenedor), React, Python 3.13, SQLite, GitLab y `curl`. Para una guía ampliada ver `docs/DESPLIEGUE_RHEL9_8084_V15.md`.


## Acceso y despliegue de la versión 16

El acceso utiliza usuario y contraseña locales configurados en `/etc/crt-vmr-5g.env` (fuera de GitLab). Para la prueba interna el usuario solicitado es `user`; la contraseña `password` **no se guarda en el repositorio ni es una clave por defecto automática**: debe haberse configurado interactivamente. Para verificar lo que realmente está cargado en el contenedor, ejecutar:

```bash
sudo podman exec -it portal-crt-vmr5g python container/check_credentials.py
```

El correo de **contacto** del administrador es `crt.bot.satys@gmail.com`. No constituye una cuenta de login ni configura SMTP.

Desde v16 los errores de autenticación aparecen en el **mismo formulario CRT** (401 datos inválidos, 403 CSRF/origen y 429 límite de intentos). Se conserva la validación de `Origin` y CSRF; no se muestra una pantalla «Solicitud no autorizada». No confirmar públicamente si un usuario existe, para prevenir enumeración de cuentas.

Despliegue real y comandos de Podman/RHEL 8084: [DESPLIEGUE.md](DESPLIEGUE.md). El despliegue definitivo con DNS necesita TLS y credenciales seguras.
