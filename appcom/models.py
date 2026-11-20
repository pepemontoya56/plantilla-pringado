# models.py

from decimal import Decimal
import random

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models



# ==========================================================
# MODELO USER (NATIVO DE DJANGO)
# ==========================================================
# Se utiliza el modelo User nativo de Django.
# No es necesario definirlo nuevamente.
#
# Relaciones:
#
# User (1) -------- (1) ProfileUser
# User (1) -------- (*) Partida
#
# Un usuario tiene un perfil.
# Un usuario puede jugar múltiples partidas.
# ==========================================================


# ==========================================================
# MODELO PROFILEUSER
# ==========================================================

class ProfileUser(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    fecha_nacimiento = models.DateField(null=True, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio = models.TextField(blank=True)
    saldo_virtual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1000.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"


# ==========================================================
# MODELO PARTIDA
# ==========================================================

class Partida(models.Model):
    # Tipos de juegos disponibles en el casino virtual
    TIPOS_JUEGO = [
        ("blackjack", "Blackjack"),
        ("ruleta", "Ruleta"),
        ("slots", "Máquinas tragamonedas"),
        ("poker", "Póker"),
        ("dados", "Dados"),
        ("keno", "Keno"),
        ("carreras", "Carreras"),
        ("bingo", "Bingo"),
    ]

    # Resultados posibles
    RESULTADOS = [
        ("pendiente", "Pendiente"),
        ("victoria", "Victoria"),
        ("derrota", "Derrota"),
        ("empate", "Empate"),
    ]

    # Relación User (1) -> (*) Partida
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="partidas",
    )
    juego = models.CharField(max_length=20, choices=TIPOS_JUEGO)
    fecha = models.DateTimeField(auto_now_add=True)
    apuesta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    puntos = models.IntegerField(default=0)
    resultado = models.CharField(
        max_length=20,
        choices=RESULTADOS,
        default="pendiente",
    )
    premio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Partida"
        verbose_name_plural = "Partidas"

    def __str__(self):
        return (
            f"Partida {self.pk} - "
            f"{self.usuario.username} - "
            f"{self.get_juego_display()}"
        )


