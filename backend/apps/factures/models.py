from django.db import models
from django.utils import timezone

from apps.common.utils import generate_code


class Facture(models.Model):
    numero_facture = models.CharField(max_length=20, unique=True, editable=False)
    reservation = models.OneToOneField('reservations.Reservation', on_delete=models.PROTECT, related_name='facture')
    date_emission = models.DateTimeField(default=timezone.now)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'factures'
        ordering = ['-date_emission']

    def save(self, *args, **kwargs):
        if not self.numero_facture:
            self.numero_facture = generate_code('FAC')
        super().save(*args, **kwargs)

    @property
    def montant_paye(self):
        return self.reservation.montant_paye

    def __str__(self):
        return self.numero_facture
