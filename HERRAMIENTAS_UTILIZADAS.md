# Inventario tecnológico — CRT VMR 5G React

| Herramienta | Rol | Dónde se usa |
|---|---|---|
| Red Hat Enterprise Linux 9.7 | Sistema operativo del servidor | `srvmbcudaqa01` |
| systemd / systemctl / journalctl | Mantener proceso activo sin SSH y arranque automático | Servicio `crt-vmr-5g.service` |
| Python 3 (biblioteca estándar) | Servidor HTTP(S), autenticación, API y cálculo | Red Hat |
| SQLite 3 | Usuarios creados y persistencia | `/var/lib/crt-vmr-5g/` |
| React 19 + React DOM | Componentes visuales y sesión | Navegador |
| Vite 7 + plugin React | Compilación optimizada de React | CI o estación de build |
| Node.js 22.12+ / npm | Resolver dependencias y ejecutar compilación/pruebas | GitLab Runner o estación de build |
| JavaScript ES modules | Motor matemático y controles conservados | Navegador |
| Excel XLSX | Fuente de referencia de supuestos | Repositorio `archivos/` |
| Git y GitLab | Versionado, CI, merge requests y auditoría | Plataforma corporativa |
| DNS / PKI institucional | FQDN y certificado TLS (no basta DNS sin TLS) | Equipo de infraestructura |
| OpenSSL/TLS de Python (`ssl`) | HTTPS directo en 8084 sin Nginx | Red Hat |
| curl | Verificar rutas y cabeceras de servicio | Red Hat |
| firewall/SELinux (según política) | Control de publicación del puerto y permisos | Red Hat |

**No se utiliza Docker, Nginx, PostgreSQL, Redis ni Flask en este proyecto.** Las pruebas Python usan `unittest`; las de JS, `node --test`.
