from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Func, Sum

from apps.common.utils import generate_code


class PlageDates(Func):
    """daterange(arrivee, depart, '[)') : la nuit du départ n'est pas occupée (départ et arrivée le même jour OK)."""
    function = 'DATERANGE'
    output_field = DateRangeField()


class Service(models.Model):
    """Prestation payante réellement proposée (petit-déjeuner, transfert…). Seuls les services actifs sont facturables."""

    class Mode(models.TextChoices):
        SEJOUR = 'SEJOUR', 'Par séjour'
        NUIT = 'NUIT', 'Par nuit'
        PERSONNE = 'PERSONNE', 'Par personne'
        PERSONNE_NUIT = 'PERSONNE_NUIT', 'Par personne et par nuit'

    nom = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=255, blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    mode = models.CharField(max_length=15, choices=Mode.choices, default=Mode.SEJOUR)
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = 'services'
        ordering = ['nom']
        constraints = [models.CheckConstraint(condition=models.Q(prix__gt=0), name='chk_service_prix')]

    def __str__(self):
        return self.nom


class Reservation(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        CONFIRMEE = 'CONFIRMEE', 'Confirmée'
        ANNULEE = 'ANNULEE', 'Annulée'
        TERMINEE = 'TERMINEE', 'Terminée'

    ACTIVES = (Statut.EN_ATTENTE, Statut.CONFIRMEE)  # statuts qui bloquent la chambre

    numero_reservation = models.CharField(max_length=20, unique=True, editable=False)
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, related_name='reservations')
    chambre = models.ForeignKey('chambres.Chambre', on_delete=models.PROTECT, related_name='reservations')
    cree_par = models.ForeignKey('authentication.User', null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='+')
    date_arrivee = models.DateField()
    date_depart = models.DateField()
    nb_adultes = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    nb_enfants = models.PositiveSmallIntegerField(default=0)
    prix_nuit = models.DecimalField(max_digits=10, decimal_places=2)  # prix figé (RG4)
    nb_nuits = models.PositiveSmallIntegerField()
    montant_total = models.DecimalField(max_digits=12, decimal_places=2)
    # Détail figé du calcul (historique cohérent même si les tarifs changent ensuite)
    hebergement_montant = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    services_montant = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reduction_montant = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxes_montant = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)
    date_reservation = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reservations'
        ordering = ['-date_reservation']
        constraints = [
            models.CheckConstraint(condition=models.Q(date_depart__gt=models.F('date_arrivee')), name='chk_dates'),
            models.CheckConstraint(condition=models.Q(montant_total__gt=0), name='chk_resa_total_positif'),
            models.CheckConstraint(condition=models.Q(nb_adultes__gte=1), name='chk_resa_adultes'),
            # Dernier rempart anti double réservation (indépendant du code Python) : deux réservations ACTIVES
            # de la même chambre ne peuvent pas avoir des périodes qui se chevauchent. Nécessite btree_gist.
            ExclusionConstraint(
                name='excl_resa_chevauchement',
                expressions=[('chambre', RangeOperators.EQUAL),
                             (PlageDates('date_arrivee', 'date_depart', models.Value('[)')), RangeOperators.OVERLAPS)],
                condition=models.Q(statut__in=['EN_ATTENTE', 'CONFIRMEE']),
            ),
        ]
        indexes = [
            models.Index(fields=['chambre', 'date_arrivee', 'date_depart'], name='idx_resa_overlap'),
            models.Index(fields=['statut'], name='idx_resa_statut'),
        ]

    def save(self, *args, **kwargs):
        if not self.numero_reservation:
            self.numero_reservation = generate_code('RES')
        super().save(*args, **kwargs)

    @property
    def montant_paye(self):
        total = self.paiements.filter(statut__in=['PAYE', 'PARTIEL']).aggregate(s=Sum('montant'))['s']
        return total or 0

    @property
    def reste_a_payer(self):
        return max(self.montant_total - self.montant_paye, 0)

    def __str__(self):
        return self.numero_reservation


class LigneService(models.Model):
    """Service choisi pour une réservation, avec le prix du moment (copie figée)."""
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='lignes_services')
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    nom = models.CharField(max_length=80)
    mode = models.CharField(max_length=15, choices=Service.Mode.choices)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    quantite = models.PositiveSmallIntegerField(default=1)
    montant = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'reservation_services'
        ordering = ['id']
