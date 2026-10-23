from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class Client(models.Model):
    class Sexe(models.TextChoices):
        M = 'M', 'Masculin'
        F = 'F', 'Féminin'

    # Un client peut exister sans compte (client de passage enregistré à l'accueil)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='client_profile')
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    sexe = models.CharField(max_length=1, choices=Sexe.choices, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    telephone = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    numero_piece_identite = models.CharField(max_length=50, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clients'
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(Lower('email'), name='uq_clients_email_ci')]

    @property
    def nom_complet(self):
        return f'{self.prenom} {self.nom}'

    def __str__(self):
        return self.nom_complet
