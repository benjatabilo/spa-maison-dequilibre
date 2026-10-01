import re
from django.core.exceptions import ValidationError


class ComplejidadPasswordValidator:

    def validate(self, password, user=None):
        if not re.search(r'[A-Za-z]', password):
            raise ValidationError(
                'La contraseña debe incluir al menos una letra.',
                code='password_sin_letra',
            )
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                'La contraseña debe incluir al menos un número.',
                code='password_sin_numero',
            )
        if not re.search(r'[^A-Za-z0-9]', password):
            raise ValidationError(
                'La contraseña debe incluir al menos un carácter especial (ej: ! @ # $ % & *).',
                code='password_sin_caracter_especial',
            )

    def get_help_text(self):
        return 'Tu contraseña debe incluir al menos una letra, un número y un carácter especial.'