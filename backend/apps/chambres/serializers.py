from rest_framework import serializers

from apps.common.constants import NB_VOYAGEURS_MAX, PRIX_MINIMUM_NUIT
from apps.common.utils import format_ar

from .models import Categorie, Chambre, Equipement


class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = ['id', 'nom', 'description']


class EquipementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipement
        fields = ['id', 'nom', 'icone']


class ChambreSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    equipements_detail = EquipementSerializer(source='equipements', many=True, read_only=True)
    equipements = serializers.PrimaryKeyRelatedField(many=True, queryset=Equipement.objects.all(), required=False)

    class Meta:
        model = Chambre
        fields = ['id', 'numero', 'categorie', 'categorie_nom', 'type_chambre', 'prix_nuit', 'capacite',
                  'description', 'etage', 'statut', 'image', 'equipements', 'equipements_detail']

    def validate_prix_nuit(self, value):
        if value < PRIX_MINIMUM_NUIT:
            raise serializers.ValidationError(
                f'Le prix minimum par nuit est de {format_ar(PRIX_MINIMUM_NUIT)} (tarif saisi : {format_ar(value)}).')
        return value

    def validate_numero(self, value):
        value = ' '.join(value.split())
        if not value:
            raise serializers.ValidationError('Le numéro de chambre est obligatoire.')
        return value

    def validate_type_chambre(self, value):
        value = ' '.join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError('Le type de chambre est obligatoire.')
        return value

    def validate_capacite(self, value):
        if value <= 0:
            raise serializers.ValidationError('La capacité doit être positive.')
        if value > NB_VOYAGEURS_MAX:
            raise serializers.ValidationError(f'La capacité ne peut pas dépasser {NB_VOYAGEURS_MAX} personnes.')
        return value


class DisponibiliteQuerySerializer(serializers.Serializer):
    arrivee = serializers.DateField()
    depart = serializers.DateField()
    categorie = serializers.IntegerField(required=False)
    personnes = serializers.IntegerField(required=False, min_value=1, max_value=NB_VOYAGEURS_MAX)

    def validate(self, attrs):
        if attrs['depart'] <= attrs['arrivee']:
            raise serializers.ValidationError({'depart': "La date de départ doit être postérieure à l'arrivée."})
        return attrs
