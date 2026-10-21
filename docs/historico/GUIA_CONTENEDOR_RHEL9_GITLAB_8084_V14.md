# Despliegue CRT VMR 5G en contenedor — Red Hat 9.7 / GitLab / DNS

**Versión de empaquetado:** v14 (basado en frontend React v13, sin cambiar las fórmulas).  
**Objetivo:** React compilado + backend Python + login/registro + API en **un contenedor** por instancia.  
**Sin Nginx.** Guía preparada para `srvmbcudaqa01`, Red Hat Enterprise Linux 9.7, puerto externo `8084`.

## Arquitectura y archivos

- `Dockerfile`: compila `frontend/` con Node 22; copia solamente React compilado y los archivos esenciales a Python 3.13. Servicio escucha `0.0.0.0:8084` dentro del contenedor.
- `compose.yaml`: ejecución con Docker Compose (HTTP para red interna de pruebas); `compose.tls.yaml` añade TLS directo en Python, sin Nginx.
- `container/quadlet/portal-crt-vmr5g.container`: definición de Podman + `systemd` para Red Hat; variante `portal-crt-vmr5g-tls.container.example` para TLS directo.
- `container/healthcheck.py`: readiness local `/api/v1/readiness`.
- Persistencia: `/var/lib/crt-vmr-5g-container` en el host, montado en `/var/lib/crt-vmr-5g` del contenedor (base SQLite).
- Credenciales: archivo **externo** `/etc/crt-vmr-5g.env`, nunca dentro de Git ni de la imagen.
- La imagen arranca con UID/GID `10001:10001`, sistema raíz de solo lectura y permisos reducidos.

**Atención:** el servicio previo `crt-vmr-5g.service` ya utiliza 8084. No arranque el contenedor directamente en 8084 mientras ese servicio permanezca activo. Para probar sin detenerlo se usa 18084 (solo loopback). La carpeta anterior queda intacta para rollback.

## 1. Preparar proyecto y herramientas

En Windows PowerShell, suponiendo que el ZIP está en Descargas:

```powershell
cd C:\Users\gustavo.garcia\Downloads
scp .\portal-crt-vmr5g-react-contenedor-v14.zip gustavo.garcia@172.17.42.163:/depi/dgp/DEI_DATOS/SATyS/
ssh gustavo.garcia@172.17.42.163
```

En Red Hat:

```bash
cd /depi/dgp/DEI_DATOS/SATyS
unzip -t portal-crt-vmr5g-react-contenedor-v14.zip
unzip -q portal-crt-vmr5g-react-contenedor-v14.zip
cd portal_crt_vmr5g_react
command -v podman || echo 'Solicitar Podman al administrador de Red Hat'
```

**Para infraestructura:** Podman 4.6+ con soporte Quadlet y `systemd` del sistema. Si Podman no está instalado y los repositorios corporativos están disponibles, el equipo administrador puede instalarlo conforme a su política de RHEL (`dnf install podman`). El servidor o runner que construya la imagen necesita acceso autorizado a registros de imágenes y al registro npm. No hay descarga de dependencias npm precargada en este ZIP.

## 2. Construir y comprobar la imagen (SIN interrumpir el 8084)

```bash
cd /depi/dgp/DEI_DATOS/SATyS/portal_crt_vmr5g_react
sudo podman build -t localhost/portal-crt-vmr5g:14 -f Dockerfile .
sudo podman image inspect localhost/portal-crt-vmr5g:14 --format '{{.Id}}'
```

La construcción usa `npm install` si todavía no existe `frontend/package-lock.json`; **antes de aprobar GitLab/producción**, generar y versionar el lock usando npm en un entorno conectado a los repositorios autorizados:

```bash
cd frontend
npm install --package-lock-only
npm ci
npm run build
cd ..
git add frontend/package-lock.json
```

El Dockerfile empleará `npm ci` cuando detecte el lock. Para reproducibilidad y gobernanza, fijar imágenes base por digest, instalar dependencias desde un mirror institucional y realizar escaneo de imágenes. No copiar secretos a los argumentos de `podman build`.

Preparar un almacenamiento **distinto** del utilizado por la instalación nativa:

```bash
sudo install -d -o 10001 -g 10001 -m 0700 /var/lib/crt-vmr-5g-container
sudo test -s /etc/crt-vmr-5g.env && echo 'Credenciales disponibles'
```

Para una prueba HTTP **solo local** en 18084 (no ingresar contraseñas desde navegadores externos):

```bash
sudo podman run -d --name portal-vmr-smoke \
  -p 127.0.0.1:18084:8084 \
  --env-file /etc/crt-vmr-5g.env \
  -e VMR_USERS_DB=/var/lib/crt-vmr-5g/users.sqlite3 \
  -v /var/lib/crt-vmr-5g-container:/var/lib/crt-vmr-5g:Z \
  localhost/portal-crt-vmr5g:14
curl -fsS http://127.0.0.1:18084/healthz
curl -fsS http://127.0.0.1:18084/api/v1/readiness
sudo podman logs --tail 30 portal-vmr-smoke
sudo podman rm -f portal-vmr-smoke
```

No pasar `-e VMR_COOKIE_SECURE=0` durante la prueba para no degradar por accidente la configuración de producción. El smoke test verifica acceso local al servicio y su frontend compilado, no el login de un navegador ni HTTPS.

## 3. Antes de cambiar el puerto 8084: respaldar y conservar usuarios

Comprobar unidad e instalación anterior:

```bash
sudo systemctl cat crt-vmr-5g
sudo ss -ltnp | grep ':8084'
sudo systemctl is-active crt-vmr-5g
```

Respaldar **fuera del GitLab**:

```bash
TS=$(date +%Y%m%d-%H%M%S)
BKP="/var/backups/crt-vmr-5g/pre-contenedor-$TS"
sudo install -d -m 0700 "$BKP"
sudo cp -a /etc/systemd/system/crt-vmr-5g.service "$BKP/"
sudo cp -a /etc/crt-vmr-5g.env "$BKP/"
sudo cp -a /depi/dgp/DEI_DATOS/SATyS/portal_crt_vmr5g_v11_8084 "$BKP/"
echo "Respaldo: $BKP"
```

**Solo cuando la imagen y el smoke test estén correctos**, planificar una ventana breve de cambio. Parar el servicio viejo y preparar una copia consistente de la base de datos si existe:

```bash
sudo systemctl stop crt-vmr-5g
# Evitar que el servicio antiguo compita por el puerto 8084 tras reiniciar RHEL.
sudo systemctl disable crt-vmr-5g
sudo ss -ltnp | grep ':8084' || echo '8084 libre'
sudo /usr/bin/python3 - <<'PY'
import sqlite3
from pathlib import Path
src=Path('/var/lib/crt-vmr-5g/users.sqlite3')
dst=Path('/var/lib/crt-vmr-5g-container/users.sqlite3')
if src.is_file() and not dst.exists():
    with sqlite3.connect(str(src)) as source, sqlite3.connect(str(dst)) as target:
        source.backup(target)
    print('Usuarios copiados a base persistente nueva')
elif dst.exists():
    print('La base nueva ya existe: no se sobrescribe; revisar sincronización')
else:
    print('No hay base previa; la aplicación creará una nueva')
PY
sudo chown -R 10001:10001 /var/lib/crt-vmr-5g-container
sudo chmod 0700 /var/lib/crt-vmr-5g-container
```

No utilizar la misma base SQLite simultáneamente desde el servicio anterior y el contenedor. Los tokens de sesión son residentes en memoria y los usuarios deberán iniciar sesión otra vez después del cambio.

## 4. Podman + Quadlet: contenedor permanente al cerrar SSH

**Escenario HTTP interno:** utilice `container/quadlet/portal-crt-vmr5g.container` solo en red interna estrictamente restringida. Usuarios reales requieren HTTPS; consulte el apartado 5.

```bash
sudo install -d -m 0755 /etc/containers/systemd
sudo cp container/quadlet/portal-crt-vmr5g.container /etc/containers/systemd/
sudo systemctl daemon-reload
sudo systemctl start portal-crt-vmr5g.service
sudo systemctl status portal-crt-vmr5g.service --no-pager
sudo podman ps --filter name=portal-crt-vmr5g
curl -fsS http://127.0.0.1:8084/api/v1/readiness
sudo journalctl -u portal-crt-vmr5g.service -n 50 --no-pager
```

El archivo tiene `[Install] WantedBy=multi-user.target` y es generado por Quadlet durante el arranque, para que funcione sin terminal y se inicie al reiniciar. **No utilizar `systemctl enable` sobre la unidad generada**: normalmente no se habilita como una unidad convencional. Podman genera la dependencia de arranque a partir del archivo `.container`.

## 5. Publicar mediante DNS con HTTPS DIRECTO, sin Nginx

El equipo DNS/infraestructura debe disponer de FQDN, certificado TLS válido para ese FQDN y clave privada en una carpeta host **separada** `/etc/crt-vmr-5g-tls/`. No se distribuyen certificados en la imagen ni en GitLab. Su administración debe garantizar acceso de lectura al UID del contenedor 10001 y a personal autorizado solamente, evitando `chmod 777` y sin alterar el almacén TLS original del sistema.

Copiar la variante TLS como **reemplazo** de la Quadlet anterior; NO arrancar dos Quadlets en el 8084:

```bash
sudo install -d -m 0700 /etc/crt-vmr-5g-tls
# El equipo de infraestructura instala aquí fullchain.pem y privkey.pem,
# con permisos restringidos compatibles con UID 10001.
sudo cp container/quadlet/portal-crt-vmr5g-tls.container.example \
  /etc/containers/systemd/portal-crt-vmr5g.container
# Editar /etc/crt-vmr-5g.env, fuera de Git:
# VMR_COOKIE_SECURE=1
# VMR_PUBLIC_ORIGIN=https://FQDN-INSTITUCIONAL:8084
# VMR_ENABLE_HSTS=1
sudo systemctl daemon-reload
sudo systemctl restart portal-crt-vmr5g.service
```

Si no existe certificado válido, **no publicar credenciales mediante HTTP**. También es válido que el equipo institucional termine HTTPS en un balanceador externo sin Nginx local, con backend restringido a la red de confianza. Las URL y encabezados de origen deben validarse según `SEGURIDAD.md`.

Verificaciones desde una máquina con confianza en la CA institucional:

```bash
curl -i https://FQDN-INSTITUCIONAL:8084/healthz
curl -i https://FQDN-INSTITUCIONAL:8084/api/v1/readiness
curl -I https://FQDN-INSTITUCIONAL:8084/login
```

No utilizar `curl -k` como criterio de aceptación de HTTPS. Comprobar certificado, hostname, renovación, controles de acceso, registro de eventos y vulnerabilidades. En políticas institucionales, DNS no implica por sí solo HTTPS.

## 6. Alternativa Docker Compose (otros equipos)

```bash
# Sin Quadlet ni crt-vmr-5g.service simultáneos escuchando 8084.
docker compose -f compose.yaml build
docker compose -f compose.yaml up -d
docker compose -f compose.yaml ps
# Para TLS directo, con los certificados preparados:
docker compose -f compose.yaml -f compose.tls.yaml up -d --build
```

Compose conserva volúmenes, limita privilegios y reinicia el servicio. No ejecutar Docker y Podman en 8084 simultáneamente. La opción recomendada para **tu Red Hat 9.7** es Podman + Quadlet.

## 7. GitLab y pruebas

```bash
/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py' -q
node --test tests/model.test.mjs tests/ui-format.test.mjs
```

No subir `.env`, certificados, cookies, bases SQLite ni contraseña de administrador. Habilitar rama protegida, MR, escaneo de dependencias y de imágenes; configurar tokens/registry en variables protegidas de GitLab. El ZIP incluye `.dockerignore`, Dockerfile, pruebas de contrato y pipeline GitLab que compila React. Publicar imágenes solo en registry institucional después de validar la canalización; el archivo Quadlet usa una imagen local que debe construirse o descargarse bajo el mismo nombre.

El motor JS de fórmulas es el mismo de la versión v13. La interfaz React contiene aún un adaptador de cálculos heredado. La migración no convierte automáticamente todos los controles en componentes React puros.

## 8. Retroceso rápido a systemd anterior

Si falla el contenedor, detener **solo** la nueva unidad y recuperar el servicio viejo; los datos anteriores permanecen intactos:

```bash
sudo systemctl stop portal-crt-vmr5g.service
sudo rm -f /etc/containers/systemd/portal-crt-vmr5g.container
sudo systemctl daemon-reload
sudo systemctl enable --now crt-vmr-5g
sudo systemctl status crt-vmr-5g --no-pager
```

El `enable --now` vuelve a habilitar el inicio automático del servicio anterior. Esto vuelve a la base de datos anterior, que no incorpora usuarios creados en el contenedor durante el intervalo. Para conservarlos, planificar reconciliación o respaldo antes del rollback.

## 9. Alcance de las verificaciones en la entrega

- Código Python y pruebas de aplicación/contrato de contenedor: se pueden ejecutar offline.
- Pruebas del modelo JS: se pueden ejecutar offline.
- Compilación efectiva `docker build`/`podman build` **pendiente en el entorno donde haya motor de contenedores y acceso al registro npm**; no se debe declarar como verificada sin ejecutar esa prueba.
- Validación de login y endpoints desde un contenedor real, red, SELinux, HTTPS/DNS y reinicio de RHEL: **pendiente en la infraestructura del equipo**.

## Herramientas empleadas

| Herramienta | Propósito |
|---|---|
| RHEL 9.7 | Sistema operativo |
| Podman + Quadlet | Motor de contenedores, integración con systemd |
| Docker Compose (opcional) | Despliegue alternativo local |
| Node.js 22, npm, Vite 7, React 19 | Build del frontend |
| Python 3.13, biblioteca estándar, SQLite | Backend, autenticación, API y persistencia |
| Open Container Initiative/Dockerfile | Imagen multi-etapa y ejecución sin root |
| Git, GitLab CI | Repositorio, pruebas y preparación de publicación |
| `curl`, `unittest`, `node --test` | Verificación de backend/cálculos |
| SELinux, systemd y firewall institucional | Controles del host |
| PKI/certificados X.509, DNS | Dominio y HTTPS |

## Referencias oficiales

- Podman Quadlet: https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html
- RHEL 9 contenedores: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/building_running_and_managing_containers/
