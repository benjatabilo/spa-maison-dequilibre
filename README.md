# Spa Maison D'Equilibre

Aplicación web desarrollada con **Django** para la gestión de un spa: catálogo de terapias y terapeutas, reservas de clientes y paneles internos para administradores y terapeutas.

Proyecto para la **Evaluación Sumativa 2** de Programación Back End (TI3V41), INACAP sede La Serena.

---

## Tabla de contenidos

1. [Funcionalidades](#funcionalidades)
2. [Tecnologías](#tecnologías)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [Requisitos previos](#requisitos-previos)
5. [Instalación local (Windows)](#instalación-local-windows)
6. [Variables de entorno](#variables-de-entorno)
7. [Base de datos y roles](#base-de-datos-y-roles)
8. [Rutas principales](#rutas-principales)
9. [Despliegue en AWS EC2 (Ubuntu)](#despliegue-en-aws-ec2-ubuntu)
10. [Solución de problemas](#solución-de-problemas)
11. [Autores](#autores)

---

## Funcionalidades

El sistema tiene tres roles, y cada uno accede solo a su área. El proyecto se dividió en tres módulos, uno por integrante:

| Módulo | App de Django | Responsable |
|---|---|---|
| Administrador | `adminApp` | Benjamin |
| Terapeuta | `terapeutaApp` | Nataly |
| Usuario / Cliente | `usuarioApp` | Visnupriya |

### Módulo Administrador (Benjamin)

Área interna para gestionar el spa, en `/administrador/`. Solo accede el rol Administrador.

- **Panel general:** indicadores en vivo calculados desde la base de datos (total de terapeutas y terapias, citas de hoy e ingresos del día), gráfico de citas de la semana y tabla con las próximas citas. Las reservas canceladas no cuentan en los indicadores ni en los ingresos.
- **Mantenedor de terapias (CRUD):** listar, buscar, agregar, editar y eliminar terapias, con imagen. Valida que el nombre no esté vacío y que el precio sea mayor a 0. Si una terapia tiene reservas asociadas no se deja eliminar, y se muestra un mensaje claro en vez de un error.
- **Mantenedor de terapeutas (CRUD):** listar con buscador (nombre, profesión o correo) y filtro por profesión, agregar, editar y eliminar. El formulario pide nombre, apellido, correo, profesión, foto, certificado, las terapias que realiza y una contraseña. Al guardar, el sistema **crea automáticamente la cuenta de acceso** del terapeuta (usuario = correo) y la agrega al grupo Terapeuta.
- **Gestión de clientes:** listar con buscador y filtro por estado de cuenta, y editar los datos básicos. «Eliminar» un cliente es **desactivar** su cuenta, no borrarla, para no perder su historial de reservas. Se puede reactivar.
- **Turnos:** por cada terapeuta, cuántas citas tiene hoy y cuál es su próxima cita.
- **Perfil** del administrador.
- Acceso también al sitio de administración de Django (`/admin/`).

### Módulo Terapeuta (Nataly)

Área de consulta para los terapeutas, en `/terapeuta/`. Acceden los roles Terapeuta y Administrador. Es de **solo lectura**: consultar y buscar.

- **Mi agenda:** indicadores (citas del mes, de hoy, pendientes, confirmadas y completadas), las 5 terapias más realizadas, próximas citas y calendario semanal en forma de grilla hora × día.
- **Reservas:** listado de las reservas asignadas, con búsqueda por cliente o terapia y filtros por estado y fecha.
- **Terapias** que realiza y **perfil**.
- Cada terapeuta ve solo sus propias reservas. El administrador ve todas.

### Módulo Usuario / Cliente (Visnupriya)

Sitio público y área del cliente, en `/` y `/usuario/`.

- **Sitio público:** página de inicio, catálogo de terapias con buscador y directorio de terapeutas, ambos desde la base de datos.
- **Registro e inicio de sesión:** el login acepta nombre de usuario o correo. Todo registro público queda en el grupo Cliente, y la contraseña debe incluir letra, número y carácter especial. Al ingresar, cada rol llega a su propio panel.
- **CRUD de reservas propias:** agendar, ver detalle, editar, cancelar y eliminar. Cada cliente solo ve y modifica las suyas.
  - Una reserva cancelada o completada no se puede editar.
  - Solo se puede eliminar definitivamente una reserva que ya esté cancelada.
  - Listado con búsqueda por terapia o terapeuta y filtros por estado y rango de fechas.
- **Formulario de reserva** con selects dependientes (terapia ↔ terapeuta) y horas ocupadas deshabilitadas, mediante endpoints AJAX. Horario de atención de 9:00 a 16:00, en franjas de una hora.
- **Validaciones de la reserva:**
  - No se puede agendar en una fecha pasada ni en una hora que ya pasó.
  - El terapeuta elegido debe realizar la terapia elegida.
  - Un terapeuta no puede tener dos citas a la misma hora.
  - Un cliente no puede tener dos citas a la misma hora.
- **Perfil:** resumen con sus métricas y próximas citas, y edición de sus datos personales.

---

## Tecnologías

| Componente | Detalle |
|---|---|
| Lenguaje | Python 3.12 o superior (desarrollado con 3.14) |
| Framework | Django 6.1 |
| Base de datos | MySQL / MariaDB |
| Conexión a MySQL | PyMySQL (activado como sustituto de `MySQLdb` en `config/__init__.py`) y `mysqlclient` |
| Variables de entorno | python-dotenv |
| Imágenes | Pillow |
| Interfaz | Bootstrap 5 (archivos locales en `static/`) |

Las dependencias exactas, con versiones, están en `requirements.txt`.

---

## Estructura del proyecto

```
spa-maison-dequilibre/
├── config/                  # Configuración del proyecto (settings, urls, wsgi, asgi)
├── adminApp/                # Área del administrador (Benja)
│   ├── models.py            #   Terapia
│   ├── views.py             #   Panel, CRUD de terapias y terapeutas, clientes
│   ├── validators.py        #   Validador de complejidad de contraseña
│   └── templates/administrador/
├── terapeutaApp/            # Área del terapeuta ([Nombre])
│   ├── models.py            #   Terapeuta
│   ├── views.py             #   Agenda, reservas, terapias, perfil (solo lectura)
│   └── templates/terapeuta/
├── usuarioApp/              # Área pública y del cliente (Visnu)
│   ├── models.py            #   Reserva
│   ├── views.py             #   Login, registro, reservas, AJAX
│   ├── roles.py             #   Lógica de roles (Administrador, Terapeuta, Cliente)
│   ├── middleware.py        #   Restricción de rutas según el rol
│   ├── management/commands/crear_roles.py   # Crea los grupos y sus permisos
│   └── templates/usuario/
├── templates/               # Plantilla base compartida
├── static/                  # CSS, JS e imágenes del sitio
├── media/                   # Archivos subidos (no se versiona)
├── .env.example             # Plantilla de variables de entorno
├── requirements.txt
└── manage.py
```

### Modelos principales

- **Terapia**: nombre, precio, duración, descripción e imagen. Tabla `terapias`.
- **Terapeuta**: nombre, profesión, correo (único), foto, certificado y terapias que realiza (relación muchos a muchos con `Terapia`). Tabla `terapeutas`.
- **Reserva**: usuario, terapia, terapeuta, fecha, hora, estado (`PENDIENTE`, `CONFIRMADA`, `CANCELADA`, `COMPLETADA`) y observaciones. Tabla `reservas`.

---

## Requisitos previos

- Python 3.12 o superior.
- Servidor MySQL o MariaDB en ejecución.
- Git.

---

## Instalación local (Windows)

1. **Clonar el repositorio**
   ```powershell
   git clone <URL-DEL-REPOSITORIO>
   cd spa-maison-dequilibre
   ```

2. **Crear y activar el entorno virtual**
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Instalar las dependencias**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Crear el archivo `.env`** a partir de la plantilla y completarlo (ver [Variables de entorno](#variables-de-entorno)):
   ```powershell
   copy .env.example .env
   ```

5. **Crear la base de datos** en MySQL (ver [Base de datos y roles](#base-de-datos-y-roles)).

6. **Aplicar migraciones, crear los roles y un superusuario**:
   ```powershell
   python manage.py migrate
   python manage.py crear_roles
   python manage.py createsuperuser
   ```

7. **Iniciar el servidor**:
   ```powershell
   python manage.py runserver
   ```
   Abrir <http://127.0.0.1:8000>.

---

## Variables de entorno

La configuración sensible vive en un archivo `.env` en la raíz del proyecto. **Ese archivo no se sube a git**; el repositorio solo incluye `.env.example`, con los valores vacíos.

| Variable | Descripción | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django. **Obligatoria**: si falta, el proyecto no arranca. Debe ser larga y distinta en cada entorno. | *(cadena aleatoria larga)* |
| `DEBUG` | `True` solo en desarrollo. Cualquier otro valor, o si falta, equivale a `False`. | `True` |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma y sin espacios. En producción debe incluir la IP pública o el dominio. | `localhost,127.0.0.1` |
| `DB_ENGINE` | Motor de base de datos. | `django.db.backends.mysql` |
| `DB_NAME` | Nombre de la base de datos. | `spa-maison-dequilibre` |
| `DB_USER` | Usuario de MySQL. | `administrador` |
| `DB_PASSWORD` | Contraseña del usuario de MySQL. | |
| `DB_HOST` | Servidor de la base de datos. | `localhost` |
| `DB_PORT` | Puerto. | `3306` |

El usuario y la contraseña del `.env` deben coincidir con los que existen en el MySQL de **esa** máquina. Cada entorno (tu PC, el servidor) tiene su propio `.env`.

Para generar una `SECRET_KEY` nueva:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Base de datos y roles

### Crear la base y un usuario

Entrar a MySQL (`mysql -u root -p`, o `sudo mysql` en Ubuntu) y ejecutar:

```sql
CREATE DATABASE `spa-maison-dequilibre` CHARACTER SET utf8mb4;
CREATE USER 'administrador'@'localhost' IDENTIFIED BY 'UNA-CLAVE-SEGURA';
GRANT ALL PRIVILEGES ON `spa-maison-dequilibre`.* TO 'administrador'@'localhost';
FLUSH PRIVILEGES;
```

Después, poner ese usuario y esa clave en `DB_USER` y `DB_PASSWORD` del `.env`. Los acentos graves alrededor del nombre de la base son necesarios por los guiones.

### Roles

El comando `crear_roles` crea los grupos y sus permisos. Es seguro volver a ejecutarlo.

```bash
python manage.py crear_roles
```

| Rol | Permisos sobre terapias | Sobre terapeutas | Sobre reservas |
|---|---|---|---|
| Administrador | Completo | Completo | Completo |
| Terapeuta | Solo ver | Solo ver | Solo ver |
| Cliente | — | — | Completo (solo las propias) |

- Quien se registra desde el sitio queda automáticamente en el grupo **Cliente**.
- Un usuario sin grupo se trata como Cliente, el caso más restrictivo.
- Un **superusuario** se considera Administrador.

### Crear un terapeuta que pueda iniciar sesión

Se hace desde el panel del administrador, en **Terapeutas → Nuevo**: se completan sus datos, su correo y una contraseña. Al guardar, el sistema crea la ficha del terapeuta y su cuenta de acceso (el usuario es el correo) y la agrega al grupo **Terapeuta**.

El sistema vincula al usuario con su ficha comparando `User.email` con `Terapeuta.correo`. Si un terapeuta no tiene cuenta (por ejemplo, una ficha antigua), basta editarlo desde el panel del administrador y asignarle una contraseña. Un terapeuta sin ficha vinculada puede entrar, pero ve un panel sin reservas.

### Control de acceso por rol

Un middleware (`RestriccionPorRolMiddleware`) restringe las rutas internas:

| Ruta | Quién puede entrar |
|---|---|
| `/administrador/` | Solo Administrador |
| `/terapeuta/` | Administrador y Terapeuta |
| `/usuario/reservas/` y `/usuario/perfil/` | Solo Cliente |

Quien intenta entrar a una zona que no le corresponde es redirigido a su panel con un mensaje de error. Al iniciar sesión, cada rol llega a su propio panel.

---

## Rutas principales

| Ruta | Descripción |
|---|---|
| `/` | Página de inicio |
| `/usuario/terapias/`, `/usuario/terapeutas/` | Catálogo público |
| `/usuario/login/`, `/usuario/registro/` | Autenticación |
| `/usuario/reservas/` | Reservas del cliente (listar, crear, editar, cancelar, eliminar) |
| `/administrador/` | Panel del administrador |
| `/administrador/terapias/` | CRUD de terapias |
| `/administrador/terapeutas/` | CRUD de terapeutas |
| `/administrador/clientes/` | Gestión de clientes |
| `/terapeuta/` | Agenda del terapeuta |
| `/terapeuta/reservas/` | Reservas asignadas, con búsqueda y filtros |
| `/admin/` | Sitio de administración de Django |

---

## Despliegue en AWS EC2 (Ubuntu)

Estos comandos se ejecutan **en la instancia**, conectado por SSH.

### 1. Paquetes del sistema

`mysqlclient` se compila al instalarse, y para eso Ubuntu necesita herramientas y las cabeceras de MySQL. Hay que instalarlas **antes** de las dependencias de Python:

```bash
sudo apt update
sudo apt install -y build-essential pkg-config python3-dev python3-venv default-libmysqlclient-dev
```

Si falta alguno, `pip install` falla con errores como `mysql_config not found`.

### 2. Código y entorno virtual

```bash
git clone <URL-DEL-REPOSITORIO>
cd spa-maison-dequilibre
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Ubuntu reciente no permite instalar paquetes de Python fuera de un entorno virtual, por eso se usa `venv`.

> `requirements.txt` debe estar guardado en **UTF-8**. Si queda en UTF-16 (por ejemplo, tras `pip freeze > requirements.txt` en PowerShell), `pip install` falla en Linux.

### 3. Archivo `.env` del servidor

El `.env` no viaja con git, así que hay que crearlo en el servidor:

```bash
cp .env.example .env
nano .env
```

Valores recomendados:

- `SECRET_KEY`: una clave **nueva**, distinta de la de desarrollo.
- `DEBUG=False`.
- `ALLOWED_HOSTS`: `localhost,127.0.0.1,<IP-PUBLICA-O-DOMINIO>`.
- `DB_*`: los datos del MySQL del servidor (o el endpoint de RDS en `DB_HOST`).

### 4. Base de datos

En el servidor, MySQL no deja que `root` se conecte con contraseña desde Django. Hay que crear un usuario propio, como se muestra en [Base de datos y roles](#base-de-datos-y-roles) (se entra con `sudo mysql`).

### 5. Migraciones y verificación

```bash
python manage.py migrate
python manage.py crear_roles
python manage.py createsuperuser
python manage.py check
```

`check` debe terminar con `System check identified no issues`.

### 6. Puesta en marcha

Para una prueba rápida:

```bash
python manage.py runserver 0.0.0.0:8000
```

Y abrir el puerto 8000 en el grupo de seguridad de la instancia.

**Archivos estáticos y `media/` con `DEBUG=False`:** el servidor de desarrollo de Django no los sirve en ese modo. Para un despliegue estable conviene un servidor web (por ejemplo Nginx) que sirva `static/` y `media/`, junto con Gunicorn para ejecutar la aplicación. Para una demostración rápida se puede usar `python manage.py runserver 0.0.0.0:8000 --insecure`, que **no es apto para producción**.

---

## Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| `Falta SECRET_KEY en el archivo .env` | No existe `.env` o no tiene `SECRET_KEY`. | Crear el `.env` desde `.env.example` y completarlo. |
| `Access denied for user ... (using password: YES)` | Usuario o contraseña del `.env` no coinciden con los de MySQL. | Revisar `DB_USER` y `DB_PASSWORD`, o crear el usuario en MySQL. |
| `DisallowedHost` / error 400 | La IP o dominio no está en `ALLOWED_HOSTS`. | Agregarla en el `.env` y reiniciar. |
| `mysql_config not found` al instalar | Faltan los paquetes de sistema. | Instalar `default-libmysqlclient-dev` y el resto de la lista de la sección de despliegue. |
| Error de codificación al hacer `pip install -r` | `requirements.txt` está en UTF-16. | Guardarlo de nuevo como UTF-8. |
| Un terapeuta entra y no ve reservas | Su correo de usuario no coincide con el de su ficha, o aún no tiene reservas asignadas. | Editar al terapeuta desde el panel del administrador y revisar que el correo sea el mismo. |
| Las imágenes no cargan con `DEBUG=False` | Django no sirve `media/` ni `static/` en ese modo. | Usar un servidor web (Nginx) para ambos. |

---

## Autores

| Integrante | Módulo |
|---|---|
| Benjamin | Administrador (`adminApp`) |
| Nataly | Terapeuta (`terapeutaApp`) |
| Visnupriya | Usuario / Cliente (`usuarioApp`) |

<<<<<<< HEAD
Programación Back End (TI3V41), INACAP sede La Serena, 2026.
=======
Programación Back End (TI3V41), INACAP sede La Serena, 2026.
>>>>>>> origin/main
