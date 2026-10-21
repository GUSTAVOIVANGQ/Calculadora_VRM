# CRT VMR 5G v11 — Rediseño de «Cómo se calcula», «Glosario y preguntas» y footer institucional

Archivos modificados: `index.html`, `assets/styles.css`, `assets/ui.js` (no se agregan archivos nuevos; `server.py` no cambia).

## Cómo se calcula
- Reducida a los valores clave: fórmula principal visual, 6 indicadores (tasas 10 % y 10.11 %, vigencia 20 años,
  factor INPC 1.0197, población de referencia 119.53 M, reducción LFD 12 %), fuente del precio por banda y
  descuento máximo por tipo de operador.
- El editor del benchmark internacional y la verificación contra Excel se conservan en dos desplegables cerrados.

## Glosario y preguntas
- Glosario en tarjetas (3 columnas en escritorio), preguntas frecuentes en acordeón con indicador +/−.
- Buscador que filtra términos y preguntas (sin acentos ni mayúsculas) y recuadro de contacto.

## Footer
- Footer institucional con las secciones de la Ventanilla Electrónica: Enlaces, ¿Qué es gob.mx?, Denuncia contra
  servidores públicos, Contacto (ayuda.ventanilla@crt.gob.mx) y barra inferior con © y versión.
- Sin imágenes externas (compatible con la CSP actual: img-src 'self').

## Actualización en el servidor (Red Hat 9, puerto 8084)
Respaldar y sustituir solo `index.html`, `assets/styles.css` y `assets/ui.js`; después Ctrl+Shift+R en el navegador.
No es necesario reiniciar el servicio.

## Impresión (todas las pestañas)
- Encabezado de impresión con logo, fecha y hora, título de la pestaña, estado (valores base / escenario modificado)
  y tabla con los parámetros del escenario (MHz y fuente por banda, tasas, INPC, vigencia, reducción; en descuentos:
  operador, modalidad, porcentaje y horizonte; en regiones: banda y tipo de valores).
- Pie en cada hoja: «CRT · Calculadora VMR 5G · Herramienta informativa» y «Página X de Y». Tamaño carta.
- Se ocultan botones, menús, buscador, desplegables cerrados y el footer web.
- Calculadora: 3 tarjetas por fila en una sola hoja. Regiones y descuentos: tablas ajustadas al ancho de la hoja
  (ya no se cortan ni se reduce toda la página); la tabla de descuentos inicia en hoja nueva.
- Glosario: las preguntas frecuentes se imprimen abiertas.

## Flechas numéricas
- Sustituidas por triángulos grises simples sin fondo ni bordes; se oscurecen al pasar el cursor.
  Misma funcionalidad y accesibilidad (etiquetas «Aumentar/Disminuir»).
