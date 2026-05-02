# VIH Base

Aplicacion Django para cargar imagenes dermatologicas, analizarlas con modelos de Roboflow y guardar el historial de resultados.

> Importante: esta herramienta es de apoyo educativo/informativo. No reemplaza la valoracion de un profesional de salud.

## Funcionalidades

- Consentimiento de terminos antes de usar la aplicacion.
- Carga de imagenes desde el navegador.
- Inferencia con dos modelos de Roboflow: lesion VIH y piel.
- Calculo de porcentaje de piel afectada y nivel de severidad configurable.
- Generacion de overlays visuales para VIH, piel y resultado combinado.
- Historial de analisis en base de datos.
- Administracion de resultados desde Django Admin.

## Estructura principal

```text
VIH_base/
|-- analisis_app/              # App Django principal
|   |-- admin.py               # Registro del modelo en Django Admin
|   |-- forms.py               # Formulario de carga de imagen
|   |-- models.py              # Modelo ImagenAnalisis
|   |-- predictor.py           # Logica de inferencia con Roboflow
|   |-- urls.py                # Rutas de la app
|   `-- views.py               # Vistas y flujo de consentimiento
|-- modelo_entrenado/          # Modelos locales, si se usan
|-- templates/analisis/        # Plantillas HTML
|-- VIH_base/
|   |-- settings.py            # Configuracion Django y variables de entorno
|   |-- urls.py                # URLs globales
|   |-- asgi.py
|   `-- wsgi.py
|-- .env.example               # Plantilla sin secretos
|-- .gitignore                 # Archivos que no deben versionarse
|-- manage.py
|-- requirements.txt
`-- README.md
```

## Configuracion de entorno

1. Copia el ejemplo:

```powershell
Copy-Item .env.example .env
```

2. Edita `.env` y agrega tus valores reales.

El archivo `.env` es privado. No debe subirse al repositorio porque contiene datos sensibles como `ROBOFLOW_API_KEY` y `SECRET_KEY`.

Variables principales:

```dotenv
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

ROBOFLOW_API_KEY=
ROBOFLOW_API_URL=https://serverless.roboflow.com
ROBOFLOW_VIH_MODEL_ID=proyecto-de-vih/1
ROBOFLOW_SKIN_MODEL_ID=proyecto-de-vih/2
```

Los umbrales de clasificacion tambien se manejan por `.env`, para evitar cambiar codigo cuando se ajusta la sensibilidad del modelo.

## Instalacion local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Si quieres ver un desglose más completo de paquetes, revisa:

- `dependencies.md` para entender cuáles son obligatorios y cuáles son opcionales.
- `dependencies-installed.txt` para ver la lista exacta de paquetes instalados en este entorno.

Abre la aplicacion en:

```text
http://localhost:8000
```

## Base de datos local (SQLite)

Este proyecto usa SQLite como base de datos local. En Django, esto significa que toda la base se guarda en un solo archivo: `db.sqlite3`.

- **Para que sirve en este proyecto:** guardar el historial de analisis, usuarios del admin, sesiones y control de migraciones.
- **Donde se configura:** en `VIH_base/settings.py`, dentro de `DATABASES`, con `ENGINE = django.db.backends.sqlite3` y `NAME = BASE_DIR / 'db.sqlite3'`.
- **Cuando se crea:** al ejecutar `python manage.py migrate` por primera vez.
- **Que tablas tendras (ejemplos):** `analisis_app_imagenanalisis`, `auth_user`, `django_migrations`, `django_session`, `django_admin_log`.
- **Se sube a Git?:** no. `db.sqlite3` contiene datos locales y normalmente se ignora en `.gitignore`.

### Comandos utiles de base de datos

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
python manage.py dbshell
python manage.py shell
```

Inspeccionar tablas desde `python manage.py shell`:

```python
from django.db import connection
print(connection.introspection.table_names())
```

Reset local rapido (solo desarrollo, elimina datos):

```powershell
Remove-Item .\db.sqlite3
python manage.py migrate
```

## Rutas

| Ruta | Uso |
| --- | --- |
| `/` | Cargar imagen |
| `/terminos/` | Terminos y consentimiento |
| `/aceptar-terminos/` | Procesa aceptacion |
| `/historial/` | Historial de analisis |
| `/admin/` | Administracion Django |

## Seguridad y privacidad

- `.env` queda ignorado por Git.
- `.env.example` no debe contener claves reales.
- `SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS` se leen desde variables de entorno.
- Las imagenes subidas quedan en `media/`, tambien ignorado por Git.
- `db.sqlite3` queda ignorado porque contiene datos locales.
- Si una API key ya estuvo en un archivo compartido, revocala y genera una nueva desde Roboflow.

## Verificacion

Comando recomendado despues de cambios:

```powershell
python manage.py check
```
