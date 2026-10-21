# Ajuste visual del enlace de registro — CRT VMR 5G v13

Se conservan íntegros los endpoints, las sesiones, las credenciales, el registro protegido y las fórmulas de la calculadora.

## Cambios

- `login.html`: elimina el texto «¿No tiene una cuenta?» y el botón «Crear cuenta con invitación». Añade un separador `o` y el enlace «Registrarme» a `/crear-cuenta`.
- `assets/login.css`: estiliza el separador y el enlace de forma discreta, inspirada en la captura de la Ventanilla Electrónica CRT, sin copiar recursos externos.
- `tests/test_registration.py`: comprueba las nuevas etiquetas y la ruta.

**Importante:** es un cambio de presentación únicamente. El servidor continúa solicitando el código de invitación para autorizar las cuentas nuevas. No se deshabilita ni se abre al público el endpoint de registro.

## Instalar solo este cambio en el Red Hat existente (8084)

1. Subir el ZIP complementario `parche-crt-registro-v13.zip` a `/depi/dgp/DEI_DATOS/SATyS`.
2. Ejecutar:

```bash
cd /depi/dgp/DEI_DATOS/SATyS
APP="$PWD/portal_crt_vmr5g_v11_8084"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$PWD/backup/login-$STAMP/assets"
cp -a "$APP/login.html" "$PWD/backup/login-$STAMP/login.html"
cp -a "$APP/assets/login.css" "$PWD/backup/login-$STAMP/assets/login.css"
unzip -t parche-crt-registro-v13.zip
unzip -o parche-crt-registro-v13.zip -d "$APP"
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8084/login
```

En la versión 11 que sirves con Python, los archivos HTML/CSS se cargan por solicitud; no se requiere reiniciar `systemd`. En Chrome usar Ctrl+Shift+R. El ZIP completo basado en React requiere compilar el frontend antes de usarlo en producción; este parche visual NO migra el servidor v11 a React.
