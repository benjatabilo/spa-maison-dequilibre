1. Modelo de la transacción

Prompt: ¿Cómo relaciono una reserva con un usuario, una terapia y un terapeuta en Django ORM?
Respuesta: Crear un modelo Reserva con tres ForeignKey y usar related_name para las consultas inversas.
Incorporación: Creé Reserva en models.py con RESTRICT hacia Terapia y Terapeuta y CASCADE hacia User. Luego ejecuté las migraciones.

2. Login y registro

Prompt: ¿Cómo hago un login con Django Authentication que acepte usuario o correo?
Respuesta: Usar authenticate(). Si el texto contiene "@", buscar el usuario por email y autenticar con su username.
Incorporación: Lo implementé en login_view. Para el registro usé un RegistroForm que extiende UserCreationForm.

3. Perfiles de usuario

Prompt: ¿Cómo implemento tres roles con permisos usando los grupos de Django?
Respuesta: Crear grupos y asignarles permisos add, change, delete y view con un comando de gestión.
Incorporación: Hice el comando crear_roles.py y la función obtener_rol() en roles.py. Todo registro público queda como Cliente.

4. Restricción de acceso

Prompt: ¿Cómo bloqueo rutas según el rol del usuario?
Respuesta: Usar un middleware que revise request.path y el rol, y redirija si no hay permiso.
Incorporación: Creé RestriccionPorRolMiddleware, lo registré en settings.py y agregué @login_required en las vistas.

5. CRUD con búsqueda

Prompt: ¿Cómo hago listar, buscar y filtrar reservas con consultas ORM?
Respuesta: Usar filter() con objetos Q y icontains, y recibir los parámetros por GET.
Incorporación: Lo apliqué en mis_reservas con filtros por texto, estado y fechas. Cada reserva se consulta con usuario=request.user.

6. Validaciones del formulario

Prompt: ¿Cómo evito que se agenden dos citas en la misma hora?
Respuesta: Validar en el método clean() del formulario, consultando reservas existentes y excluyendo las canceladas.
Incorporación: Lo agregué en ReservaForm.clean(), junto con la validación de fecha pasada y de terapeuta-terapia.

7. Menú dinámico por rol

Prompt: ¿Cómo muestro un menú distinto según el perfil en las plantillas?
Respuesta: Crear un context processor que entregue el rol a todos los templates y usar {% if %}.
Incorporación: Hice rol_usuario en context_processors.py, lo registré en settings.py y lo usé en base.html.

8. Modelo del mantenedor

Prompt: ¿Cómo diseño un modelo Terapia con precio, duración e imagen en Django?
Respuesta: Usar CharField, DecimalField, PositiveIntegerField y ImageField con upload_to, más un campo creado automático.
Incorporación: Se creó Terapia en models.py, se instaló Pillow y se ejecutaron las migraciones.

9. Registro en Django Admin

Prompt: ¿Cómo personalizo Django Admin para buscar y filtrar terapias?
Respuesta: Usar @admin.register con list_display, search_fields, list_filter y fieldsets.
Incorporación: Se aplicó en TerapiaAdmin, con búsqueda por nombre y descripción y filtro por duración.

10. Validador de contraseña

Prompt: ¿Cómo creo un validador de contraseña propio con reglas de complejidad?
Respuesta: Crear una clase con los métodos validate() y get_help_text(), y registrarla en AUTH_PASSWORD_VALIDATORS.
Incorporación: Se creó ComplejidadPasswordValidator en adminApp/validators.py y se agregó en settings.py.

11. Panel del administrador

Prompt: ¿Cómo hago un panel para que el administrador gestione terapias con CRUD?
Respuesta: Crear vistas protegidas con @login_required, formularios ModelForm y plantillas con Bootstrap.
Incorporación: Se implementó en la vista panel_admin, con listado, buscador y formularios de agregar, modificar y eliminar.

12. Modelo con archivos

Prompt: ¿Cómo guardo la foto y el certificado de un terapeuta en Django?
Respuesta: Usar ImageField para la foto y FileField para el certificado, con upload_to y MEDIA_ROOT.
Incorporación: Se agregaron foto y certificado al modelo Terapeuta y se configuró MEDIA_URL en settings.py.

13. Relación entre terapeutas y terapias

Prompt: ¿Cómo relaciono un terapeuta con varias terapias y viceversa?
Respuesta: Usar un ManyToManyField con related_name, para consultar terapeuta.terapias y terapia.terapeutas.
Incorporación: Se definió la relación en el modelo y se usó en los filtros de la reserva.

14. Servir archivos subidos

Prompt: ¿Cómo muestro en las plantillas las imágenes y los PDF que se suben?
Respuesta: Agregar static(settings.MEDIA_URL, ...) a las URLs en desarrollo y usar {{ campo.url }} en el template.
Incorporación: Se configuró en urls.py y se mostró la foto en el listado y el certificado como enlace de descarga.

15. Variables de entorno

Prompt: ¿Cómo oculto la clave secreta y la contraseña de la base de datos?
Respuesta: Guardarlas en un .env, cargarlas con python-dotenv y agregar .env al .gitignore.
Incorporación: Se usó load_dotenv() y os.getenv en settings.py para la clave, DEBUG y los datos de MySQL.

16. Panel de rendimiento del terapeuta

Prompt: ¿Cómo muestro métricas de reservas por terapeuta con consultas ORM?
Respuesta: Usar filter() y annotate() con Count sobre la relación reservas.
Incorporación: Se aplicó en la vista rendimiento_terapeuta.