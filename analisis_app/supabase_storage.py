import mimetypes
from datetime import datetime
from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import uuid4

import requests
from django.conf import settings


class SupabaseStorageError(Exception):
    """Error controlado para fallas de subida a Supabase Storage."""


def _require_config():
    if not settings.SUPABASE_URL or not settings.SUPABASE_PUBLISHABLE_KEY:
        raise SupabaseStorageError('Falta configurar SUPABASE_URL o SUPABASE_PUBLISHABLE_KEY.')
    if not settings.SUPABASE_BUCKET:
        raise SupabaseStorageError('Falta configurar SUPABASE_BUCKET.')


def build_storage_path(folder, original_name, extension=None):
    now = datetime.utcnow()
    suffix = extension or PurePosixPath(original_name or '').suffix.lower()
    if not suffix:
        suffix = '.bin'
    suffix = suffix if suffix.startswith('.') else f'.{suffix}'
    return f"{folder}/{now:%Y/%m}/{uuid4().hex}{suffix}"


def public_url(path):
    _require_config()
    quoted_path = quote(path.lstrip('/'), safe='/')
    bucket = quote(settings.SUPABASE_BUCKET, safe='')
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{quoted_path}"


def upload_bytes(path, content, content_type='application/octet-stream'):
    _require_config()
    bucket = quote(settings.SUPABASE_BUCKET, safe='')
    object_path = quote(path.lstrip('/'), safe='/')
    url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{object_path}"
    headers = {
        'apikey': settings.SUPABASE_PUBLISHABLE_KEY,
        'Authorization': f"Bearer {settings.SUPABASE_PUBLISHABLE_KEY}",
        'Content-Type': content_type or 'application/octet-stream',
        'Cache-Control': '3600',
        'x-upsert': 'false',
    }

    try:
        response = requests.post(
            url,
            data=content,
            headers=headers,
            timeout=settings.SUPABASE_UPLOAD_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise SupabaseStorageError(f'No se pudo conectar con Supabase Storage: {exc}') from exc

    if response.status_code not in {200, 201}:
        detail = response.text[:300] if response.text else response.reason
        raise SupabaseStorageError(f'Supabase rechazo la subida ({response.status_code}): {detail}')

    return {
        'path': path,
        'url': public_url(path),
    }


def upload_django_file(file_obj, folder='originales'):
    content_type = getattr(file_obj, 'content_type', None)
    if not content_type:
        content_type = mimetypes.guess_type(getattr(file_obj, 'name', ''))[0] or 'application/octet-stream'
    path = build_storage_path(folder, getattr(file_obj, 'name', 'upload'), None)
    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)
    content = file_obj.read()
    return upload_bytes(path, content, content_type)

