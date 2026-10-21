# CRT VMR 5G · Actualización de interfaz 9

- Se mantiene tal cual el login implementado en la entrega v8: hashes SHA-256 idénticos de servidor, página de login, estilos de login, generador de credenciales y archivos systemd/proxy. **No se reemplaza ni restaura el login de un servidor al que no tenemos acceso.**
- Los ZIP originales proporcionados no traían login integrado; si tu Red Hat cuenta con uno distinto, conserva su proceso/archivos y aplica solo los cambios de interfaz bajo su protección.
- Los campos de moneda MXN, parámetros monetarios, porcentajes, población y referencias usan coma de miles y punto decimal, también durante la edición.
- No se cambió el motor de VMR, cálculos de descuentos, tabla, ni validaciones numéricas; solo cómo se muestran y capturan las cifras.
- Se ocultaron las marcas «avanzado», la explicación larga del editor, el texto sobre proporciones base y el botón «Restablecer modalidad». El desplegable de modalidad se mantiene.
- Consulta `ACTUALIZAR_SIN_CAMBIAR_LOGIN_8084.md` para actualizar con respaldo, sin tocar credenciales ni servicio.
