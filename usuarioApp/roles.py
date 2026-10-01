ADMINISTRADOR = 'Administrador'
TERAPEUTA = 'Terapeuta'
CLIENTE = 'Cliente'


def obtener_rol(user):
    """
    Devuelve el rol del usuario: ADMINISTRADOR, TERAPEUTA o CLIENTE.
    Un usuario sin grupo asignado se considera Cliente (el caso más restrictivo).
    """
    if not user.is_authenticated:
        return None
    if user.is_superuser or user.groups.filter(name=ADMINISTRADOR).exists():
        return ADMINISTRADOR
    if user.groups.filter(name=TERAPEUTA).exists():
        return TERAPEUTA
    return CLIENTE