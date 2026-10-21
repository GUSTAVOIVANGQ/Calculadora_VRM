# Endpoints CRT VMR 5G — versión React

**Origen**: mismo dominio y puerto que el frontend. No se habilita CORS por defecto. API JSON con cookie de sesión.

| Método | Ruta | Permiso | Respuesta / finalidad |
|---|---|---|---|
| GET | `/healthz` | Público | `ok` para systemd/monitoreo |
| GET | `/api/v1/health` | Público | Estado API sin datos sensibles |
| GET | `/api/v1/readiness` | Público | `{ready: true/false}` según disponibilidad de compilación React |
| GET | `/login` | Público | Pantalla HTML de acceso CRT |
| POST | `/login` | Público + token CSRF formulario | Autenticación y cookie |
| GET | `/crear-cuenta` o `/register` | Público | Formulario de registro con invitación |
| POST | `/crear-cuenta` o `/register` | Público + token CSRF formulario | Crear cuenta si hay invitación |
| POST | `/logout` | Sesión + token CSRF formulario | Destruye cookie y sesión |
| GET | `/api/v1/auth/status` | Público | `{authenticated, registrationEnabled}` |
| GET | `/api/v1/auth/csrf` | Público | Token de un solo uso para login/registro JSON |
| GET | `/api/v1/auth/session` | Autenticado | `{authenticated:true, csrf:"..."}` para logout y cálculo; `401` sin sesión |
| POST | `/api/v1/auth/login` | Token CSRF JSON | `{csrf,username,password}` |
| POST | `/api/v1/auth/register` | Token CSRF JSON | `{csrf,username,password,confirmPassword,inviteCode}` |
| GET | `/api/v1/metadata` | Autenticado | Operadores, bandas, modalidades y límites |
| GET | `/api/v1/defaults` | Autenticado | Parámetros iniciales de cálculo |
| POST | `/api/v1/calculate` | Sesión + `X-VMR-CSRF` | VMR + descuentos + regional |
| POST | `/api/v1/calculate/vmr` | Sesión + `X-VMR-CSRF` | VMR por banda |
| POST | `/api/v1/calculate/discounts` | Sesión + `X-VMR-CSRF` | Descuentos, tabla y obligaciones |

**Ejemplo (tras iniciar sesión, con cookie y token de la sesión):**

```bash
# Consultar la sesión ya autenticada y preservar cookie en cookie.txt en el equipo autorizado
curl -b cookie.txt https://DOMINIO:8084/api/v1/auth/session

curl -b cookie.txt -X POST 'https://DOMINIO:8084/api/v1/calculate' \
  -H 'Content-Type: application/json' \
  -H 'X-VMR-CSRF: TOKEN_ENTREGADO_POR_SESSION' \
  -d '{"scenario":{"spectrum":[40,20,20]}}'
```

**HTTP 401**: falta sesión; **403**: CSRF / origen no permitido; **413**: tamaño excesivo; **415**: tipo incorrecto; **422**: escenario inválido. No enviar tokens reales al repositorio ni registros compartidos.
