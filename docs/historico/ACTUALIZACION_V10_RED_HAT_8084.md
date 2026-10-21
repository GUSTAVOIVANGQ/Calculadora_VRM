# CRT VMR 5G · Versión 10 · Flechas y endpoints JSON (Red Hat / puerto 8084)

## Lo que se conserva y lo que se amplía

- **Se mantiene el login** de la v9/v8: `login.html`, `assets/login.css`, `create_login.py`, configuración systemd/Nginx, usuario, contraseña y sus variables de entorno **no se modifican**.
- La lógica de la clase `Auth` del servidor permanece igual. En `server.py` solo se agregan rutas API y se autoriza `connect-src 'self'` para poder invocarlas desde el mismo origen.
- La interfaz clásica añade flechas ▲ y ▼ a los campos editables de VMR, precios MXN, INPC, población, cuotas, cobertura y editor de modalidad. Los miles siguen separados con comas y los decimales con punto.
- El modelo se mantiene intacto (`assets/model.js`, `assets/data.js`, `assets/controls.js`). La API incluye `api.py`, versión de las mismas fórmulas en Python sin dependencias externas, y **no necesita Node.js en producción**.

**Muy importante:** Los ZIP originales no incluían un login. Si tu sistema Red Hat usa un login **distinto** al de las entregas v8/v9 (SSO, Nginx Auth, servidor Python personalizado u otro), no reemplaces su `server.py` automáticamente. Usa la actualización **solo UI** y facilita el código del backend existente para incorporar los endpoints conservando ese login. Los endpoints requieren añadir rutas al backend; no aparecen instalando únicamente HTML/CSS/JS.

## Endpoints disponibles

| Método | Ruta | Requiere login | Resultado |
|---|---|---|---|
| GET | `/healthz` | No | Respuesta de texto `ok` (original) |
| GET | `/api/v1/health` | No | Estado JSON del servidor |
| GET | `/api/v1/metadata` | Sí | Bandas, operadores, modalidades y límites |
| GET | `/api/v1/defaults` | Sí | Escenario completo de valores base |
| POST | `/api/v1/calculate/vmr` | Sí | VMR y detalle de nueve regiones por banda |
| POST | `/api/v1/calculate/discounts` | Sí | Descuento seleccionado y tabla del 10% al 100% |
| POST | `/api/v1/calculate` | Sí | VMR y descuentos combinados |

Los POST reciben `Content-Type: application/json` y una propiedad `scenario` con los cambios deseados respecto del modelo base. Por ejemplo:

```json
{
  "scenario": {
    "spectrum": [30, 20, 10],
    "discounts": {
      "operator": "Telcel",
      "mode": "Cobertura",
      "percent": 20
    }
  }
}
```

Un escenario vacío `{ "scenario": {} }` utiliza todos los valores base. Se pueden enviar también valores completos de `population`, `q`, `coverage`, `references`, `benchmarkIncluded` y `discounts.allocations`, respetando su estructura. La API rechaza campos desconocidos, cifras no finitas, valores fuera de límites y modalidades inválidas. Devuelve 200 si la solicitud es válida, 401 sin sesión, 415 cuando falta JSON, 422 por datos inválidos. Los porcentajes no aplicables se identifican con `available:false` y la razón correspondiente. No se exponen contraseñas o tokens.

Desde el navegador, **después de iniciar sesión como siempre**, puede consultar la API con:

```js
const r = await fetch('/api/v1/calculate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ scenario: { spectrum: [30, 20, 10] } })
});
const resultado = await r.json();
console.log(resultado);
```

No se habilita CORS externo. Para otras aplicaciones o clientes de API, se necesita gestionar una sesión del mismo login o desarrollar un mecanismo de autenticación para esos clientes; **no hay tokens de API abiertos**.

## Despliegue seguro en tu Red Hat, conservando el puerto 8084

### 1. Identifica el servicio existente

```bash
sudo ss -ltnp | grep ':8084'
sudo systemctl cat crt-vmr-5g
```

Comprueba en `ExecStart` y `WorkingDirectory` que el directorio real sea `/opt/crt-vmr-5g`. Si no lo es, cambia `APP` en los comandos siguientes. No instales otro servicio que ocupe el mismo puerto.

### 2. Respalda todo ANTES de actualizar

```bash
APP=/opt/crt-vmr-5g
FECHA=$(date +%Y%m%d-%H%M%S)
sudo mkdir -p /var/backups/crt-vmr-5g
sudo cp -a "$APP" "/var/backups/crt-vmr-5g/app-$FECHA"
sudo systemctl cat crt-vmr-5g > "crt-vmr-5g-systemd-$FECHA.txt"
```

El respaldo incluye los archivos del login y del motor que ya tenías. Las credenciales privadas en `/etc/crt-vmr-5g.env` no deben empaquetarse ni enviarse a otra persona.

### 3. Descomprime la versión 10

```bash
unzip crt-vmr-5g-v10-completo-login-conservado-api-8084.zip
cd crt-vmr-5g-publico
APP=/opt/crt-vmr-5g
```

### 4. Revisa antes de actualizar el servidor (muy importante)

El SHA-256 del `server.py` de la **versión 9 entregada anteriormente** es:

```
b3082962914483aa4e9a34318bd453ba0c44327458b4e09ca634df3f8eea563c
```

Comprueba el archivo de tu servidor:

```bash
sudo sha256sum "$APP/server.py"
```

- **Si coincide**, tu backend parte de la versión 9: puedes agregar la API con el `server.py` de esta entrega sin perder el mecanismo de login, que no cambió.
- **Si no coincide**, **no reemplaces `server.py`**: podría contener tu login original, un proxy especial o personalizaciones. Actualiza solo la interfaz y solicita adaptar `api.py` y las rutas al servidor existente.

### 5. Instalación en servidor compatible con v9

```bash
sudo install -m 0644 index.html "$APP/index.html"
sudo install -m 0644 assets/ui.js "$APP/assets/ui.js"
sudo install -m 0644 assets/styles.css "$APP/assets/styles.css"
# Solo si se verificó el hash del server.py v9:
sudo install -m 0644 api.py "$APP/api.py"
sudo install -m 0644 server.py "$APP/server.py"
sudo systemctl restart crt-vmr-5g
sudo systemctl status crt-vmr-5g --no-pager
```

**No reemplaces** `login.html`, `login.css`, `create_login.py`, variables de entorno, servicio systemd ni Nginx. En instalaciones con SELinux, conserva el propietario y contexto esperado (`sudo restorecon -Rv "$APP"` si tienes políticas etiquetadas para la ruta y se requiere).

### 6. Comprobaciones

```bash
sudo ss -ltnp | grep ':8084'
curl -i http://127.0.0.1:8084/healthz
curl -i http://127.0.0.1:8084/api/v1/health
curl -i http://127.0.0.1:8084/api/v1/metadata
```

`/api/v1/health` debe responder `200` en JSON, y `/api/v1/metadata` debe responder `401` **sin login**. La aplicación debe conservar el acceso por el mismo dominio/IP y las mismas credenciales, usando HTTPS público. Si antes Nginx escuchaba públicamente en `:8084` y Python escuchaba en otro puerto, **no cambies los puertos del servicio existente**: comprueba primero la topología actual; los ejemplos anteriores de curl a `127.0.0.1:8084` aplican solo cuando Python escucha ahí.

Después de iniciar sesión desde el navegador, verifica las flechas en `Espectro a valorar`, `Costo por radiobase` y `Ampliación de cobertura`, y que la tabla de descuentos se actualice al cambiar los valores.

Para los endpoints protegidos, usa una sesión válida; una solicitud curl sin las cookies del login devuelve 401 por diseño.

### 7. Revertir si algo falla

```bash
# Utiliza la fecha real generada al respaldar:
APP=/opt/crt-vmr-5g
sudo cp -a /var/backups/crt-vmr-5g/app-FECHA/. "$APP/"
sudo systemctl restart crt-vmr-5g
```

Reemplaza `app-FECHA` por el directorio real; comprueba los logs si hay problemas:

```bash
sudo journalctl -u crt-vmr-5g -n 80 --no-pager
```

## Paquetes que se entregan

- **ZIP completo v10:** calculadora, login idéntico a v9, servidor con endpoints, nueva API, guías y tests.
- **ZIP solo interfaz v10:** exclusivamente `index.html`, `assets/ui.js` y `assets/styles.css`, más esta guía. Preserva cualquier login y backend preexistentes; **no instala endpoints**.
- **Vista HTML independiente:** para revisar la interfaz sin login; tampoco instala la API del backend.

## Pruebas para validación antes del despliegue

```bash
python3 -m unittest discover -s tests -p 'test_server.py'
python3 -m unittest discover -s tests -p 'test_api.py'
node --test tests/model.test.mjs tests/ui-format.test.mjs
```

El Node.js indicado es opcional y **solo para las pruebas del motor JavaScript**.
