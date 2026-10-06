from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import TestCase
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient


def crear_usuario(username, grupo=None, **extra):
    user = User.objects.create_user(username, password='Clave#Segura2026', **extra)
    if grupo:
        user.groups.add(Group.objects.get_or_create(name=grupo)[0])
    return user


class AutenticacionJWTTest(TestCase):
    def setUp(self):
        cache.clear()                         # reinicia el contador de intentos (throttling)
        self.api = APIClient()
        self.cliente = crear_usuario('cliente1', 'Cliente', first_name='Ana', last_name='Soto',
                                     email='ana@privado.cl')

    def pedir_token(self, username='cliente1', password='Clave#Segura2026'):
        return self.api.post(reverse('token_obtain_pair'),
                             {'username': username, 'password': password}, format='json')

    def test_login_entrega_access_refresh_y_rol(self):
        r = self.pedir_token()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json()), {'access', 'refresh', 'rol'})
        self.assertEqual(r.json()['rol'], 'Cliente')

    def test_token_no_contiene_datos_sensibles(self):
        from rest_framework_simplejwt.tokens import AccessToken
        contenido = AccessToken(self.pedir_token().json()['access']).payload
        self.assertEqual(contenido['rol'], 'Cliente')
        self.assertNotIn('ana@privado.cl', str(contenido))
        self.assertNotIn('password', str(contenido).lower())

    def test_credenciales_incorrectas_401_json(self):
        r = self.pedir_token(password='mala')
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r['Content-Type'], 'application/json')
        self.assertIn('detail', r.json())

    def test_usuario_inactivo_no_obtiene_token(self):
        self.cliente.is_active = False
        self.cliente.save()
        self.assertEqual(self.pedir_token().status_code, 401)

    def test_endpoint_protegido_sin_token_401(self):
        r = self.api.get(reverse('api_me'))
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r['Content-Type'], 'application/json')

    def test_endpoint_protegido_con_token_200(self):
        access = self.pedir_token().json()['access']
        r = self.api.get(reverse('api_me'), HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'username': 'cliente1', 'nombre': 'Ana Soto', 'rol': 'Cliente'})

    def test_token_falso_o_manipulado_401(self):
        r = self.api.get(reverse('api_me'), HTTP_AUTHORIZATION='Bearer esto.no.es.un.jwt')
        self.assertEqual(r.status_code, 401)

    def test_refresh_entrega_nuevo_access_y_rota_el_refresh(self):
        refresh_viejo = self.pedir_token().json()['refresh']
        r = self.api.post(reverse('token_refresh'), {'refresh': refresh_viejo}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.json())
        self.assertNotEqual(r.json()['refresh'], refresh_viejo)
        # el refresh anterior quedó en lista negra: no se puede reutilizar
        reuso = self.api.post(reverse('token_refresh'), {'refresh': refresh_viejo}, format='json')
        self.assertEqual(reuso.status_code, 401)

    def test_access_token_no_sirve_como_refresh(self):
        access = self.pedir_token().json()['access']
        r = self.api.post(reverse('token_refresh'), {'refresh': access}, format='json')
        self.assertEqual(r.status_code, 401)

    def test_login_limita_intentos_429(self):
        codigos = [self.pedir_token(password='mala').status_code for _ in range(12)]
        self.assertIn(429, codigos)           # tras 10 intentos/min se bloquea


class SwaggerTest(TestCase):
    def test_swagger_ui_y_redoc_cargan(self):
        self.assertEqual(self.client.get(reverse('swagger-ui')).status_code, 200)
        self.assertEqual(self.client.get(reverse('redoc')).status_code, 200)

    def test_esquema_openapi_incluye_jwt_y_endpoints(self):
        r = self.client.get(reverse('schema'), {'format': 'json'})
        self.assertEqual(r.status_code, 200)
        esquema = r.json()
        self.assertIn('/api/token/', esquema['paths'])
        self.assertIn('/api/token/refresh/', esquema['paths'])
        self.assertIn('/api/me/', esquema['paths'])
        esquemas_seguridad = esquema['components']['securitySchemes']
        self.assertEqual(esquemas_seguridad['jwtAuth']['scheme'], 'bearer')


# =====================================================================
# Roles, datos sensibles y códigos HTTP de los mantenedores y la transacción
# =====================================================================
from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta
from usuarioApp.models import Reserva


class ApiRolesTest(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = crear_usuario('admin1', 'Administrador', email='admin@spa.cl')
        self.cliente = crear_usuario('cliente1', 'Cliente', email='c1@spa.cl')
        self.otro = crear_usuario('cliente2', 'Cliente', email='c2@spa.cl')
        self.tera_user = crear_usuario('tera@spa.cl', 'Terapeuta', email='tera@spa.cl')

        self.terapia = Terapia.objects.create(nombre='Masaje', precio=30000, duracion='60 min')
        self.terapeuta = Terapeuta.objects.create(nombre='Luz Rojas', profesion='Masoterapeuta',
                                                  correo='tera@spa.cl')
        self.terapeuta.terapias.add(self.terapia)
        self.fecha = (timezone.localdate() + timedelta(days=3)).isoformat()

    def como(self, usuario):
        api = APIClient()
        api.force_authenticate(usuario)
        return api

    def datos_reserva(self, hora='10:00'):
        return {'terapia': self.terapia.pk, 'terapeuta': self.terapeuta.pk,
                'fecha': self.fecha, 'hora': hora}

    # --- 401 / acceso general ---
    def test_sin_token_401_en_todos_los_recursos(self):
        for nombre in ('terapia-list', 'terapeuta-list', 'reserva-list'):
            self.assertEqual(APIClient().get(reverse(nombre)).status_code, 401, nombre)

    # --- datos sensibles: serializers diferenciados ---
    def test_cliente_no_ve_correo_ni_certificado_del_terapeuta(self):
        r = self.como(self.cliente).get(reverse('terapeuta-list'))
        self.assertEqual(r.status_code, 200)
        ficha = r.json()['results'][0]
        self.assertNotIn('correo', ficha)
        self.assertNotIn('certificado', ficha)
        self.assertNotIn('password', ficha)

    def test_admin_ve_correo_y_nunca_la_password(self):
        r = self.como(self.admin).get(reverse('terapeuta-list'))
        ficha = r.json()['results'][0]
        self.assertEqual(ficha['correo'], 'tera@spa.cl')
        self.assertNotIn('password', ficha)

    # --- 403: permisos ---
    def test_cliente_no_puede_crear_terapias_403(self):
        r = self.como(self.cliente).post(reverse('terapia-list'),
                                         {'nombre': 'X', 'precio': 1000, 'duracion': '30'}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_admin_crea_terapia_201_y_valida_400(self):
        api = self.como(self.admin)
        ok = api.post(reverse('terapia-list'),
                      {'nombre': 'Facial', 'precio': 25000, 'duracion': '45 min'}, format='json')
        self.assertEqual(ok.status_code, 201)
        malo = api.post(reverse('terapia-list'),
                        {'nombre': 'Otra', 'precio': -5, 'duracion': '45 min'}, format='json')
        self.assertEqual(malo.status_code, 400)
        self.assertIn('precio', malo.json())

    def test_terapeuta_no_puede_crear_reservas_403(self):
        r = self.como(self.tera_user).post(reverse('reserva-list'), self.datos_reserva(), format='json')
        self.assertEqual(r.status_code, 403)

    # --- reservas: filtrado por dueño ---
    def test_cliente_crea_reserva_propia_y_estado_queda_pendiente(self):
        r = self.como(self.cliente).post(reverse('reserva-list'),
                                         {**self.datos_reserva(), 'estado': 'CONFIRMADA'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['estado'], 'PENDIENTE')            # no puede autoconfirmarse
        self.assertEqual(Reserva.objects.get().usuario, self.cliente)  # el dueño sale del token

    def test_cliente_no_accede_a_reserva_ajena_404(self):
        reserva = Reserva.objects.create(usuario=self.otro, terapia=self.terapia, terapeuta=self.terapeuta,
                                         fecha=self.fecha, hora='11:00')
        api = self.como(self.cliente)
        self.assertEqual(api.get(reverse('reserva-detail', args=[reserva.pk])).status_code, 404)
        self.assertEqual(api.delete(reverse('reserva-detail', args=[reserva.pk])).status_code, 404)
        self.assertEqual(api.get(reverse('reserva-list')).json()['count'], 0)

    def test_terapeuta_solo_ve_sus_reservas_en_lectura(self):
        Reserva.objects.create(usuario=self.cliente, terapia=self.terapia, terapeuta=self.terapeuta,
                               fecha=self.fecha, hora='11:00')
        r = self.como(self.tera_user).get(reverse('reserva-list'))
        self.assertEqual(r.json()['count'], 1)

    def test_admin_ve_todo_y_cambia_estado(self):
        reserva = Reserva.objects.create(usuario=self.cliente, terapia=self.terapia,
                                         terapeuta=self.terapeuta, fecha=self.fecha, hora='11:00')
        api = self.como(self.admin)
        r = api.patch(reverse('reserva-detail', args=[reserva.pk]), {'estado': 'CONFIRMADA'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['estado'], 'CONFIRMADA')

    # --- validaciones de negocio (400) ---
    def test_no_permite_fecha_pasada_ni_hora_fuera_de_horario(self):
        api = self.como(self.cliente)
        ayer = (timezone.localdate() - timedelta(days=1)).isoformat()
        self.assertEqual(api.post(reverse('reserva-list'), {**self.datos_reserva(), 'fecha': ayer},
                                  format='json').status_code, 400)
        self.assertEqual(api.post(reverse('reserva-list'), self.datos_reserva('23:00'),
                                  format='json').status_code, 400)

    def test_no_permite_doble_reserva_del_terapeuta_a_la_misma_hora(self):
        Reserva.objects.create(usuario=self.otro, terapia=self.terapia, terapeuta=self.terapeuta,
                               fecha=self.fecha, hora='10:00')
        r = self.como(self.cliente).post(reverse('reserva-list'), self.datos_reserva('10:00'), format='json')
        self.assertEqual(r.status_code, 400)

    # --- 409: borrar algo en uso ---
    def test_borrar_terapia_con_reservas_409_json(self):
        Reserva.objects.create(usuario=self.cliente, terapia=self.terapia, terapeuta=self.terapeuta,
                               fecha=self.fecha, hora='11:00')
        r = self.como(self.admin).delete(reverse('terapia-detail', args=[self.terapia.pk]))
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r['Content-Type'], 'application/json')

    def test_404_en_json_para_recurso_inexistente(self):
        r = self.como(self.admin).get(reverse('terapia-detail', args=[9999]))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r['Content-Type'], 'application/json')
