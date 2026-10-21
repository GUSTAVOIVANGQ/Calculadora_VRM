# CRT VMR 5G — proyecto completo v11 con login y creación de cuentas

## Qué se conserva y qué se agrega

Este ZIP toma como base **CRT VMR 5G v10** (no la página web del ejemplo de la captura). Se conservan el diseño de login existente (`login.html`, `assets/login.css`, `create_login.py`), el usuario administrador definido en `/etc/crt-vmr-5g.env`, la interfaz clásica, los campos editables con formato `1,234,567.89` y flechas ▲/▼, la tabla de descuentos y los cálculos v10.

Se añade exclusivamente un enlace **«Crear cuenta con invitación»** en el login, la página `/crear-cuenta`, cuentas adicionales almacenadas en SQLite local, endpoints JSON de autenticación y herramientas de registro/administración. **No se accede a `laboratorios.ift.org.mx`, no se reutilizan sus credenciales ni se conecta con ese login externo.** Si el login **realmente instalado** en Red Hat es distinto al que trae este ZIP, debe integrarse en su backend antes de reemplazar archivos; la captura no aporta ese código.

La creación de cuentas **está deshabilitada hasta que el administrador genera un código de invitación**. Es una protección deliberada para no abrir los datos de una calculadora restringida a cualquier visitante. El código se entrega a las personas autorizadas; su hash se guarda en el entorno y la contraseña de cada usuario se almacena como PBKDF2-SHA256 en base SQLite privada. No hay usuarios, contraseñas ni invitaciones predeterminados.

## Endpoints operativos

| Método | Ruta | Función | Acceso |
|---|---|---|---|
| GET | `/login` | Mostrar el login que venía en la v10 | Público |
| POST | `/login` | Autenticar y crear cookie de sesión (formulario, csrf) | Público |
| GET | `/crear-cuenta` | Formulario para crear cuenta | Público |
| POST | `/crear-cuenta` | Registrar cuenta con invitación y abrir sesión | Código de invitación |
| GET / POST | `/register` | Alias de `/crear-cuenta` | Igual |
| POST | `/logout` | Cerrar sesión, requiere token CSRF de la sesión | Con sesión |
| GET | `/api/v1/auth/status` | `{authenticated, registrationEnabled}` | Público |
| GET | `/api/v1/auth/csrf` | Emite token efímero y de un solo uso para cliente JSON | Público |
| POST | `/api/v1/auth/login` | Inicia sesión por JSON, emite cookie | JSON + CSRF |
| POST | `/api/v1/auth/register` | Crea una cuenta por JSON, emite cookie | JSON + CSRF + invitación |
| GET | `/healthz`, `/api/v1/health` | Estado de backend | Público |
| GET | `/api/v1/metadata`, `/api/v1/defaults` | Catálogos y valores base | Con sesión |
| POST | `/api/v1/calculate`, `/api/v1/calculate/vmr`, `/api/v1/calculate/discounts` | Cálculos actualizados | Con sesión |

**Ejemplo para una aplicación cliente** (mismo origen HTTPS, las cookies son `HttpOnly`, `Secure` y `SameSite=Strict`):

```js
const { csrf } = await (await fetch('/api/v1/auth/csrf')).json();
const resp = await fetch('/api/v1/auth/login', {
  method: 'POST', credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ csrf, username, password })
});
if (!resp.ok) throw new Error('No fue posible iniciar sesión');
location.assign('/');
```

Para crear cuenta JSON, primero obtenga *otro* token en `/api/v1/auth/csrf`, luego envíe:

```json
{
  "csrf": "TOKEN_OBTENIDO",
  "username": "usuario_nuevo",
  "password": "CONTRASEÑA_ELEGIDA",
  "confirmPassword": "MISMA_CONTRASEÑA",
  "inviteCode": "CODIGO_ENTREGADO_POR_ADMINISTRADOR"
}
```

Con `Content-Type: application/json` a `POST /api/v1/auth/register`. Responde HTTP **201** y asigna cookie al crear cuenta; HTTP 400 por datos incorrectos, 403 por CSRF/registro deshabilitado, 429 por límite de intentos. El login JSON devuelve 200 o 401. **No escriba contraseñas reales en scripts, logs, comandos de shell ni capturas.** Los formularios HTML son el flujo habitual; no necesitan JavaScript.

## Despliegue en Red Hat ya instalado en puerto 8084

### 1. Identifique quién está escuchando en 8084 y la ruta real

```bash
sudo ss -ltnp | grep ':8084' || true
sudo systemctl status crt-vmr-5g --no-pager || true
sudo systemctl cat crt-vmr-5g
sudo systemctl show crt-vmr-5g -p User -p Group -p ExecStart -p WorkingDirectory
python3 --version
```

Los comandos siguientes asumen `crt-vmr-5g.service` y `/opt/crt-vmr-5g`, según el proyecto entregado. Si la unidad, ruta o login actual **no coincide**, detenga la sustitución y adapte la guía. No instale otro proceso que escuche el mismo puerto. Python 3.9 o superior; no requiere paquetes `pip` ni Node.js en producción.

Existen dos configuraciones comunes:

- **A.** HTTPS público en Nginx `:443` → Python en `127.0.0.1:8084`. Conserve el Nginx existente.
- **B.** HTTPS público en Nginx `:8084` → Python en `127.0.0.1:18084`. El **8084 público** sigue siendo 8084. Conserve ese Nginx y no traslade Python a 8084; configure la unidad según `crt-vmr-5g-publico-8084.service.example` solo si ya sigue esta arquitectura.

La app debe estar bajo HTTPS para ingresar contraseñas; no se recomienda publicar el puerto Python sin TLS. Asegúrese de que Nginx remita **todas las rutas** (login, registro, assets y API) al backend Python: no exponga `index.html` ni `assets/model.js` directamente con `root`/`alias`, porque eso eludiría el login.

### 2. Respaldo ANTES de tocar la aplicación

```bash
APP=/opt/crt-vmr-5g
FECHA=$(date +%Y%m%d-%H%M%S)
sudo install -d -m 0700 /var/backups/crt-vmr-5g
sudo cp -a "$APP" "/var/backups/crt-vmr-5g/app-$FECHA"
sudo systemctl cat crt-vmr-5g | sudo tee "/var/backups/crt-vmr-5g/unit-$FECHA.txt" >/dev/null
sudo test -f /etc/crt-vmr-5g.env && sudo cp -a /etc/crt-vmr-5g.env "/var/backups/crt-vmr-5g/auth-$FECHA.env"
sudo test -f /var/lib/crt-vmr-5g/users.sqlite3 && sudo cp -a /var/lib/crt-vmr-5g/users.sqlite3 "/var/backups/crt-vmr-5g/users-$FECHA.sqlite3"
```

No suba los respaldos con credenciales a Git ni a servicios públicos. Guarde también la configuración Nginx si va a cambiarla (normalmente **no** hace falta).

### 3. Verifique qué login hay realmente en su servidor

En la versión 10 que te entregué, el `server.py` original tiene SHA-256:

```text
aaa1666c935d50500f030f99aefc94a9f5b10f6b4958b369f7729c763a975f58
```

Compruebe en Red Hat:

```bash
sudo sha256sum /opt/crt-vmr-5g/server.py
```

**Si coincide**, podrá integrar el paquete completo sin perder ese login. Si **no coincide**, no sobrescriba `server.py`: puede ser otra versión o un SSO corporativo. Hay que integrar únicamente `accounts.py` y las rutas necesarias en su backend personalizado, o proporcionar los archivos reales del login del servidor. La captura de una web externa no es suficiente para reconstruir su autenticación.

### 4. Descomprima el ZIP y copie la versión 11

Suba el archivo `crt-vmr-5g-v11-completo-login-registro-redhat-8084.zip` al servidor mediante SFTP/SCP y ejecute (solamente después de verificar el punto 3):

```bash
mkdir -p /tmp/vmr11
unzip -q crt-vmr-5g-v11-completo-login-registro-redhat-8084.zip -d /tmp/vmr11
cd /tmp/vmr11/crt-vmr-5g-publico
python3 -m compileall -q server.py api.py accounts.py setup_registration.py manage_users.py
# Directorio real de la instalación existente
APP=/opt/crt-vmr-5g
sudo cp -a . "$APP/"
sudo chown -R root:root "$APP"
sudo restorecon -R "$APP" 2>/dev/null || true
```

**No reemplace** `/etc/crt-vmr-5g.env`, las contraseñas, el dominio, el certificado ni los archivos Nginx. La instalación **no** contiene un archivo `.env` con credenciales.

### 5. Habilite directorio persistente de usuarios sin cambiar el puerto ni ExecStart

Confirme el usuario bajo el que corre systemd (en la unidad de referencia es `crt-vmr`):

```bash
sudo systemctl show crt-vmr-5g -p User -p Group
```

Si es `crt-vmr`, ejecute:

```bash
sudo install -d -o crt-vmr -g crt-vmr -m 0700 /var/lib/crt-vmr-5g
sudo mkdir -p /etc/systemd/system/crt-vmr-5g.service.d
printf '[Service]\nStateDirectory=crt-vmr-5g\nStateDirectoryMode=0700\n' | \
  sudo tee /etc/systemd/system/crt-vmr-5g.service.d/usuarios.conf
sudo systemctl daemon-reload
```

El directorio debe ser **escribible** por el usuario de servicio, aunque `ProtectSystem=strict` esté activo. Si el usuario o ruta son distintos, adapte las órdenes. La base `users.sqlite3` se crea con permisos privados 0600 en el primer inicio.

### 6. Active el endpoint Crear cuenta mediante invitación

**No vuelva a ejecutar `create_login.py`** si ya funciona su cuenta anterior: eso cambiaría las credenciales. En su lugar ejecute:

```bash
sudo python3 "$APP/setup_registration.py" --env /etc/crt-vmr-5g.env
```

El programa **conserva `VMR_AUTH_USER` y `VMR_PASSWORD_HASH`** y agrega únicamente `VMR_REGISTRATION_CODE_HASH`. Imprime un nuevo código de invitación **una sola vez**. Cópielo a un gestor seguro y entréguelo solo a los usuarios permitidos.

```bash
sudo systemctl restart crt-vmr-5g
sudo systemctl status crt-vmr-5g --no-pager
sudo journalctl -u crt-vmr-5g -n 50 --no-pager
```

Para revocar futuras invitaciones (las cuentas existentes siguen funcionando):

```bash
sudo python3 "$APP/setup_registration.py" --env /etc/crt-vmr-5g.env --disable
sudo systemctl restart crt-vmr-5g
```

Para generar **otro código**, ejecute de nuevo el comando sin `--disable` y reinicie; invalida el código previo, no las cuentas existentes.

### 7. Verifique el servicio, login, registro y API

Si **Python escucha en 8084 (caso A)**:

```bash
curl -i http://127.0.0.1:8084/healthz
curl -i http://127.0.0.1:8084/api/v1/auth/status
curl -I http://127.0.0.1:8084/login
curl -I http://127.0.0.1:8084/crear-cuenta
curl -I http://127.0.0.1:8084/api/v1/metadata
```

Debe aparecer `ok`, `registrationEnabled:true`, **200** para login/crear cuenta y **401** para `/api/v1/metadata` sin sesión. En el caso **B**, haga las pruebas internas al backend en `127.0.0.1:18084` y las externas en `https://SU-DOMINIO:8084`.

Compruebe en el navegador con HTTPS:

1. Abra la URL institucional **de su calculadora**, no la del sitio mostrado como referencia.
2. Debe verse la pantalla anterior de login y el nuevo vínculo **«Crear cuenta con invitación»**.
3. Cree una cuenta con usuario nuevo, contraseña propia (mínimo 12 caracteres) y código de invitación.
4. La aplicación debe entrar automáticamente a la calculadora. Cierre sesión y vuelva a entrar con la nueva cuenta desde `/login`.
5. Verifique que la antigua cuenta de administrador sigue pudiendo iniciar sesión.
6. Compruebe en la calculadora las flechas ▲/▼, formato de comas, descuentos por obligación, selector de modalidad y endpoints protegidos.

### 8. Administrar las cuentas locales registradas

Ejecutar como usuario del servicio (ajuste `crt-vmr` si es distinto):

```bash
sudo -u crt-vmr python3 "$APP/manage_users.py" --list
sudo -u crt-vmr python3 "$APP/manage_users.py" --reset-password usuario_nuevo
sudo -u crt-vmr python3 "$APP/manage_users.py" --delete usuario_nuevo
sudo systemctl restart crt-vmr-5g  # invalidar sesiones previas tras eliminar una cuenta
```

El usuario principal definido en `/etc/crt-vmr-5g.env` **no** se modifica ni se elimina con `manage_users.py`. No hay enlace de recuperación de contraseña por correo ni integración con LDAP/SSO.

### 9. Si falla: reversión

Reemplace `FECHA` por la fecha utilizada en el respaldo:

```bash
APP=/opt/crt-vmr-5g
sudo cp -a /var/backups/crt-vmr-5g/app-FECHA/. "$APP/"
sudo cp -a /var/backups/crt-vmr-5g/auth-FECHA.env /etc/crt-vmr-5g.env
sudo systemctl restart crt-vmr-5g
sudo journalctl -u crt-vmr-5g -n 50 --no-pager
```

Si añadió el drop-in `usuarios.conf` exclusivamente para esta versión, puede quitarlo al volver atrás y ejecutar `sudo systemctl daemon-reload`. No elimine `/var/lib/crt-vmr-5g/users.sqlite3` a menos que tenga una copia y realmente desee perder usuarios nuevos. Los reinicios invalidan las sesiones actuales, pero no las cuentas.

## Seguridad y límites

- Mantenga la entrada pública **bajo HTTPS**; `VMR_COOKIE_SECURE=1` impide sesión funcional por HTTP sin TLS. Un `curl` HTTP local valida salud/rutas, pero para **login** use HTTPS a través de Nginx.
- El registro no está abierto: precisa código de invitación aleatorio, CSRF, rate limit, validaciones y credenciales propias. El hash de la invitación está en `/etc/crt-vmr-5g.env` (0600), los hashes PBKDF2 en `/var/lib/crt-vmr-5g/users.sqlite3` (0600).
- No sirva `login.html`, `register.html`, `server.py`, `.env`, base SQLite ni los archivos de cálculo con Nginx `root` o `alias`: pase las peticiones al backend. Solo rutas autorizadas por el servidor Python son públicas.
- Las sesiones están en memoria; al reiniciar se requiere volver a iniciar sesión.
- No se conecta con el sitio de la captura `laboratorios.ift.org.mx`, ni se autentican allí usuarios. Para autenticar contra un sistema institucional/SSO real, haría falta documentación técnica de su endpoint y autorización de integración.
- Si SELinux bloquea el proxy en una instalación nueva, valide primero logs/auditoría y, si está permitido, `sudo setsebool -P httpd_can_network_connect on`. Si Nginx debe escuchar HTTPS en `8084`, ajuste **solo** el servidor web y los puertos SELinux/firewalld que correspondan: no abra el backend Python de manera indiscriminada.

## Pruebas incluidas

```bash
cd /opt/crt-vmr-5g
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/model.test.mjs tests/ui-format.test.mjs  # opcional, solo para pruebas
```

Los tests crean sus propios servidores temporales y DB SQLite en directorios temporales; no deberían tocar las cuentas reales del sistema.
