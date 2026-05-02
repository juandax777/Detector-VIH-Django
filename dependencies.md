# Dependencias del proyecto

Este repo usa dos archivos distintos para dependencias:

- `requirements.txt`: dependencias mínimas y directas para ejecutar la app.
- `dependencies-installed.txt`: lista completa de paquetes instalados en el entorno local al momento de preparar el repo.

## Dependencias mínimas requeridas

| Paquete | Motivo |
| --- | --- |
| `Django` | Framework web principal del proyecto. |
| `Pillow` | Manejo de imágenes en `ImageField` y procesamiento de overlays. |
| `numpy` | Operaciones sobre máscaras y arreglos de imagen. |
| `inference-sdk` | Cliente para consultar Roboflow desde `analisis_app/predictor.py`. |

## Paquetes instalados localmente que no son obligatorios para correr la app

Estos paquetes aparecen en el entorno local, pero no son necesarios para ejecutar la aplicación base:

- `tensorflow`
- `opencv-python`
- `matplotlib`
- `scipy`
- `supervision`
- `coverage`
- `python-dotenv`
- `requests`

## Recomendación para publicar el repo

Para que el proyecto sea reproducible en otra máquina:

1. Instala con `requirements.txt`.
2. Copia `.env.example` a `.env`.
3. Ejecuta migraciones con `python manage.py migrate`.
4. Usa `dependencies-installed.txt` solo como referencia o para recrear exactamente este entorno.

