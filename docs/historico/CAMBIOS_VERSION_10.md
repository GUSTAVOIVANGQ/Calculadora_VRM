# CRT VMR 5G – versión 10

- Vuelven las flechas ▲ / ▼ en todos los campos numéricos editables, con clic y teclas ArrowUp/ArrowDown, manteniendo separadores de miles y decimales y respetando min/max y step. Incluye tablas, dinero MXN, población y porcentajes.
- Login, estilos de login, generador de credenciales, archivo systemd y configuración Nginx: sin cambios frente a v9. Misma lógica de `Auth`; `server.py` incorpora únicamente rutas de API y CSP `connect-src self`.
- `api.py`: cálculo en Python estándar compatible con los datos y las fórmulas JS; endpoints protegidos. Modelos `assets/model.js`, `assets/data.js`, `assets/controls.js` intactos.
- Se mantienen menú select de Modalidad, editor de porcentajes y tabla 10%–100%, sin los textos ni botón retirados en v9.
- No se cambia el puerto: el servidor sigue teniendo 8084 como predeterminado. No se crean contraseñas en el ZIP.
- Consulte `ACTUALIZACION_V10_RED_HAT_8084.md` antes de reemplazar archivos en producción.
