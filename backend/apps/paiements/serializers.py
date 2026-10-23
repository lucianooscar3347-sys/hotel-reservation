from django.db import transaction
from rest_framework import serializers

from apps.authentication.models import User
from apps.reservations.models import Reservation

from .models import Paiement
from .providers import get_provider


class PaiementSerializer(serializers.ModelSerializer):
    reservation_numero = serializers.CharField(source='reservation.numero_reservation', read_only=True)

    class Meta:
        model = Paiement
        fields = ['id', 'reference', 'reservation', 'reservation_numero', 'montant', 'date_paiement',
                  'mode_paiement', 'statut']
        read_only_fields = ['reference', 'date_paiement', 'statut']

    def validate_montant(self, value):
        if value <= 0:
            raise serializers.ValidationError('Le montant doit être positif.')
        return value

    def validate_mode_paiement(self, value):
        user = self.context['request'].user
        if user.role == User.Role.CLIENT and value in (Paiement.Mode.ESPECES, Paiement.Mode.VIREMENT):
            raise serializers.ValidationError('Ce mode de paiement est enregistré par la réception.')
        return value

    def validate_reservation(self, resa):
        user = self.context['request'].user
        if user.role == User.Role.CLIENT and resa.client.user_id != user.id:
            raise serializers.ValidationError('Réservation introuvable.')
        if resa.statut == Reservation.Statut.ANNULEE:
            raise serializers.ValidationError('Réservation annulée : paiement impossible.')
        return resa

    @transaction.atomic
    def create(self, vd):
        resa = Reservation.objects.select_for_update().get(pk=vd['reservation'].pk)
        reste = resa.reste_a_payer
        if vd['montant'] > reste:
            raise serializers.ValidationError({'montant': f'Le montant dépasse le reste à payer ({reste}).'})
        result = get_provider(vd['mode_paiement']).charge(resa, vd['montant'], vd['mode_paiement'])
        if not result['success']:
            raise serializers.ValidationError(result.get('message', 'Paiement refusé.'))
        # RG11 : payé si cumul >= total, sinon partiellement payé
        vd['statut'] = Paiement.Statut.PAYE if resa.montant_paye + vd['montant'] >= resa.montant_total \
            else Paiement.Statut.PARTIEL
        return super().create(vd)
