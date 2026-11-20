from decimal import Decimal
import random

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


# Create your models here.


# ==========================================================
# MODELO RULETA
# ==========================================================
Partida = models.OneToOneField(
    "appcom.Partida",
    on_delete=models.CASCADE,
    related_name="ruleta",
)
class Ruleta(models.Model):

    partida = models.OneToOneField(
        Partida,
        on_delete=models.CASCADE,
        related_name="ruleta",
    )

    numero_resultado = models.PositiveSmallIntegerField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    @property
    def color_resultado(self):
        if self.numero_resultado is None:
            return None
        if self.numero_resultado == 0:
            return "verde"

        numero = NumeroRuleta.objects.filter(
            num=self.numero_resultado
        ).first()

        return numero.color if numero else None

    def girar(self):
        if self.numero_resultado is not None:
            raise ValidationError("La ruleta ya ha girado.")

        self.numero_resultado = random.SystemRandom().randint(0, 36)
        self.save()

        premios = self.premios.all()

        for apuesta in premios:
            apuesta.comprobar(self.numero_resultado)

        total_premios = sum(
            (p.premio for p in premios),
            Decimal("0.00"),
        )

        self.partida.premio = total_premios

        if total_premios > self.partida.apuesta:
            self.partida.resultado = "victoria"
        elif total_premios == self.partida.apuesta:
            self.partida.resultado = "empate"
        else:
            self.partida.resultado = "derrota"

        self.partida.save()
        return self.numero_resultado

    def __str__(self):
        return f"Ruleta - Partida {self.partida_id}"


class NumeroRuleta(models.Model):

    num = models.PositiveSmallIntegerField(unique=True)
    color = models.CharField(max_length=10)
    par = models.BooleanField()

    s12 = models.PositiveSmallIntegerField()
    fila = models.PositiveSmallIntegerField()
    colum = models.PositiveSmallIntegerField()
    medio = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.num} - {self.color}"


# ==========================================================
# MODELO PREMIO
# ==========================================================

class Premio(models.Model):
    TIPOS_APUESTA = [
        # APUESTAS INTERNAS
        ("pleno", "Número individual"),
        ("caballo", "Caballo (2 números)"),
        ("transversal", "Transversal (3 números)"),
        ("cuadro", "Cuadro (4 números)"),
        ("seisena", "Seisena (6 números)"),
        # APUESTAS EXTERNAS
        ("color", "Rojo / Negro"),
        ("paridad", "Par / Impar"),
        ("mitad", "Falta / Pasa"),
        ("docena", "Docenas"),
        ("columna", "Columnas"),
    ]

    MULTIPLICADORES = {
        "pleno": 35,
        "caballo": 17,
        "transversal": 11,
        "cuadro": 8,
        "seisena": 5,
        "color": 1,
        "paridad": 1,
        "mitad": 1,
        "docena": 2,
        "columna": 2,
    }

    ruleta = models.ForeignKey(
        Ruleta,
        on_delete=models.CASCADE,
        related_name="premios",
    )
    tipo = models.CharField(max_length=20, choices=TIPOS_APUESTA)
    seleccion = models.CharField(max_length=30)
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    ganada = models.BooleanField(null=True, blank=True, default=None)
    premio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    def clean(self):
        numeros_por_tipo = {
            "pleno": 1,
            "caballo": 2,
            "transversal": 3,
            "cuadro": 4,
            "seisena": 6,
        }

        if self.tipo in numeros_por_tipo:
            try:
                numeros = [int(n.strip()) for n in self.seleccion.split(",")]
            except ValueError:
                raise ValidationError("Introduce números separados por comas.")

            if len(numeros) != numeros_por_tipo[self.tipo]:
                raise ValidationError("Cantidad de números incorrecta para esta apuesta.")

            if len(set(numeros)) != len(numeros):
                raise ValidationError("No puedes repetir números.")

            if any(n < 0 or n > 36 for n in numeros):
                raise ValidationError("Los números deben estar entre 0 y 36.")
        else:
            opciones = {
                "color": ["rojo", "negro"],
                "paridad": ["par", "impar"],
                "mitad": ["falta", "pasa"],
                "docena": ["1", "2", "3"],
                "columna": ["1", "2", "3"],
            }
            if self.seleccion not in opciones[self.tipo]:
                raise ValidationError("Selección incorrecta para esta apuesta.")

    def comprobar(self, numero):
        if self.ganada is not None:
            return self.ganada

        if self.tipo in ["pleno", "caballo", "transversal", "cuadro", "seisena"]:
            numeros = [int(n.strip()) for n in self.seleccion.split(",")]
            ganada = numero in numeros

        elif self.tipo == "color":
            if self.seleccion == "rojo":
                ganada = numero in Ruleta.NUMEROS_ROJOS
            else:
                ganada = numero != 0 and numero not in Ruleta.NUMEROS_ROJOS

        elif self.tipo == "paridad":
            ganada = (
                numero != 0
                and (
                    (numero % 2 == 0 and self.seleccion == "par")
                    or (numero % 2 != 0 and self.seleccion == "impar")
                )
            )

        elif self.tipo == "mitad":
            ganada = (
                (1 <= numero <= 18 and self.seleccion == "falta")
                or (19 <= numero <= 36 and self.seleccion == "pasa")
            )

        elif self.tipo == "docena":
            ganada = numero != 0 and (numero - 1) // 12 + 1 == int(self.seleccion)

        elif self.tipo == "columna":
            ganada = numero != 0 and (numero - 1) % 3 + 1 == int(self.seleccion)

        else:
            ganada = False

        self.ganada = ganada

        if ganada:
            multiplicador = self.MULTIPLICADORES[self.tipo]
            # Devuelve apuesta + beneficio
            self.premio = self.cantidad * (multiplicador + 1)
        else:
            self.premio = Decimal("0.00")

        self.save()
        return ganada

    @property
    def beneficio(self):
        if not self.ganada:
            return Decimal("0.00")
        return self.premio - self.cantidad

    def __str__(self):
        return (
            f"{self.get_tipo_display()} - "
            f"{self.seleccion} - "
            f"{self.cantidad}€"
        )


# ==========================================================
# EJEMPLOS DE USO (EN VISTAS O EN DJANGO SHELL)
# ==========================================================
#
# from django.contrib.auth import get_user_model
# from decimal import Decimal
# from .models import ProfileUser, Partida
#
# User = get_user_model()
#
# # Crear usuario
# usuario = User.objects.create_user(
#     username="jugador1",
#     email="jugador1@example.com",
#     password="password_segura_123"
# )
#
# # Crear perfil asociado al usuario
# perfil = ProfileUser.objects.create(
#     user=usuario,
#     saldo_virtual=Decimal("1000.00")
# )
#
# # Crear una partida de Blackjack
# partida1 = Partida.objects.create(
#     usuario=usuario,
#     juego="blackjack",
#     apuesta=Decimal("50.00"),
#     puntos=21,
#     resultado="victoria",
#     premio=Decimal("100.00")
# )
#
# # Crear una partida de Ruleta
# partida2 = Partida.objects.create(
#     usuario=usuario,
#     juego="ruleta",
#     apuesta=Decimal("25.00"),
#     resultado="derrota",
#     premio=Decimal("0.00")
# )
#
# # Consultar el perfil de un usuario
# perfil = usuario.perfil
#
# # Consultar todas las partidas de un usuario
# partidas = usuario.partidas.all()
#
# # Consultar partidas de Blackjack
# partidas_blackjack = usuario.partidas.filter(juego="blackjack")
#
# ==========================================================
# COMANDOS PARA CREAR LAS MIGRACIONES
# ==========================================================
#
# pip install Pillow
#
# python manage.py makemigrations
# python manage.py migrate
#
# ==========================================================
# NOTAS
# ==========================================================
#
# 1. User es el modelo de autenticación nativo de Django.
#
# 2. ProfileUser utiliza OneToOneField:
#    Un usuario -> Un perfil.
#
# 3. Partida utiliza ForeignKey:
#    Un usuario -> Muchas partidas.
#
# 4. El campo "juego" permite almacenar partidas
#    de diferentes juegos del casino.
#
# 5. El saldo_virtual representa créditos ficticios.
#
# 6. La creación del perfil no es automática.
#    Puede implementarse mediante una señal post_save
#    o en el flujo de registro.
#
# 7. Las apuestas, premios y saldos deben actualizarse
#    mediante operaciones atómicas y transacciones
#    para evitar inconsistencias.
#
# 8. Este modelo está pensado para créditos virtuales
#    sin valor monetario ni posibilidad de retirada.
#
# ==========================================================