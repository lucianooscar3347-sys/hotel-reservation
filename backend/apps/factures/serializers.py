from rest_framework import serializers

from apps.authentication.models import User
from apps.reservations.models import Reservation

from .models import Facture


class FactureSerializer(serializers.ModelSerializer):
    reservation_numero = serializers.CharField(source='reservation.numero_reservation', read_only=True)
    client_nom = serializers.CharField(source='reservation.client.nom_complet', read_only=True)
    chambre_numero = serializers.CharField(source='reservation.chambre.numero', read_only=True)
    date_arrivee = serializers.DateField(source='reservation.date_arrivee', read_only=True)
    date_depart = serializers.DateField(source='reservation.date_depart', read_only=True)
    nb_nuits = serializers.IntegerField(source='reservation.nb_nuits', read_only=True)
    prix_nuit = serializers.DecimalField(source='reservation.prix_nuit', max_digits=10, decimal_places=2, read_only=True)
    montant_paye = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Facture
        fields = ['id', 'numero_facture', 'reservation', 'reservation_numero', 'client_nom', 'chambre_numero',
                  'date_arrivee', 'date_depart', 'nb_nuits', 'prix_nuit', 'montant_total', 'montant_paye', 'date_emission']
        read_only_fields = ['numero_facture', 'montant_total', 'date_emission']

    def validate_reservation(self, resa):
        user = self.context['request'].user
        if user.role == User.Role.CLIENT and resa.client.user_id != user.id:
            raise serializers.ValidationError('Réservation introuvable.')
        if resa.statut not in (Reservation.Statut.CONFIRMEE, Reservation.Statut.TERMINEE):  # RG10
            raise serializers.ValidationError('Facture possible uniquement pour une réservation confirmée ou terminée.')
        if Facture.objects.filter(reservation=resa).exists():
            raise serializers.ValidationError('Une facture existe déjà pour cette réservation.')
        return resa

    def create(self, vd):
        vd['montant_total'] = vd['reservation'].montant_total
        return super().create(vd)
