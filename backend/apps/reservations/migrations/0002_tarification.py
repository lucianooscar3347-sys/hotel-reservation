import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F


def remplir_hebergement(apps, schema_editor):
    """Anciennes réservations : tout le montant était de l'hébergement (nuits x prix)."""
    Reservation = apps.get_model('reservations', 'Reservation')
    Reservation.objects.update(hebergement_montant=F('montant_total'))


class Migration(migrations.Migration):

    dependencies = [('reservations', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=80, unique=True)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('prix', models.DecimalField(decimal_places=2, max_digits=10)),
                ('mode', models.CharField(choices=[('SEJOUR', 'Par séjour'), ('NUIT', 'Par nuit'), ('PERSONNE', 'Par personne'), ('PERSONNE_NUIT', 'Par personne et par nuit')], default='SEJOUR', max_length=15)),
                ('actif', models.BooleanField(default=True)),
            ],
            options={'db_table': 'services', 'ordering': ['nom'],
                     'constraints': [models.CheckConstraint(condition=models.Q(('prix__gt', 0)), name='chk_service_prix')]},
        ),
        migrations.AddField(model_name='reservation', name='hebergement_montant', field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name='reservation', name='services_montant', field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name='reservation', name='reduction_montant', field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name='reservation', name='taxes_montant', field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.CreateModel(
            name='LigneService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=80)),
                ('mode', models.CharField(choices=[('SEJOUR', 'Par séjour'), ('NUIT', 'Par nuit'), ('PERSONNE', 'Par personne'), ('PERSONNE_NUIT', 'Par personne et par nuit')], max_length=15)),
                ('prix_unitaire', models.DecimalField(decimal_places=2, max_digits=10)),
                ('quantite', models.PositiveSmallIntegerField(default=1)),
                ('montant', models.DecimalField(decimal_places=2, max_digits=12)),
                ('reservation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lignes_services', to='reservations.reservation')),
                ('service', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='reservations.service')),
            ],
            options={'db_table': 'reservation_services', 'ordering': ['id']},
        ),
        migrations.RunPython(remplir_hebergement, migrations.RunPython.noop),
    ]
