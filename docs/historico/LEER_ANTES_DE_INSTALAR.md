# PROYECTO EN CARPETA RENOMBRADA (RHEL 9.7 · puerto 8084)

Este paquete se extrae en **portal_crt_vmr5g_v11_8084/**, sin tocar
Calculadora_VMR/crt-vmr-5g-app ni ninguna carpeta crt-vmr-5g existente.

Antes de realizar cambios en el servicio consulte:
**GUIA_PORTAL_CRT_VMR5G_V11_RHEL9_8084_PERSISTENTE.md**

Para mantener el puerto 8084 y la sesión SSH independiente, use la unidad
**crt-vmr-5g.service** YA instalada, agregando solamente el override
**systemd/95-portal-crt-vmr5g-v11-8084.conf**.

ADVERTENCIA: Las plantillas antiguas *.service dentro del paquete no están
adaptadas a la ruta de su servidor. NO las instale.
El login v11 deriva de la v10 entregada previamente: compare el login
actual de su servidor antes de cambiar WorkingDirectory.
