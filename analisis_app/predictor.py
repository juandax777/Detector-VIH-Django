import base64
import io
import logging
import os
import time
import uuid

import numpy as np
from django.conf import settings

try:
    from inference_sdk import InferenceHTTPClient
except ImportError:
    InferenceHTTPClient = None

from PIL import Image, ImageDraw


logger = logging.getLogger(__name__)


class PredictorError(Exception):
    """Error controlado para fallas de inferencia o parseo."""


def _debug_enabled():
    flag = (getattr(settings, 'ROBOFLOW_DEBUG_LOGS', '') or os.environ.get('ROBOFLOW_DEBUG_LOGS', '')).strip().lower()
    return flag in {'1', 'true', 'yes', 'on'}


def _debug(message):
    if _debug_enabled():
        print(f"[ROBOFLOW DEBUG] {message}", flush=True)


def decode_b64(mask_b64):
    """Decodifica una mascara base64 y retorna arreglo uint8 en escala de grises."""
    if not mask_b64:
        return None

    payload = mask_b64
    if ',' in payload and payload.strip().startswith('data:'):
        payload = payload.split(',', 1)[1]

    try:
        raw = base64.b64decode(payload)
        mask_img = Image.open(io.BytesIO(raw)).convert('L')
        return np.array(mask_img, dtype=np.uint8)
    except Exception:
        return None


def _mask_from_polygon(prediction, width, height):
    points = prediction.get('points') or prediction.get('polygon')
    if not points:
        return None

    try:
        poly = [(float(p['x']), float(p['y'])) for p in points if 'x' in p and 'y' in p]
        if len(poly) < 3:
            return None
        canvas = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(canvas)
        draw.polygon(poly, fill=255)
        return np.array(canvas, dtype=np.uint8) > 0
    except Exception:
        return None


def _resize_mask(mask_bool, target_size):
    if mask_bool is None:
        return None

    mask_img = Image.fromarray((mask_bool.astype(np.uint8) * 255), mode='L')
    if hasattr(Image, 'Resampling'):
        resample_nearest = Image.Resampling.NEAREST
    else:
        resample_nearest = getattr(Image, 'NEAREST', 0)
    mask_img = mask_img.resize(target_size, resample=resample_nearest)
    return np.array(mask_img) > 0


def _parse_predictions_dict(predictions_obj, target_size, target_class_id):
    seg = decode_b64(predictions_obj.get('segmentation_mask'))
    conf = decode_b64(predictions_obj.get('confidence_mask'))

    if seg is None:
        return None, 0.0, 'dict_without_segmentation_mask'

    seg_img = Image.fromarray(seg, mode='L')
    if seg_img.size != target_size:
        if hasattr(Image, 'Resampling'):
            resample_nearest = Image.Resampling.NEAREST
        else:
            resample_nearest = getattr(Image, 'NEAREST', 0)
        seg_img = seg_img.resize(target_size, resample=resample_nearest)

    seg_arr = np.array(seg_img, dtype=np.uint8)
    mask = seg_arr == int(target_class_id)

    # Fallback robusto: algunos modelos pueden no usar el mismo class id esperado.
    if not np.any(mask):
        mask = seg_arr > 0

    conf_mean = 0.0
    if conf is not None:
        conf_img = Image.fromarray(conf, mode='L')
        if conf_img.size != target_size:
            if hasattr(Image, 'Resampling'):
                resample_nearest = Image.Resampling.NEAREST
            else:
                resample_nearest = getattr(Image, 'NEAREST', 0)
            conf_img = conf_img.resize(target_size, resample=resample_nearest)

        conf_arr = np.array(conf_img, dtype=np.float32) / 255.0
        if np.any(mask):
            conf_mean = float(conf_arr[mask].mean())

    return mask, conf_mean, 'dict_segmentation_mask'


def get_masks(client, image_path, model_id, target_size, target_class_id):
    """Consulta Roboflow y retorna mascara combinada + confianza media + metadatos."""
    started = time.time()
    try:
        response = client.infer(image_path, model_id=model_id)
    except Exception as exc:
        raise PredictorError(f'Fallo al consultar Roboflow ({model_id}): {exc}') from exc

    elapsed_ms = int((time.time() - started) * 1000)
    predictions = response.get('predictions', []) if isinstance(response, dict) else []

    _debug(
        f"modelo={model_id} tiempo={elapsed_ms}ms tipo_predictions={type(predictions).__name__} "
        f"keys={list(response.keys()) if isinstance(response, dict) else 'n/a'}"
    )

    if isinstance(predictions, dict):
        mask, conf_mean, source = _parse_predictions_dict(predictions, target_size, target_class_id)
        if mask is None:
            return np.zeros((target_size[1], target_size[0]), dtype=bool), 0.0, {
                'model_id': model_id,
                'source': source,
                'elapsed_ms': elapsed_ms,
                'pixels': 0,
            }

        return mask, conf_mean, {
            'model_id': model_id,
            'source': source,
            'elapsed_ms': elapsed_ms,
            'pixels': int(np.count_nonzero(mask)),
        }

    if not isinstance(predictions, list):
        predictions = []

    masks = []
    confidences = []

    for pred in predictions:
        if not isinstance(pred, dict):
            continue

        mask_arr = decode_b64(
            pred.get('mask')
            or pred.get('segmentation_mask')
            or pred.get('mask_base64')
            or pred.get('binary_mask')
        )

        mask = None
        if mask_arr is not None:
            mask = mask_arr > 0

        if mask is None:
            mask = _mask_from_polygon(pred, target_size[0], target_size[1])

        if mask is None:
            continue

        resized = _resize_mask(mask, target_size)
        if resized is None:
            continue

        masks.append(resized)
        try:
            confidences.append(float(pred.get('confidence', 0.0)))
        except (TypeError, ValueError):
            confidences.append(0.0)

    if not masks:
        return np.zeros((target_size[1], target_size[0]), dtype=bool), 0.0, {
            'model_id': model_id,
            'source': 'list_predictions_empty',
            'elapsed_ms': elapsed_ms,
            'pixels': 0,
        }

    combined = np.logical_or.reduce(masks)
    conf_mean = float(np.mean(confidences)) if confidences else 0.0
    return combined, conf_mean, {
        'model_id': model_id,
        'source': 'list_predictions',
        'elapsed_ms': elapsed_ms,
        'pixels': int(np.count_nonzero(combined)),
    }


def overlay_single(image_rgb, mask, color=(255, 0, 0), alpha=0.45):
    output = image_rgb.astype(np.float32).copy()
    if mask is not None and np.any(mask):
        output[mask] = (1.0 - alpha) * output[mask] + alpha * np.array(color, dtype=np.float32)
    return Image.fromarray(np.clip(output, 0, 255).astype(np.uint8))


def overlay_two(image_rgb, vih_mask, skin_mask):
    output = image_rgb.astype(np.float32).copy()

    if skin_mask is not None and np.any(skin_mask):
        output[skin_mask] = (1.0 - 0.25) * output[skin_mask] + 0.25 * np.array([255, 165, 0], dtype=np.float32)

    if vih_mask is not None and np.any(vih_mask):
        output[vih_mask] = (1.0 - 0.55) * output[vih_mask] + 0.55 * np.array([255, 0, 0], dtype=np.float32)

    return Image.fromarray(np.clip(output, 0, 255).astype(np.uint8))


def _save_overlay(image_pil, source_image_path, suffix):
    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'overlays'), exist_ok=True)

    base_name = os.path.splitext(os.path.basename(source_image_path))[0]
    file_name = f"{base_name}_{suffix}_{uuid.uuid4().hex[:8]}.png"
    abs_path = os.path.join(settings.MEDIA_ROOT, 'overlays', file_name)
    image_pil.save(abs_path, format='PNG')

    media_url = settings.MEDIA_URL if settings.MEDIA_URL.endswith('/') else f"{settings.MEDIA_URL}/"
    return f"{media_url}overlays/{file_name}"


def _get_float_setting(name, default_value):
    raw = getattr(settings, name, default_value)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default_value)


def _get_int_setting(name, default_value):
    raw = getattr(settings, name, default_value)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return int(default_value)


def _aplica_umbral_alerta(vih_px, overlap_px, ratio):
    """Devuelve True cuando se supera el minimo para considerar alerta real."""
    min_vih_px = _get_int_setting('ROBOFLOW_MIN_VIH_PX', 120)
    min_overlap_px = _get_int_setting('ROBOFLOW_MIN_OVERLAP_PX', 40)
    min_ratio_alert = _get_float_setting('ROBOFLOW_MIN_RATIO_ALERT', 0.8)
    return (vih_px >= min_vih_px) and (overlap_px >= min_overlap_px) and (ratio >= min_ratio_alert)


def _clasificar_ratio(ratio, supera_umbral_alerta):
    fase_nula_max = _get_float_setting('ROBOFLOW_FASE_NULA_MAX', 1.0)
    fase_baja_max = _get_float_setting('ROBOFLOW_FASE_BAJA_MAX', 8.0)
    fase_mediana_max = _get_float_setting('ROBOFLOW_FASE_MEDIANA_MAX', 20.0)

    # Asegura orden creciente aun si alguien configura mal el .env
    fase_baja_max = max(fase_baja_max, fase_nula_max)
    fase_mediana_max = max(fase_mediana_max, fase_baja_max)

    if (ratio <= fase_nula_max) or (not supera_umbral_alerta):
        return 'Nula', 'Sin evidencia consistente de lesion VIH sobre piel (filtrado por umbral).'
    if ratio <= fase_baja_max:
        return 'Baja', 'Area VIH baja en proporcion al area de piel detectada.'
    if ratio <= fase_mediana_max:
        return 'Mediana', 'Area VIH mediana respecto al area de piel detectada.'
    return 'Alta', 'Area VIH alta respecto al area de piel detectada.'


def analizar_imagen_con_roboflow(image_path):
    if InferenceHTTPClient is None:
        raise PredictorError('Falta la dependencia inference-sdk. Instala requirements.txt y vuelve a intentar.')

    api_key = (getattr(settings, 'ROBOFLOW_API_KEY', '') or '').strip()
    if not api_key:
        raise PredictorError('Falta configurar ROBOFLOW_API_KEY en variables de entorno o en .env.')

    api_url = (getattr(settings, 'ROBOFLOW_API_URL', 'https://serverless.roboflow.com') or 'https://serverless.roboflow.com').strip()
    vih_model_id = (getattr(settings, 'ROBOFLOW_VIH_MODEL_ID', 'proyecto-de-vih/1') or 'proyecto-de-vih/1').strip()
    skin_model_id = (getattr(settings, 'ROBOFLOW_SKIN_MODEL_ID', 'proyecto-de-vih/2') or 'proyecto-de-vih/2').strip()
    vih_class_id = int(getattr(settings, 'ROBOFLOW_VIH_CLASS_ID', os.environ.get('ROBOFLOW_VIH_CLASS_ID', 1)))
    skin_class_id = int(getattr(settings, 'ROBOFLOW_SKIN_CLASS_ID', os.environ.get('ROBOFLOW_SKIN_CLASS_ID', 2)))

    if not os.path.exists(image_path):
        raise PredictorError('La imagen no existe o no es accesible para analisis.')

    try:
        base_img = Image.open(image_path).convert('RGB')
    except Exception as exc:
        raise PredictorError(f'No se pudo abrir la imagen para analisis: {exc}') from exc

    base_np = np.array(base_img)
    width, height = base_img.size

    _debug(f"inicio inferencia imagen={image_path} size={width}x{height} vih={vih_model_id} skin={skin_model_id}")
    client = InferenceHTTPClient(api_url=api_url, api_key=api_key)

    vih_mask, vih_conf_mean, vih_meta = get_masks(client, image_path, vih_model_id, (width, height), vih_class_id)
    skin_mask, skin_conf_mean, skin_meta = get_masks(client, image_path, skin_model_id, (width, height), skin_class_id)

    vih_px = int(np.count_nonzero(vih_mask))
    skin_px = int(np.count_nonzero(skin_mask))
    overlap_px = int(np.count_nonzero(np.logical_and(vih_mask, skin_mask)))

    if skin_px > 0 and vih_px > 0:
        ratio = float((vih_px / skin_px) * 100.0)
    else:
        ratio = 0.0

    supera_umbral_alerta = _aplica_umbral_alerta(vih_px, overlap_px, ratio)

    _debug(
        f"resultado vih_px={vih_px} skin_px={skin_px} overlap_px={overlap_px} ratio={ratio:.2f}% "
        f"supera_umbral_alerta={supera_umbral_alerta} vih_meta={vih_meta} skin_meta={skin_meta}"
    )
    logger.warning(
        "Roboflow resumen -> vih_px=%s skin_px=%s overlap_px=%s ratio=%.2f%% vih_source=%s skin_source=%s",
        vih_px,
        skin_px,
        overlap_px,
        ratio,
        vih_meta.get('source'),
        skin_meta.get('source'),
    )

    nivel, descripcion = _clasificar_ratio(ratio, supera_umbral_alerta)

    overlay_vih_path = _save_overlay(overlay_single(base_np, vih_mask, color=(255, 0, 0), alpha=0.55), image_path, 'vih')
    overlay_skin_path = _save_overlay(overlay_single(base_np, skin_mask, color=(255, 165, 0), alpha=0.35), image_path, 'skin')
    overlay_combined_path = _save_overlay(overlay_two(base_np, vih_mask, skin_mask), image_path, 'combined')

    if supera_umbral_alerta:
        diagnostico = 'Positivo - Posible lesion asociada al VIH detectada'
        confianza = round(float(vih_conf_mean) * 100.0, 2)
    else:
        diagnostico = 'Negativo - Hallazgo por debajo de umbral clinico configurable'
        # Evita mostrar una confianza alta cuando el hallazgo no supera filtros minimos.
        confianza = 0.0

    confianza_modelo_bruta = round(float(vih_conf_mean) * 100.0, 2)
    ratio_round = round(ratio, 2)

    return {
        'vih_px': vih_px,
        'skin_px': skin_px,
        'overlap_px': overlap_px,
        'ratio': ratio_round,
        'vih_conf_mean': round(float(vih_conf_mean), 4),
        'skin_conf_mean': round(float(skin_conf_mean), 4),
        'nivel': nivel,
        'descripcion': descripcion,
        'overlay_vih_path': overlay_vih_path,
        'overlay_skin_path': overlay_skin_path,
        'overlay_combined_path': overlay_combined_path,
        'debug': {
            'vih': vih_meta,
            'skin': skin_meta,
            'supera_umbral_alerta': supera_umbral_alerta,
            'min_vih_px': _get_int_setting('ROBOFLOW_MIN_VIH_PX', 120),
            'min_overlap_px': _get_int_setting('ROBOFLOW_MIN_OVERLAP_PX', 40),
            'min_ratio_alert': _get_float_setting('ROBOFLOW_MIN_RATIO_ALERT', 0.8),
            'fase_nula_max': _get_float_setting('ROBOFLOW_FASE_NULA_MAX', 1.0),
            'fase_baja_max': _get_float_setting('ROBOFLOW_FASE_BAJA_MAX', 8.0),
            'fase_mediana_max': _get_float_setting('ROBOFLOW_FASE_MEDIANA_MAX', 20.0),
        },
        'diagnostico': diagnostico,
        'confianza': confianza,
        'confianza_modelo_bruta': confianza_modelo_bruta,
        'valor_prediccion': round(ratio_round / 100.0, 4),
        'todas_las_predicciones': [
            {'clase': 'Area VIH sobre piel', 'probabilidad': ratio_round},
            {'clase': 'Confianza media VIH (bruta)', 'probabilidad': confianza_modelo_bruta},
            {'clase': 'Confianza media piel', 'probabilidad': round(float(skin_conf_mean) * 100.0, 2)},
        ],
    }


def predecir(imagen_path):
    return analizar_imagen_con_roboflow(imagen_path)
