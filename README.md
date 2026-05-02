# VIH Base

Aplicacion Django para cargar imagenes dermatologicas, analizarlas con modelos de Roboflow y guardar el historial de resultados.

> Importante: esta herramienta es de apoyo educativo/informativo. No reemplaza la valoracion de un profesional de salud.

## Funcionalidades

- Consentimiento de terminos antes de usar la aplicacion.
- Carga de imagenes desde el navegador.
- Inferencia con dos modelos de Roboflow: lesion VIH y piel.
- Calculo de porcentaje de piel afectada y nivel de severidad configurable.
- Generacion de overlays visuales para VIH, piel y resultado combinado.
- Subida de imagen original y overlays a Supabase Storage.
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

DATABASE_URL=
DB_SSL_REQUIRE=True
DB_CONN_MAX_AGE=60

ROBOFLOW_API_KEY=
ROBOFLOW_API_URL=https://serverless.roboflow.com
ROBOFLOW_VIH_MODEL_ID=proyecto-de-vih/1
ROBOFLOW_SKIN_MODEL_ID=proyecto-de-vih/2

SUPABASE_URL=https://<tu-proyecto>.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_<tu_clave>
SUPABASE_BUCKET=VIH
SUPABASE_UPLOAD_TIMEOUT=30
MAX_UPLOAD_SIZE_MB=10
```

Los umbrales de clasificacion tambien se manejan por `.env`, para evitar cambiar codigo cuando se ajusta la sensibilidad del modelo.

### Supabase Storage

El proyecto usa Supabase para guardar:

- la imagen original enviada por el usuario;
- los overlays generados por el analisis;
- las URLs publicas que luego se guardan en la base de datos local.

Requisitos en Supabase:

1. Crear un bucket con el mismo nombre definido en `SUPABASE_BUCKET`.
2. Configurarlo como **publico** para que el navegador pueda cargar las imagenes con una URL directa.
3. Verificar que la `SUPABASE_PUBLISHABLE_KEY` tenga permiso de escritura sobre ese bucket.

Flujo de subida implementado en la app:

1. El usuario sube una imagen desde el formulario.
2. Django envia el archivo original a Supabase Storage.
3. Se ejecuta el analisis con Roboflow.
4. Los overlays generados se suben tambien a Supabase.
5. En la BD local se guardan la URL publica y la ruta interna de cada archivo.

Si Supabase responde con error, la vista muestra un mensaje de falló al analizar/subir la imagen y no deja un registro parcial.

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
- **En pruebas:** `python manage.py test` usa SQLite para no depender de la base remota aunque exista `DATABASE_URL`.
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

Comandos recomendados despues de cambios:

```powershell
python manage.py check
python manage.py test analisis_app
```

Si tambien cambiaste configuracion de base de datos o migraciones, ejecuta adicionalmente:

```powershell
python manage.py showmigrations
python manage.py migrate
```
