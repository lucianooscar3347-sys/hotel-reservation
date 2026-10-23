from decimal import Decimal

import django.core.validators
from django.db import migrations, models

MINIMUM = Decimal('20000')


def relever_prix(apps, schema_editor):
    """Les chambres sous le minimum (ex. données de démo en dollars) sont relevées à 20 000 Ar,
    sinon la contrainte SQL ne pourrait pas être créée. Les réservations existantes ne sont PAS modifiées."""
    Chambre = apps.get_model('chambres', 'Chambre')
    Chambre.objects.filter(prix_nuit__lt=MINIMUM).update(prix_nuit=MINIMUM)


class Migration(migrations.Migration):

    dependencies = [('chambres', '0001_initial')]

    operations = [
        migrations.RunPython(relever_prix, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name='chambre', name='chk_prix'),
        migrations.AlterField(
            model_name='chambre', name='prix_nuit',
            field=models.DecimalField(decimal_places=2, max_digits=10, validators=[
                django.core.validators.MinValueValidator(MINIMUM, message='Le prix minimum par nuit est de 20 000 Ar.')]),
        ),
        migrations.AddConstraint(
            model_name='chambre',
            constraint=models.CheckConstraint(condition=models.Q(('prix_nuit__gte', MINIMUM)), name='chk_prix'),
        ),
    ]
