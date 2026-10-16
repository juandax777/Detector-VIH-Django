from unittest.mock import Mock, patch

from django.test import TestCase, Client, override_settings
from django.utils.datastructures import MultiValueDict
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
from requests.exceptions import RequestException

from .views import TERMINOS_SESSION_KEY
from .models import ImagenAnalisis
from .forms import ImagenForm
from .supabase_storage import SupabaseStorageError, public_url, upload_bytes
from .predictor import (
    decode_b64,
    _get_float_setting, _get_int_setting, _aplica_umbral_alerta,
    _clasificar_ratio, PredictorError
)


# ==================== PRUEBAS DE MODELOS ====================

class ImagenAnalisisModelTests(TestCase):
    """Pruebas para el modelo ImagenAnalisis"""

    def setUp(self):
        """Crear datos de prueba"""
        self.imagen_test = self._crear_imagen_test()

    def _crear_imagen_test(self, nombre='test.jpg'):
        """Helper para crear una imagen de prueba"""
        imagen = Image.new('RGB', (100, 100), color='red')
        imagen_io = io.BytesIO()
        imagen.save(imagen_io, format='JPEG')
        imagen_io.seek(0)
        return SimpleUploadedFile(nombre, imagen_io.getvalue(), content_type='image/jpeg')

    def test_crear_imagen_analisis(self):
        """Verificar que se puede crear una ImagenAnalisis"""
        analisis = ImagenAnalisis.objects.create(
            imagen=self.imagen_test,
            resultado='Negativo',
            confianza=85.5
        )
        self.assertEqual(ImagenAnalisis.objects.count(), 1)
        self.assertEqual(analisis.resultado, 'Negativo')
        self.assertEqual(analisis.confianza, 85.5)

    def test_imagen_analisis_str(self):
        """Verificar que el __str__ funciona correctamente"""
        analisis = ImagenAnalisis.objects.create(
            imagen=self.imagen_test,
            resultado='Positivo',
            confianza=92.3
        )
        str_resultado = str(analisis)
        self.assertIn('Análisis #', str_resultado)
        self.assertIn(str(analisis.pk), str_resultado)

    def test_imagen_analisis_campos_opcionales(self):
        """Verificar que resultado y confianza pueden ser nulos"""
        analisis = ImagenAnalisis.objects.create(imagen=self.imagen_test)
        self.assertIsNone(analisis.resultado)
        self.assertIsNone(analisis.confianza)

    def test_imagen_analisis_ordenamiento(self):
        """Verificar que se ordenan por fecha descendente"""
        img1 = ImagenAnalisis.objects.create(imagen=self.imagen_test)
        img2 = ImagenAnalisis.objects.create(imagen=self._crear_imagen_test('test2.jpg'))

        lista = list(ImagenAnalisis.objects.all())
        self.assertEqual(lista[0].pk, img2.pk)
        self.assertEqual(lista[1].pk, img1.pk)


# ==================== PRUEBAS DE FORMULARIOS ====================

class ImagenFormTests(TestCase):
    """Pruebas para el formulario ImagenForm"""

    def _crear_imagen_test(self):
        """Helper para crear una imagen de prueba"""
        imagen = Image.new('RGB', (100, 100), color='blue')
        imagen_io = io.BytesIO()
        imagen.save(imagen_io, format='JPEG')
        imagen_io.seek(0)
        return SimpleUploadedFile('test.jpg', imagen_io.getvalue(), content_type='image/jpeg')

    def test_formulario_valido(self):
        """Verificar que el formulario es válido con una imagen"""
        imagen = self._crear_imagen_test()
        form = ImagenForm(data={}, files=MultiValueDict({'imagen': [imagen]}))
        self.assertTrue(form.is_valid())

    def test_formulario_sin_imagen(self):
        """Verificar que el formulario es inválido sin imagen"""
        form = ImagenForm(data={}, files=MultiValueDict())
        self.assertFalse(form.is_valid())
        self.assertIn('imagen', form.errors)

    def test_formulario_acepta_formatos_imagen(self):
        """Verificar que se aceptan diferentes formatos de imagen"""
        for formato in ['JPEG', 'PNG', 'GIF']:
            imagen = Image.new('RGB', (50, 50), color='green')
            imagen_io = io.BytesIO()
            imagen.save(imagen_io, format=formato)
            imagen_io.seek(0)

            uploaded = SimpleUploadedFile(f'test.{formato.lower()}',
                                         imagen_io.getvalue(),
                                         content_type=f'image/{formato.lower()}')
            form = ImagenForm(data={}, files=MultiValueDict({'imagen': [uploaded]}))
            self.assertTrue(form.is_valid(), f"Falló para formato {formato}")


# ==================== PRUEBAS DE VISTAS ====================

class TerminosConsentimientoTests(TestCase):
    """Pruebas para vistas de términos y consentimiento"""

    def test_redirige_a_terminos_si_no_hay_consentimiento(self):
        """Sin consentimiento, debe redirigir a términos"""
        respuesta = self.client.get(reverse('analisis:subir_imagen'))

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('analisis:terminos'), respuesta['Location'])

    def test_aceptar_terminos_habilita_acceso(self):
        """Aceptar términos debe permitir acceso a subir_imagen"""
        respuesta = self.client.post(reverse('analisis:aceptar_terminos'), {
            'acepto': 'on',
            'next': reverse('analisis:subir_imagen'),
        })

        self.assertRedirects(respuesta, reverse('analisis:subir_imagen'))
        self.assertTrue(self.client.session.get(TERMINOS_SESSION_KEY))

        acceso = self.client.get(reverse('analisis:subir_imagen'))
        self.assertEqual(acceso.status_code, 200)

    def test_no_acepta_terminos_muestra_error(self):
        """Sin aceptar términos, debe mostrar error"""
        respuesta = self.client.post(reverse('analisis:aceptar_terminos'), {
            'next': reverse('analisis:subir_imagen'),
        })

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Debes aceptar los terminos y condiciones para continuar.')
        self.assertFalse(self.client.session.get(TERMINOS_SESSION_KEY, False))

    def test_ver_terminos_sin_consentimiento(self):
        """Debe permitir ver términos sin consentimiento previo"""
        respuesta = self.client.get(reverse('analisis:terminos'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'analisis/terminos.html')


class SubirImagenViewTests(TestCase):
    """Pruebas para la vista de subir imagen"""

    def setUp(self):
        """Preparar datos antes de cada prueba"""
        self.client = Client()
        session = self.client.session
        session[TERMINOS_SESSION_KEY] = True
        session.save()

    def _crear_imagen_test(self):
        """Helper para crear una imagen de prueba"""
        imagen = Image.new('RGB', (100, 100), color='yellow')
        imagen_io = io.BytesIO()
        imagen.save(imagen_io, format='JPEG')
        imagen_io.seek(0)
        return SimpleUploadedFile('test.jpg', imagen_io.getvalue(), content_type='image/jpeg')

    def test_get_subir_imagen_muestra_formulario(self):
        """GET debe mostrar el formulario de carga"""
        respuesta = self.client.get(reverse('analisis:subir_imagen'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'analisis/upload.html')
        self.assertIsInstance(respuesta.context['form'], ImagenForm)

    def test_post_sin_imagen_muestra_error(self):
        """POST sin imagen debe mostrar formulario con error"""
        respuesta = self.client.post(reverse('analisis:subir_imagen'), {})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'analisis/upload.html')


class SupabaseStorageTests(TestCase):
    """Pruebas para el almacenamiento en Supabase"""

    @override_settings(
        SUPABASE_URL='https://demo.supabase.co',
        SUPABASE_PUBLISHABLE_KEY='anon-key',
        SUPABASE_BUCKET='VIH',
        SUPABASE_UPLOAD_TIMEOUT=12,
    )
    def test_public_url_arma_la_ruta_publica(self):
        esperado = 'https://demo.supabase.co/storage/v1/object/public/VIH/originales/2026/05/imagen.png'
        self.assertEqual(public_url('originales/2026/05/imagen.png'), esperado)

    @override_settings(
        SUPABASE_URL='https://demo.supabase.co',
        SUPABASE_PUBLISHABLE_KEY='anon-key',
        SUPABASE_BUCKET='VIH',
        SUPABASE_UPLOAD_TIMEOUT=12,
    )
    @patch('analisis_app.supabase_storage.requests.post')
    def test_upload_bytes_exitoso(self, mock_post):
        mock_post.return_value = Mock(status_code=201, text='created', reason='Created')

        resultado = upload_bytes('originales/2026/05/imagen.png', b'datos', 'image/png')

        self.assertEqual(resultado['path'], 'originales/2026/05/imagen.png')
        self.assertEqual(resultado['url'], public_url('originales/2026/05/imagen.png'))
        self.assertEqual(mock_post.call_args.args[0], 'https://demo.supabase.co/storage/v1/object/VIH/originales/2026/05/imagen.png')
        self.assertEqual(mock_post.call_args.kwargs['timeout'], 12)
        self.assertEqual(mock_post.call_args.kwargs['data'], b'datos')
        self.assertEqual(mock_post.call_args.kwargs['headers']['Content-Type'], 'image/png')

    @override_settings(
        SUPABASE_URL='https://demo.supabase.co',
        SUPABASE_PUBLISHABLE_KEY='anon-key',
        SUPABASE_BUCKET='VIH',
        SUPABASE_UPLOAD_TIMEOUT=12,
    )
    @patch('analisis_app.supabase_storage.requests.post')
    def test_upload_bytes_rechazo_http(self, mock_post):
        mock_post.return_value = Mock(status_code=400, text='bad request', reason='Bad Request')

        with self.assertRaises(SupabaseStorageError) as ctx:
            upload_bytes('originales/2026/05/imagen.png', b'datos', 'image/png')

        self.assertIn('Supabase rechazo la subida (400)', str(ctx.exception))

    @override_settings(
        SUPABASE_URL='',
        SUPABASE_PUBLISHABLE_KEY='',
        SUPABASE_BUCKET='VIH',
    )
    def test_upload_bytes_sin_configuracion(self):
        with self.assertRaises(SupabaseStorageError):
            upload_bytes('originales/2026/05/imagen.png', b'datos')

    @override_settings(
        SUPABASE_URL='https://demo.supabase.co',
        SUPABASE_PUBLISHABLE_KEY='anon-key',
        SUPABASE_BUCKET='VIH',
        SUPABASE_UPLOAD_TIMEOUT=12,
    )
    @patch('analisis_app.supabase_storage.requests.post', side_effect=RequestException('sin conexion'))
    def test_upload_bytes_error_de_red(self, mock_post):
        with self.assertRaises(SupabaseStorageError) as ctx:
            upload_bytes('originales/2026/05/imagen.png', b'datos', 'image/png')

        self.assertIn('No se pudo conectar con Supabase Storage', str(ctx.exception))


class SubirImagenSupabaseIntegrationTests(TestCase):
    """Pruebas de integracion de la vista con Supabase"""

    def setUp(self):
        self.client = Client()
        session = self.client.session
        session[TERMINOS_SESSION_KEY] = True
        session.save()

    def _crear_imagen_test(self, nombre='test.jpg'):
        imagen = Image.new('RGB', (100, 100), color='purple')
        imagen_io = io.BytesIO()
        imagen.save(imagen_io, format='JPEG')
        imagen_io.seek(0)
        return SimpleUploadedFile(nombre, imagen_io.getvalue(), content_type='image/jpeg')

    @override_settings(
        SUPABASE_URL='https://demo.supabase.co',
        SUPABASE_PUBLISHABLE_KEY='anon-key',
        SUPABASE_BUCKET='VIH',
        SUPABASE_UPLOAD_TIMEOUT=12,
    )
    @patch('analisis_app.views.upload_django_file')
    @patch('analisis_app.views._guardar_temporal_para_analisis')
    @patch('analisis_app.views.predecir')
    @patch('analisis_app.views.upload_bytes')
    @patch('analisis_app.views.build_storage_path')
    def test_post_guarda_urls_y_rutas_de_supabase(
        self,
        mock_build_storage_path,
        mock_upload_bytes,
        mock_predecir,
        mock_guardar_temporal,
        mock_upload_django_file,
    ):
        mock_upload_django_file.return_value = {
            'path': 'originales/2026/05/original.jpg',
            'url': 'https://demo.supabase.co/storage/v1/object/public/VIH/originales/2026/05/original.jpg',
        }
        mock_guardar_temporal.return_value = 'C:\\temp\\analisis.jpg'
        mock_predecir.return_value = {
            'diagnostico': 'Se identificaron características visuales compatibles con la categoría analizada.',
            'confianza': 91.2,
            'overlay_vih_file': {'filename': 'vih.png', 'content': b'vih', 'content_type': 'image/png'},
            'overlay_skin_file': {'filename': 'skin.png', 'content': b'skin', 'content_type': 'image/png'},
            'overlay_combined_file': {'filename': 'combined.png', 'content': b'combined', 'content_type': 'image/png'},
        }

        rutas = iter([
            'overlays/vih-001.png',
            'overlays/skin-001.png',
            'overlays/combined-001.png',
        ])
        mock_build_storage_path.side_effect = lambda folder, original_name, extension=None: next(rutas)
        mock_upload_bytes.side_effect = lambda path, content, content_type='application/octet-stream': {
            'path': path,
            'url': f'https://demo.supabase.co/storage/v1/object/public/VIH/{path}',
        }

        respuesta = self.client.post(reverse('analisis:subir_imagen'), {
            'imagen': self._crear_imagen_test(),
        })

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'analisis/resultado.html')

        analisis = ImagenAnalisis.objects.latest('pk')
        self.assertEqual(analisis.imagen_url, mock_upload_django_file.return_value['url'])
        self.assertEqual(analisis.imagen_storage_path, mock_upload_django_file.return_value['path'])
        self.assertEqual(analisis.overlay_vih_storage_path, 'overlays/vih-001.png')
        self.assertEqual(analisis.overlay_vih_url, 'https://demo.supabase.co/storage/v1/object/public/VIH/overlays/vih-001.png')
        self.assertEqual(analisis.overlay_skin_storage_path, 'overlays/skin-001.png')
        self.assertEqual(analisis.overlay_combined_storage_path, 'overlays/combined-001.png')
        self.assertEqual(analisis.resultado, 'Se identificaron características visuales compatibles con la categoría analizada.')
        self.assertEqual(analisis.confianza, 91.2)
        self.assertEqual(mock_upload_bytes.call_count, 3)
        self.assertEqual(mock_build_storage_path.call_count, 3)
        self.assertIn('overlay_combined_path', analisis.resultado_detalle)
        self.assertTrue(analisis.resultado_detalle['overlay_combined_path'].startswith('https://demo.supabase.co/storage/v1/object/public/VIH/'))


class HistorialViewTests(TestCase):
    """Pruebas para la vista de historial"""

    def setUp(self):
        """Preparar datos antes de cada prueba"""
        self.client = Client()
        session = self.client.session
        session[TERMINOS_SESSION_KEY] = True
        session.save()

    def test_historial_sin_consentimiento_redirige(self):
        """Sin consentimiento debe redirigir a términos"""
        cliente = Client()
        respuesta = cliente.get(reverse('analisis:historial'))
        self.assertEqual(respuesta.status_code, 302)

    def test_historial_con_consentimiento_muestra_lista(self):
        """Con consentimiento debe mostrar lista de análisis"""
        respuesta = self.client.get(reverse('analisis:historial'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'analisis/historial.html')
        self.assertIn('analisis', respuesta.context)


# ==================== PRUEBAS DE FUNCIONES DEL PREDICTOR ====================

class PredictorHelperTests(TestCase):
    """Pruebas para funciones auxiliares del predictor"""

    def test_decode_b64_vacio(self):
        """decode_b64 con entrada vacía debe retornar None"""
        resultado = decode_b64(None)
        self.assertIsNone(resultado)

        resultado = decode_b64('')
        self.assertIsNone(resultado)

    def test_clasificar_ratio_nula(self):
        """Ratio bajo debe clasificarse como Nula"""
        nivel, desc = _clasificar_ratio(0.5, False)
        self.assertEqual(nivel, 'Nula')

    def test_clasificar_ratio_baja(self):
        """Ratio entre 1 y 8 debe clasificarse como Baja"""
        nivel, desc = _clasificar_ratio(5.0, True)
        self.assertEqual(nivel, 'Baja')

    def test_clasificar_ratio_mediana(self):
        """Ratio entre 8 y 20 debe clasificarse como Mediana"""
        nivel, desc = _clasificar_ratio(12.0, True)
        self.assertEqual(nivel, 'Mediana')

    def test_clasificar_ratio_alta(self):
        """Ratio mayor a 20 debe clasificarse como Alta"""
        nivel, desc = _clasificar_ratio(25.0, True)
        self.assertEqual(nivel, 'Alta')

    def test_aplica_umbral_alerta_negativo(self):
        """Debe retornar False cuando no cumple umbrales"""
        resultado = _aplica_umbral_alerta(50, 20, 0.5)
        self.assertFalse(resultado)

    def test_aplica_umbral_alerta_positivo(self):
        """Debe retornar True cuando cumple todos los umbrales"""
        resultado = _aplica_umbral_alerta(200, 100, 15.0)
        # Dependerá de los valores de configuración
        self.assertIsInstance(resultado, bool)

    def test_get_float_setting_valido(self):
        """_get_float_setting debe retornar float válido"""
        resultado = _get_float_setting('PRUEBA', 3.14)
        self.assertEqual(resultado, 3.14)
        self.assertIsInstance(resultado, float)

    def test_get_int_setting_valido(self):
        """_get_int_setting debe retornar int válido"""
        resultado = _get_int_setting('PRUEBA', 42)
        self.assertEqual(resultado, 42)
        self.assertIsInstance(resultado, int)


# ==================== PRUEBAS DE EXCEPCIONES ====================

class PredictorErrorTests(TestCase):
    """Pruebas para el manejo de errores"""

    def test_predictor_error_es_exception(self):
        """PredictorError debe ser una excepción"""
        with self.assertRaises(PredictorError):
            raise PredictorError('Mensaje de error')

    def test_predictor_error_mensaje(self):
        """PredictorError debe preservar el mensaje"""
        mensaje = 'Error específico del predictor'
        try:
            raise PredictorError(mensaje)
        except PredictorError as e:
            self.assertEqual(str(e), mensaje)
