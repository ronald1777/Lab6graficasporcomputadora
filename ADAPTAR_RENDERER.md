# Integración con los recursos de clase

La consigna exige el renderer CPU y la esfera proporcionados en clase. No se adjuntaron esos archivos: el proyecto autónomo es una referencia funcional, no una integración verificada contra una API desconocida.

## Renderer de clase en Python

Conserva su carga de esfera, transformaciones, rasterización, z-buffer y presentación. Usa exactamente la misma geometría para los tres shaders. Copia/adapta `src/noise.py` y `src/shaders.py`.

El contrato de los shaders es:

```python
colors = shader(p, view, light, time, params=None)
```

- `p`: posiciones locales normalizadas, arreglo NumPy `(N, 3)`.
- `view`: vector unitario desde la superficie hacia la cámara ortográfica, `(3,)`.
- `light`: vector unitario desde la superficie hacia la luz direccional, `(3,)`.
- `time`: segundos; no modifica la geometría.
- Salida: colores RGB flotantes `(N, 3)`; recorta entre 0 y 1 antes de convertir al formato del renderer.

Posición, vista y luz deben estar en el mismo espacio local. Normalizar las coordenadas de muestreo no modifica vértices. Para un renderer que llama un fragmento a la vez, una adaptación posible es:

```python
import numpy as np
from src.noise import normalize
from src.shaders import SHADERS

def fragment_adapter(local_position, local_view, local_light, seconds, selected):
    p = normalize(np.asarray(local_position, dtype=float).reshape(1, 3))
    view = normalize(np.asarray(local_view, dtype=float))
    light = normalize(np.asarray(local_light, dtype=float))
    rgb = SHADERS[selected](p, view, light, seconds)[0]
    return tuple(np.uint8(np.clip(rgb, 0, 1) * 255 + .5))
```

`selected` es `star`, `rock` o `gas`. Adapta los nombres y el retorno a la API real. Si puedes procesar bloques de fragmentos, conserva la vectorización para mejorar el rendimiento.

Los shaders ya calculan su iluminación: no multipliques otra vez por la intensidad difusa sin revisar el resultado. La estrella es emisiva. Los brillos, el bump y las sombras requieren dirección de luz; una intensidad escalar no basta para reconstruirla.

Para perspectiva, calcula una vista por fragmento y adapta los productos punto `p @ view` a sumas elemento a elemento. El vector mitad también debe admitir esa vista variable. No afirmes haber integrado esta variante hasta comprobarla visualmente.

## Renderer en otro lenguaje

Porta las operaciones de `noise.py` y `shaders.py`, conservando espacios de coordenadas y parámetros. Este paquete no incluye un puerto a un lenguaje que no se especificó. Usa las capturas como referencia para comparar.

## Probar un OBJ oficial en el respaldo

```bash
python main.py --obj ruta/a/esfera_de_clase.obj --body rock
```

El lector admite polígonos triangulables, índices positivos/negativos y campos `v/vt/vn`. El respaldo requiere una esfera centrada de radio 1 y usa normales radiales. Para una esfera escalada/descentrada u otro formato, adapta carga, modelo/cámara y muestreo sin desplazar vértices para añadir detalles. Ejecutar este comando no sustituye integrar el renderer oficial.

## Verificación final

- Seleccionar cada shader conserva los vértices y caras originales.
- Con cámara fija, cambia el material de Helios y se desplazan las nubes de Nerida respecto de los continentes.
- Con tiempo pausado y luz móvil, cambian reflejos del agua, luces de noche y dirección de las sombras.
- Desactivar bump cambia la iluminación del terreno sin cambiar silueta.
- `vortex_strength = 0` elimina la torsión de bandas alrededor de la tormenta.
- Regenera evidencias con la versión integrada y actualiza rutas, funciones y notas pendientes del README.
