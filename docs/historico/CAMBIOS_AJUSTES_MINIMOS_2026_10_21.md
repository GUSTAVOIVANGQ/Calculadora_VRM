# CRT VMR 5G v11 — ajustes mínimos de interfaz (21-10-2026)

Esta entrega incluye el proyecto completo con login CRT y encabezado compacto de la instalación v11.

Cambios visuales:
- Se elimina el aviso amarillo de la pestaña Descuentos y obligaciones (incluida su actualización por JavaScript).
- Se ocultan ambos botones «Copiar enlace de este escenario», sin modificar las funciones internas de compartir escenarios.
- Se retiran las menciones visibles al «cuadro del 15 de octubre» y a «Valores base del cuadro».
- Siguen funcionando cálculos, tabla, exportación CSV, botón «Compartir escenario», flechas numéricas, login, alta de cuentas y endpoints.

## Actualización recomendada de la instalación existente (Red Hat 9, puerto 8084)

**La instalación actual ya tiene el servicio `crt-vmr-5g` con WorkingDirectory:
`/depi/dgp/DEI_DATOS/SATyS/portal_crt_vmr5g_v11_8084`**. No cambie ese servicio ni la configuración de credenciales.

1. Suba el archivo `crt-vmr5g-v11-solo-ajustes-ui.zip` al directorio `/depi/dgp/DEI_DATOS/SATyS`.
2. Ejecute los siguientes comandos:

```bash
cd /depi/dgp/DEI_DATOS/SATyS
APP="$PWD/portal_crt_vmr5g_v11_8084"
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$PWD/backup/ui-$STAMP/assets"
cp -a "$APP/index.html" "$PWD/backup/ui-$STAMP/index.html"
cp -a "$APP/assets/ui.js" "$PWD/backup/ui-$STAMP/assets/ui.js"
unzip -t crt-vmr5g-v11-solo-ajustes-ui.zip
unzip -oq crt-vmr5g-v11-solo-ajustes-ui.zip -d "$APP"
sudo systemctl is-active crt-vmr-5g
sudo systemctl is-enabled crt-vmr-5g
```

3. Abra la pestaña Descuentos y obligaciones y haga Ctrl+Shift+R. Si el servicio está activo no es necesario reiniciarlo para archivos de interfaz.
4. Si hay que restaurar, sustituya los dos archivos desde `backup/ui-<fecha>/`.

**No descomprima el proyecto completo encima del servicio existente si solamente quiere aplicar estos cambios visuales.**
El ZIP completo es para respaldo o despliegue íntegro en una carpeta nueva. Si crea una instalación nueva, configure sus credenciales y un servicio systemd según la guía de Red Hat ya incluida. No publique autenticación HTTP sin TLS fuera de una red interna restringida.
