# Instalación paralela en carpeta nueva y servicio permanente — CRT VMR 5G v11

**Servidor:** `srvmbcudaqa01` · **SO:** Red Hat Enterprise Linux 9.7 · **puerto existente:** `8084`

## Qué cambia y qué NO cambia

- Nueva carpeta: `/depi/dgp/DEI_DATOS/SATyS/portal_crt_vmr5g_v11_8084`.
- Se conserva `crt-vmr-5g.service`, el mismo puerto `8084`, el usuario `gustavo.garcia` y el `EnvironmentFile=-/etc/crt-vmr-5g.env` de la instalación actual.
- Se conserva sin modificaciones la carpeta anterior: `/depi/dgp/DEI_DATOS/SATyS/Calculadora_VMR/crt-vmr-5g-app`.
- Solo se añade **un override de WorkingDirectory** al servicio systemd existente. **NO copiar** el archivo `crt-vmr-5g.service` incluido en el ZIP, ya que es una plantilla para otra ruta (`/opt`).
- El login que trae v11 procede del paquete v10 suministrado anteriormente, **no necesariamente coincide con el código del login ya instalado**. Compare antes de efectuar el cambio de servicio. Si es distinto y se requiere conservarlo exactamente, DETENERSE: es necesario integrar el login actual en la v11.
- La autenticación debe exponerse con **HTTPS**; actualmente Python escucha `0.0.0.0:8084` directamente, por lo que el tráfico HTTP en claro no es adecuado para introducir contraseñas a través de redes no confiables. Coordine TLS con el administrador de red antes de acceso público.

## 1. Descomprimir en carpeta con nombre diferente

En la misma terminal que mostró `SATyS`:

```bash
cd /depi/dgp/DEI_DATOS/SATyS
ls -lh portal-crt-vmr5g-v11-redhat8084-renombrado.zip
unzip -t portal-crt-vmr5g-v11-redhat8084-renombrado.zip | tail -2
# Asegúrese de que aún no exista ese nombre:
if test -e portal_crt_vmr5g_v11_8084; then
  echo 'La carpeta ya existe: NO descomprimir encima'
else
  unzip portal-crt-vmr5g-v11-redhat8084-renombrado.zip
fi
cd portal_crt_vmr5g_v11_8084
/usr/bin/python3 -m compileall -q server.py api.py accounts.py setup_registration.py manage_users.py
ls -l login.html register.html index.html server.py
```

Si ya existe la carpeta, **no** use `unzip -o`: elija otro nombre y ajuste el override.

**Alternativa: utilizar el ZIP de v11 que YA está en `SATyS` (sin volver a subirlo):**

```bash
cd /depi/dgp/DEI_DATOS/SATyS
mkdir -p vmr_v11_descomprimido_temporal
unzip -q crt-vmr-5g-v11-completo-login-registro-redhat-8084.zip -d vmr_v11_descomprimido_temporal
if test -e portal_crt_vmr5g_v11_8084; then
  echo 'El destino ya existe; no cambiarlo'
else
  mv vmr_v11_descomprimido_temporal/crt-vmr-5g-publico portal_crt_vmr5g_v11_8084
fi
```

Esta alternativa no trae el archivo nuevo del override `systemd/95-portal-crt-vmr5g-v11-8084.conf`. **Después de verificar el login y hacer respaldo**, en el paso 4 sustituya el comando `sudo cp` por:

```bash
printf '[Service]\nWorkingDirectory=/depi/dgp/DEI_DATOS/SATyS/portal_crt_vmr5g_v11_8084\n' | \
  sudo tee /etc/systemd/system/crt-vmr-5g.service.d/95-portal-crt-vmr5g-v11-8084.conf
```

## 2. Verificación obligatoria del login antes de sustituir el servicio

```bash
ANTERIOR=/depi/dgp/DEI_DATOS/SATyS/Calculadora_VMR/crt-vmr-5g-app
NUEVO=/depi/dgp/DEI_DATOS/SATyS/portal_crt_vmr5g_v11_8084
sudo ls -l "$ANTERIOR/server.py" "$ANTERIOR/login.html" "$NUEVO/server.py" "$NUEVO/login.html"
sudo sha256sum "$ANTERIOR/server.py" "$NUEVO/server.py"
sudo diff -u "$ANTERIOR/login.html" "$NUEVO/login.html" | head -80
```

- Si el archivo viejo `login.html` no existe o las pantallas/rutas son diferentes, **NO cambie todavía el servicio**; primero revise la autenticación existente. La traza `FileNotFoundError` que mostró el servicio podría deberse a un archivo HTML faltante.
- Si el login actual es una versión personalizada, hay que portarlo al servidor actualizado; **no** basta con conservar `/etc/crt-vmr-5g.env`.
- Como referencia, el hash SHA-256 de `server.py` en el paquete original v10 era `aaa1666c935d50500f030f99aefc94a9f5b10f6b4958b369f7729c763a975f58`.

**Continúe solo después de verificar compatibilidad o aceptar expresamente el login entregado con la versión 11.**

## 3. Respaldo seguro ANTES de cambiar systemd

```bash
FECHA=$(date +%Y%m%d-%H%M%S)
RESPALDO=/var/backups/portal-crt-vmr5g-8084/$FECHA
sudo install -d -m 0700 "$RESPALDO"
sudo cp -a /depi/dgp/DEI_DATOS/SATyS/Calculadora_VMR/crt-vmr-5g-app "$RESPALDO/"
sudo systemctl cat crt-vmr-5g | sudo tee "$RESPALDO/systemd-anterior.txt" >/dev/null
if sudo test -f /etc/crt-vmr-5g.env; then sudo cp -a /etc/crt-vmr-5g.env "$RESPALDO/"; fi
sudo systemctl is-enabled crt-vmr-5g
sudo systemctl is-active crt-vmr-5g
```

La base de datos de usuarios está fuera de la carpeta del proyecto. Si se requiere hacerle un respaldo coherente mientras el servicio está activo, utilizar `sqlite3.Connection.backup()` o detener el servicio brevemente antes de copiarla; no sobrescribir ni borrar `/var/lib/crt-vmr-5g`.

## 4. Actualizar el WorkingDirectory del servicio existente (solo cuando sea seguro)

Este procedimiento **no crea otro servicio** ni otro proceso adicional en 8084; reinicia el ya existente.

```bash
NUEVO=/depi/dgp/DEI_DATOS/SATyS/portal_crt_vmr5g_v11_8084
sudo install -d -m 0755 /etc/systemd/system/crt-vmr-5g.service.d
sudo cp "$NUEVO/systemd/95-portal-crt-vmr5g-v11-8084.conf" \
  /etc/systemd/system/crt-vmr-5g.service.d/95-portal-crt-vmr5g-v11-8084.conf
sudo systemctl daemon-reload
sudo systemctl show crt-vmr-5g -p WorkingDirectory -p ExecStart -p User
sudo systemctl restart crt-vmr-5g
sudo systemctl status crt-vmr-5g --no-pager -l
```

Debe verse `WorkingDirectory=/depi/dgp/DEI_DATOS/SATyS/portal_crt_vmr5g_v11_8084` y `ExecStart=/usr/bin/python3 server.py --bind 0.0.0.0 --port 8084` (puede aparecer con formato de propiedades systemd).

Si el servicio falla:

```bash
sudo journalctl -u crt-vmr-5g -n 80 --no-pager
```

## 5. Pruebas sin abrir un segundo proceso

```bash
sudo ss -ltnp | grep ':8084'
curl -i http://127.0.0.1:8084/healthz
curl -i http://127.0.0.1:8084/api/v1/auth/status
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8084/login
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8084/crear-cuenta
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8084/api/v1/metadata
```

Esperado: salud 200, estado JSON 200, login 200, crear cuenta 200 y metadata 401 si no hay sesión. `registrationEnabled` seguirá falso hasta habilitar registro por invitación.

## 6. Crear cuentas nuevas (opcional; **sin cambiar** contraseña existente)

Si ya se validó el login de v11 y existe `/etc/crt-vmr-5g.env`:

```bash
sudo /usr/bin/python3 /depi/dgp/DEI_DATOS/SATyS/portal_crt_vmr5g_v11_8084/setup_registration.py \
  --env /etc/crt-vmr-5g.env
sudo systemctl restart crt-vmr-5g
curl -s http://127.0.0.1:8084/api/v1/auth/status
```

El programa muestra una única vez un código de invitación. No lo comparta en capturas ni chats. El formulario estará en `/crear-cuenta`; las cuentas locales se guardan en `/var/lib/crt-vmr-5g/users.sqlite3` (si no hay un `VMR_USERS_DB` configurado).

## 7. Dejarlo funcionando tras cerrar SSH y al reiniciar Red Hat

```bash
sudo systemctl enable crt-vmr-5g
sudo systemctl is-enabled crt-vmr-5g
sudo systemctl is-active crt-vmr-5g
sudo systemctl status crt-vmr-5g --no-pager
```

`enabled` + `active` significa que **systemd lo mantiene en ejecución sin una terminal abierta** y lo iniciará en el siguiente arranque. Se ejecuta en segundo plano como servicio, no use `nohup`, `&` ni una nueva ejecución manual de `server.py` en 8084.

Cierre SSH con `exit` y luego vuelva a conectar para comprobar:

```bash
sudo systemctl status crt-vmr-5g --no-pager
sudo ss -ltnp | grep ':8084'
```

## 8. Reversión inmediata SIN borrar la carpeta nueva

Si la v11 falla tras el cambio de directorio:

```bash
sudo rm -f /etc/systemd/system/crt-vmr-5g.service.d/95-portal-crt-vmr5g-v11-8084.conf
sudo systemctl daemon-reload
sudo systemctl restart crt-vmr-5g
sudo systemctl show crt-vmr-5g -p WorkingDirectory
sudo systemctl status crt-vmr-5g --no-pager
```

Esto devuelve la unidad a su `WorkingDirectory` anterior (salvo que haya **otro override previo**, que deberá revisar con `sudo systemctl cat crt-vmr-5g`). Conserva ambas carpetas y `/var/lib/crt-vmr-5g`.

## Observaciones importantes

- La unidad ya existente tiene `Restart=always`, `RestartSec=3` y `enabled`; por tanto cumple el requisito de permanecer tras cerrar terminal. Cambiar la carpeta no exige instalar un servicio nuevo.
- El servicio usa `/usr/bin/python3` (Python del sistema RHEL), **no necesariamente** el `python3` de Conda que aparece en su terminal. Por ello los comandos de verificación usan `/usr/bin/python3`.
- El servicio actual escucha en `0.0.0.0:8084` sin TLS gestionado por Python. No es recomendable ingresar contraseñas sobre HTTP público. Para uso externo implemente un terminador HTTPS autorizado por TI o limite el acceso a red confiable.
- No cambie ni copie el archivo `.service` de ejemplo del ZIP sobre `/etc/systemd/system/crt-vmr-5g.service` porque usa una ruta distinta de la real y puede provocar caída.
