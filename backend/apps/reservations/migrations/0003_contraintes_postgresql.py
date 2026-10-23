"""Contraintes PostgreSQL : anti double réservation au niveau de la base + contrôles d'intégrité."""
import django.contrib.postgres.constraints
import django.contrib.postgres.fields.ranges
import django.db.models.expressions
from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations, models

import apps.reservations.models


class Migration(migrations.Migration):

    dependencies = [('reservations', '0002_tarification')]

    operations = [
        BtreeGistExtension(),  # permet « chambre = » + « période && » dans une même contrainte d'exclusion
        migrations.AddConstraint(
            model_name='reservation',
            constraint=models.CheckConstraint(condition=models.Q(('montant_total__gt', 0)), name='chk_resa_total_positif'),
        ),
        migrations.AddConstraint(
            model_name='reservation',
            constraint=models.CheckConstraint(condition=models.Q(('nb_adultes__gte', 1)), name='chk_resa_adultes'),
        ),
        migrations.AddConstraint(
            model_name='reservation',
            constraint=django.contrib.postgres.constraints.ExclusionConstraint(
                condition=models.Q(('statut__in', ['EN_ATTENTE', 'CONFIRMEE'])),
                expressions=[
                    ('chambre', '='),
                    (apps.reservations.models.PlageDates('date_arrivee', 'date_depart', models.Value('[)')), '&&'),
                ],
                name='excl_resa_chevauchement',
            ),
        ),
    ]
