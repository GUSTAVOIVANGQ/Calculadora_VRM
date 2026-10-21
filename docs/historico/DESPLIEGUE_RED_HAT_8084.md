# Guía de actualización en Red Hat Enterprise Linux — CRT VMR 5G con login

**Versión 8.0 — Se conserva la interfaz clásica y los cálculos de la v7.**

> **Importante:** los ZIP `crt-vmr-5g-publico` y `CRT_VMR_5G_proyecto_despliegue` recibidos describen explícitamente una aplicación **sin login**. Este paquete implementa un **nuevo login en el servidor Python**, sin credenciales predeterminadas. Si el login anterior estaba en Nginx, Apache, otro backend o un servicio corporativo, ese acceso **no se ha podido recuperar** de los ZIP; coordine con el administrador si debe conservarse el SSO/LDAP/integración institucional. La v8 incluye una cuenta local configurable, no SSO ni recuperación de contraseñas.

**Requisitos:** Python 3.9 o superior, systemd y, para acceso remoto, Nginx con HTTPS. En RHEL 8 quizás necesite `sudo dnf install python39` y sustituir `/usr/bin/python3` por `/usr/bin/python3.9` en la unidad systemd y en los comandos. Compruebe `python3 --version` antes de instalar. No se requieren paquetes pip.

## 1. Arquitectura y puerto 8084

**Opción A — Recomendada, cuando 8084 ya es el puerto interno del servicio:**

`navegador → HTTPS :443 (Nginx existente) → http://127.0.0.1:8084 (Python con login)`

En esta opción la calculadora **sigue ejecutándose en el 8084**, pero el usuario entra por el dominio HTTPS del portal. **No abra 8084 en firewalld**. Si ya existe un proxy, conserve el dominio/certificado y cambie solo su `location` si hace falta.

**Opción B — Solo si los usuarios entraban a `:8084` desde fuera y deben mantener esa URL:**

`navegador → HTTPS :8084 (Nginx) → http://127.0.0.1:18084 (Python con login)`

Aquí el puerto visible seguirá siendo 8084, pero Python cambia de puerto para evitar conflicto. La configuración de ejemplo está en `nginx-publico-8084-ssl.conf.example` y el servicio alternativo `crt-vmr-5g-publico-8084.service.example`. Requiere certificado TLS válido, firewall y SELinux según la sección 7. Nunca publique un formulario de contraseña por HTTP sin cifrar.

## 2. Identifique qué ocupa actualmente el 8084 (no borre nada todavía)

Ejecute en Red Hat:

```bash
sudo ss -ltnp | grep ':8084' || true
sudo systemctl status crt-vmr-5g --no-pager || true
sudo systemctl cat crt-vmr-5g || true
sudo nginx -t  # solo si ya usa nginx
```

Confirme que el puerto 8084 pertenece a este proyecto. **Si pertenece a otra aplicación o al mismo Nginx, no lo detenga**: identifique primero el servicio y utilice la opción correcta. Los comandos siguientes suponen que el servicio existente se llama `crt-vmr-5g` y está instalado en `/opt/crt-vmr-5g` (como el ZIP público original).

## 3. Respalde la aplicación y su servicio anterior

Transfiera `crt-vmr-5g-con-login-redhat-8084.zip` al servidor (SCP/SFTP); después:

```bash
FECHA=$(date +%Y%m%d-%H%M%S)
sudo mkdir -p /var/backups/crt-vmr-5g
sudo cp -a /opt/crt-vmr-5g "/var/backups/crt-vmr-5g/app-$FECHA"    # si la ruta existe
sudo cp -a /etc/systemd/system/crt-vmr-5g.service "/var/backups/crt-vmr-5g/service-$FECHA"  # si existe
sudo cp -a /etc/crt-vmr-5g.env "/var/backups/crt-vmr-5g/auth-$FECHA.env"  # si existía
```

Conserve también una copia del bloque existente de Nginx o Apache si va a modificarlo. Resguarde los respaldos porque pueden contener credenciales de versiones antiguas.

## 4. Copie la versión completa al mismo directorio

Descomprima el ZIP en un directorio temporal:

```bash
mkdir -p /tmp/vmr8
unzip -o crt-vmr-5g-con-login-redhat-8084.zip -d /tmp/vmr8
cd /tmp/vmr8/crt-vmr-5g-publico
```

Instale con privilegios de administrador:

```bash
sudo getent group crt-vmr >/dev/null || sudo groupadd --system crt-vmr
id crt-vmr >/dev/null 2>&1 || sudo useradd --system --gid crt-vmr --no-create-home --shell /sbin/nologin crt-vmr
sudo install -d -m 755 /opt/crt-vmr-5g
sudo cp -a . /opt/crt-vmr-5g/
sudo chown -R root:root /opt/crt-vmr-5g
sudo chmod 755 /opt/crt-vmr-5g /opt/crt-vmr-5g/assets /opt/crt-vmr-5g/archivos
```

No utilice `rsync --delete` sin revisar los datos que ya guarda su servidor. El `server.py` restringe los archivos publicables a una lista explícita.

## 5. Cree el usuario y su contraseña (solo una vez)

```bash
sudo python3 /opt/crt-vmr-5g/create_login.py --username analista --output /etc/crt-vmr-5g.env
```

La herramienta solicitará una **contraseña nueva de mínimo 12 caracteres** dos veces, sin mostrarla en pantalla. Guarda un hash PBKDF2-SHA256 y el archivo en modo 600, **no** la contraseña en texto claro. Cambie `analista` por el usuario institucional que prefiera. **No existe usuario/clave predefinido.**

Si ya tiene el archivo `/etc/crt-vmr-5g.env` de esta versión y desea **cambiar la contraseña**, use `--replace`; esto invalida las sesiones después del reinicio:

```bash
sudo python3 /opt/crt-vmr-5g/create_login.py --username analista --output /etc/crt-vmr-5g.env --replace
```

El archivo mantiene `VMR_COOKIE_SECURE=1`: obliga a usar HTTPS para que el navegador envíe la cookie. **No cambie este valor a 0 en producción.**

## 6. Reemplace y reinicie solamente el servicio de esta calculadora

**Opción A (Python en 127.0.0.1:8084):**

```bash
sudo cp /opt/crt-vmr-5g/crt-vmr-5g.service /etc/systemd/system/crt-vmr-5g.service
sudo systemctl daemon-reload
sudo systemctl enable crt-vmr-5g
sudo systemctl restart crt-vmr-5g
sudo systemctl status crt-vmr-5g --no-pager
```

Si todavía no existía el servicio, `restart` lo inicia después de `enable`.

Compruebe desde el propio servidor:

```bash
curl -i http://127.0.0.1:8084/healthz
# HTTP/1.0 200 OK; cuerpo: ok
curl -I http://127.0.0.1:8084/
# HTTP/1.0 302 Found; Location: /login
curl -I http://127.0.0.1:8084/assets/model.js
# HTTP/1.0 401 Unauthorized antes del login
sudo ss -ltnp | grep ':8084'
sudo journalctl -u crt-vmr-5g -n 50 --no-pager
```

Estas pruebas `curl` no dependen de la cookie `Secure`. **La autenticación interactiva del navegador debe hacerse mediante HTTPS**.

## 7. Nginx, HTTPS y SELinux (Opción A)

Si su Nginx **ya atiende** el dominio y HTTPS, **no cree otro bloque server para el mismo dominio**. En el bloque existente debe haber un `location /` (o la ubicación exclusiva para esta app) que envíe **TODAS** las rutas a Python:

```nginx
location / {
    proxy_pass http://127.0.0.1:8084;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

**No sirva `index.html`, `assets` ni `archivos` directamente con `root` o `alias` de Nginx**, porque se saltaría la autorización de Python. Como punto de partida, consulte `nginx.conf.example` (requiere sustituir dominio y certificados).

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Si hay un **502** y SELinux está Enforcing, en RHEL puede requerirse:

```bash
sudo getsebool httpd_can_network_connect
sudo setsebool -P httpd_can_network_connect on
sudo nginx -t && sudo systemctl reload nginx
```

Es la opción documentada por Red Hat para permitir conexiones de Nginx a backends. Aplique esta modificación de política solo si es necesaria y está autorizada por las reglas de seguridad de su institución. No hace falta abrir `8084/tcp` en `firewalld` si el backend queda en `127.0.0.1`.

## 8. Opción B: HTTPS externo en 8084

Solo para instalaciones donde la URL anterior era `http://IP:8084` o `https://dominio:8084` y se desea **conservar el puerto visible 8084**. Primero configure un certificado TLS de dominio: la URL final debe ser `https://SU-DOMINIO:8084/`. No se recomienda acceso HTTP directo con credenciales.

Use `crt-vmr-5g-publico-8084.service.example` como `/etc/systemd/system/crt-vmr-5g.service`: escucha en **127.0.0.1:18084**. Use `nginx-publico-8084-ssl.conf.example` como nuevo bloque Nginx, adaptando dominio/certificados. No deje activo el backend antiguo en 8084; no pueden compartir el mismo puerto.

```bash
sudo cp /opt/crt-vmr-5g/crt-vmr-5g-publico-8084.service.example /etc/systemd/system/crt-vmr-5g.service
sudo systemctl daemon-reload
sudo systemctl restart crt-vmr-5g
curl -i http://127.0.0.1:18084/healthz
```

Instale y adapte el archivo Nginx de ejemplo en `/etc/nginx/conf.d/` después de revisar los bloques existentes (evite duplicarlos). Para el puerto TLS 8084, SELinux puede requerir `policycoreutils-python-utils` y etiquetar el puerto para Nginx:

```bash
sudo semanage port -l | grep http_port_t
# Si 8084 no está registrado, y no está asignado a otro tipo:
sudo semanage port -a -t http_port_t -p tcp 8084
sudo setsebool -P httpd_can_network_connect on
sudo firewall-cmd --permanent --add-port=8084/tcp
sudo firewall-cmd --reload
sudo nginx -t && sudo systemctl reload nginx
```

En esta **Opción B**, `8084` lo escucha Nginx y `18084` Python. Revise certificados y DNS antes de cambiar el servicio existente. **No ejecute los pasos de firewall/SELinux de la opción B si sigue la opción A.**

## 9. Verificaciones funcionales

Abra `https://SU-DOMINIO/` (A) o `https://SU-DOMINIO:8084/` (B):

1. Sin sesión aparece **Iniciar sesión**. No debe cargar la calculadora ni descargarse el Excel sin login.
2. Ingrese usuario y contraseña creados en el paso 5.
3. Compruebe las pestañas Calculadora, Descuentos y obligaciones, Resultados por región, Cómo se calcula y Glosario.
4. La modalidad sigue usando un **select**, sin slider. En **Editar valores de la modalidad** modifique Ampliación de cobertura y Modernización (suman 100%) y observe la actualización de montos y tabla.
5. Descargue CSV y el Excel del 15 de octubre, y cierre sesión. El archivo XLSX vuelve a quedar protegido.
6. Verifique con las entradas base: VMR 600 MHz **5,822,459,759.62 MXN**, 800 MHz **1,398,617,016.46 MXN**, 2.5 GHz **273,481,832.24 MXN**. Telcel / Cobertura / 10%: **8,174,344,267.76 MXN** en 10 años, 484 radiobases, 1,452 localidades.

Pruebas técnicas (opcionales en la estación de desarrollo; Node.js **no** se requiere en producción):

```bash
cd /opt/crt-vmr-5g
python3 -B -m unittest -v tests/test_server.py
node --test tests/model.test.mjs
```

## 10. Revertir a la versión anterior si algo falla

Use **sus rutas reales** de respaldo creadas en el paso 3, por ejemplo:

```bash
sudo systemctl stop crt-vmr-5g
sudo cp -a /var/backups/crt-vmr-5g/app-FECHA/. /opt/crt-vmr-5g/
sudo cp /var/backups/crt-vmr-5g/service-FECHA /etc/systemd/system/crt-vmr-5g.service
sudo systemctl daemon-reload
sudo systemctl start crt-vmr-5g
sudo systemctl status crt-vmr-5g --no-pager
```

Reemplace `FECHA` por el identificador real y restaure además Nginx si se modificó. **Ojo:** la versión pública original no incluía autenticación; revertirla puede quitar el login integrado. Revise el control de acceso externo antes de dejarla expuesta.

## Notas de seguridad y compatibilidad

- Sin contraseñas fijas en el ZIP, ni base de datos, ni API externa. Una cuenta local; para múltiples usuarios / SSO / LDAP hay que conectar la autenticación institucional.
- Hash PBKDF2-SHA256 (310,000 iteraciones), intentos fallidos limitados, CSRF para formularios y cookies `HttpOnly`, `SameSite=Strict`, `Secure` (HTTPS). Las sesiones se guardan en memoria y caducan a las 8 horas; se invalidan si reinicia el servicio.
- El login protege todas las rutas de la calculadora y su Excel; los recursos de la pantalla de acceso (CSS/logotipo/favicon) y `/healthz` siguen públicos.
- Mantenga habilitado HTTPS y las políticas de seguridad de Red Hat. El proceso Python debe correr sin privilegios mediante systemd.
- Los parámetros de escenarios enviados en enlaces compartidos forman parte de la URL; evite enviar enlaces con datos que considere sensibles.
