# Notas de integración

**Interfaz conservada:** proyecto original `crt-vmr-5g-publico`: logo, barra institucional, tipografía, gama de colores, pestañas horizontales, hero, pasos, formularios laterales y tarjetas de VMR. Se añadió una pestaña de descuentos usando las mismas clases y componentes; no se trasladó la interfaz nueva del segundo ZIP.

**Lógica incorporada:** módulos `model.js` y `data.js` del proyecto de despliegue actualizado; descuento y obligaciones por operador/modalidad, bases y parámetros editables, 27 resultados regionales, derechos anuales con reducción general, observaciones editables de benchmark, licitaciones, CSV, enlace compartible versión 4 y Excel descargable.

**Comportamiento actualizado:** los derechos de 800 MHz se ponderan con su cuota propia; la reducción general no aplica a 600 MHz; los descuentos por obligaciones nunca se restan automáticamente a la VMR.

**Comprobaciones ejecutadas:** 12 pruebas automatizadas de Node (`npm test`) satisfactorias, que comprenden la paridad VMR y regional y los 90 escenarios de descuentos contra Excel. Seis pruebas del servidor Python también correctas. Se verificaron los recursos y las secciones HTML del proyecto. La ejecución visual en Chromium no estuvo disponible en el entorno, por lo que se recomienda una pasada manual de escritorio y móvil antes de publicar en producción.


## Mejoras de interfaz · Versión 6
- Se sustituyó «Cómo se obtiene el descuento» por una tabla de comparación de **10% a 100%** en incrementos de 10%, calculada con el motor de descuentos para cada porcentaje. Se incluyen base anual, descuento anual y acumulado, montos, radiobases, localidades y población estimada por obligación. Los valores monetarios se muestran en millones de MXN y no en valor presente.
- Las opciones de descuento que superan el máximo permitido de cada operador se muestran como **No aplica** sin extrapolar resultados inexistentes.
- El usuario puede pulsar un porcentaje permitido de la tabla para aplicarlo a la calculadora.
- El selector «Modalidad» ahora es un control deslizante discreto con las modalidades predefinidas del modelo (no permite cambiar libremente las proporciones, para mantener la correspondencia con los cálculos validados de Excel). Para los tipos C/D/E solo muestra las modalidades permitidas. Al cambiar de operador se normaliza la modalidad y/o porcentaje al máximo permitido si hace falta.
- «Cobertura nueva» ahora se muestra como **Ampliación de cobertura**. Los cálculos de fondo permanecen intactos.

## Edición de modalidad (v7)

El desplegable «Modalidad de la obligación» conserva exclusivamente las opciones del Excel
permitidas para cada operador. «Editar valores de la modalidad» abre dos campos numéricos
para distribuir, a modo de simulación, el presupuesto entre ampliación de cobertura y
modernización; la suma se mantiene en 100 % y el otro campo se actualiza automáticamente.
Las distribuciones personalizadas se guardan por modalidad en el escenario y en el enlace
compartido; «Restablecer modalidad» recupera las proporciones oficiales. La edición no
modifica descuentos máximos, permisos por tipo de operador ni los valores fuente del Excel.
Los enlaces de escenario anteriores siguen siendo compatibles.

## v9
Login de v8 intacto, se mantienen cálculos, se añade formato de miles en los campos editables, se eliminan rótulos y texto indicados y botón de restablecimiento de modalidad.
