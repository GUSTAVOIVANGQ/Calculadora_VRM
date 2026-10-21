# Actualización segura en Red Hat — CRT VMR 5G (puerto 8084)

## Importante: conservar el login existente

Los ZIP originales `crt-vmr-5g-publico` y `CRT_VMR_5G_proyecto_despliegue` **no incluyen** el login que mencionas. Puede estar en el servidor actual, Nginx, Apache, otra aplicación o un proxy. **No se modifica ni se sustituye su autenticación** durante esta actualización. Esta entrega mantiene intactos los archivos de autenticación de la v8. Si en producción se usa un login diferente, no reemplaces esos archivos ni la configuración del servidor; aplica únicamente los archivos estáticos.

**No copies el `server.py`, `crt-vmr-5g.service`, configuraciones de Nginx ni archivos de credenciales del ZIP sobre los que funcionan en producción.** El paquete incluye los originales de v8 sin modificaciones; el método recomendado reemplaza solo la interfaz. Si el servidor en uso fue construido a medida, hay que verificar que sirva los nuevos archivos de `assets/` y `archivos/`, manteniendo las reglas de acceso del login. No publiques el directorio estático fuera de la protección del login.

## 1. Identificar el proceso y hacer copia de seguridad

```bash
sudo ss -ltnp | grep ':8084'
sudo systemctl status crt-vmr-5g --no-pager
sudo mkdir -p /var/backups/crt-vmr-5g
FECHA=$(date +%Y%m%d-%H%M%S)
sudo cp -a /opt/crt-vmr-5g /var/backups/crt-vmr-5g/app-$FECHA
```

Estos comandos suponen que la instalación actual está en `/opt/crt-vmr-5g`. **Verifica primero la ruta real** con `systemctl cat crt-vmr-5g` o la configuración del servicio. Si es distinta, ajústala.

## 2. Descomprimir

```bash
unzip crt-vmr-5g-v9-login-sin-cambios.zip
cd crt-vmr-5g-publico
```

## 3. Actualizar solamente la interfaz y recursos de la calculadora

Cambia `/opt/crt-vmr-5g` por la ruta real si corresponde. El login previo y servicio no se tocan.

```bash
APP=/opt/crt-vmr-5g
sudo install -m 0644 index.html "$APP/index.html"
sudo install -m 0644 assets/ui.js "$APP/assets/ui.js"
sudo install -m 0644 assets/styles.css "$APP/assets/styles.css"
```

**Atención:** estos comandos solo sustituyen la página de la calculadora, su JavaScript y su CSS. No modifican `login.html`, `login.css`, `server.py`, credenciales ni la configuración de systemd/Nginx. Si necesitas agregar nuevos recursos del motor (`model.js`, `data.js`, `controls.js`, el Excel), conserva también el control de acceso sobre esas rutas.

Si tu instalación anterior usa un login que comparte el archivo `index.html` (por ejemplo, el login se muestra allí mediante JavaScript), **no reemplaces** `index.html` sin integrar primero ese código con el nuevo archivo. Si no estás seguro, conserva el servicio y comparte el `index.html`/configuración del login actual para integrarlo sin perder el acceso.

## 4. Verificación sin cambiar login ni puerto

```bash
sudo ss -ltnp | grep ':8084'
curl -I http://127.0.0.1:8084/
```

La respuesta de `curl` depende del login instalado; puede ser una redirección (302/303) o una respuesta autorizada. En el navegador, abre **la misma URL y el mismo método de acceso que utilizabas antes**; inicia sesión y revisa los campos monetarios (por ejemplo, `1,234,567.89 MXN`) y la tabla de descuentos. En un entorno con HTTPS, realiza también la prueba usando el dominio y certificado reales.

No es necesario reiniciar un servicio estático si sirve los archivos de disco directamente. Si utiliza cache o empaquetado, reinícialo solo tras confirmar qué proceso lo ejecuta; no cambies el puerto.

## Reversión

```bash
# Usa la ruta del respaldo que realmente hayas creado:
sudo cp -a /var/backups/crt-vmr-5g/app-FECHA/. /opt/crt-vmr-5g/
```

**Nota de seguridad:** copiar archivos públicos por encima de un proyecto que contiene login solo es seguro si el servidor conserva exactamente las rutas protegidas. Revisa permisos y propiedad de los archivos y prueba que un usuario sin autenticación no pueda acceder a `/`, `/assets/model.js`, ni a los documentos.

## Si utilizas la autenticación de la entrega v8

Los archivos `login.html`, `assets/login.css`, `server.py`, `create_login.py`, `crt-vmr-5g.service` y `nginx-publico-8084-ssl.conf.example` son idénticos a los de la v8. No es necesario configurar contraseñas nuevamente, modificar el servicio ni cambiar el puerto. Copia solo `index.html`, `assets/ui.js`, `assets/styles.css`; si faltan recursos del modelo, copia también `assets/model.js`, `assets/data.js`, `assets/controls.js` y el Excel **en rutas que sigan protegidas por tu login**.

No sustituyas `index.html` si tu login anterior estaba implementado en ese mismo archivo en vez de en `/login`. En ese caso, se necesita el archivo original del servidor para conservarlo sin cambios.
