from django.core.validators import MinValueValidator
from django.db import models

from apps.common.constants import PRIX_MINIMUM_NUIT
from apps.common.utils import format_ar


class Categorie(models.Model):
    nom = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'categories_chambres'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Equipement(models.Model):
    nom = models.CharField(max_length=80, unique=True)
    icone = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'equipements'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Chambre(models.Model):
    class Statut(models.TextChoices):
        DISPONIBLE = 'DISPONIBLE', 'Disponible'
        RESERVEE = 'RESERVEE', 'Réservée'
        OCCUPEE = 'OCCUPEE', 'Occupée'
        NETTOYAGE = 'NETTOYAGE', 'En nettoyage'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'

    numero = models.CharField(max_length=10, unique=True)
    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, related_name='chambres')
    type_chambre = models.CharField(max_length=50)
    prix_nuit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(
        PRIX_MINIMUM_NUIT, message=f'Le prix minimum par nuit est de {format_ar(PRIX_MINIMUM_NUIT)}.')])
    capacite = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    description = models.TextField(blank=True)
    etage = models.SmallIntegerField(default=0)
    statut = models.CharField(max_length=15, choices=Statut.choices, default=Statut.DISPONIBLE)
    image = models.ImageField(upload_to='chambres/', blank=True, null=True)
    equipements = models.ManyToManyField(Equipement, blank=True, related_name='chambres',
                                         db_table='chambre_equipement')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chambres'
        ordering = ['numero']
        constraints = [
            models.CheckConstraint(condition=models.Q(prix_nuit__gte=PRIX_MINIMUM_NUIT), name='chk_prix'),
            models.CheckConstraint(condition=models.Q(capacite__gt=0), name='chk_capacite'),
        ]
        indexes = [models.Index(fields=['statut'], name='idx_chambre_statut')]

    def __str__(self):
        return f'Chambre {self.numero}'