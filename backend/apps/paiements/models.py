from django.db import models
from django.utils import timezone

from apps.common.utils import generate_code


class Paiement(models.Model):
    class Mode(models.TextChoices):
        ESPECES = 'ESPECES', 'Espèces'
        CARTE = 'CARTE', 'Carte bancaire'
        MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile Money'
        VIREMENT = 'VIREMENT', 'Virement'

    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        PAYE = 'PAYE', 'Payé'
        PARTIEL = 'PARTIEL', 'Partiellement payé'
        REMBOURSE = 'REMBOURSE', 'Remboursé'

    reference = models.CharField(max_length=30, unique=True, editable=False)
    reservation = models.ForeignKey('reservations.Reservation', on_delete=models.PROTECT, related_name='paiements')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date_paiement = models.DateTimeField(default=timezone.now)
    mode_paiement = models.CharField(max_length=15, choices=Mode.choices)
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)

    class Meta:
        db_table = 'paiements'
        ordering = ['-date_paiement']
        constraints = [models.CheckConstraint(condition=models.Q(montant__gt=0), name='chk_montant')]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_code('PAY')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.reference