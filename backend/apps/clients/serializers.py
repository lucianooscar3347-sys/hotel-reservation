from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.common.validators import (nettoyer, valider_email_domaine, valider_nom, valider_cin,
                                    valider_telephone)

from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    email = serializers.EmailField(max_length=254, validators=[UniqueValidator(
        queryset=Client.objects.all(), lookup='iexact', message='Un client existe déjà avec cette adresse e-mail.')])

    class Meta:
        model = Client
        fields = ['id', 'user', 'nom', 'prenom', 'nom_complet', 'sexe', 'date_naissance', 'adresse', 'telephone',
                  'email', 'numero_piece_identite', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def validate_nom(self, value):
        return valider_nom(value, 'Le nom')

    def validate_prenom(self, value):
        return valider_nom(value, 'Le prénom')

    def validate_email(self, value):
        return valider_email_domaine(value)

    def validate_telephone(self, value):
        return valider_telephone(value)

    def validate_adresse(self, value):
        return nettoyer(value)

    def validate_numero_piece_identite(self, value):
        return valider_cin(value or '')

    def validate_date_naissance(self, value):
        if value:
            today = timezone.localdate()
            if value > today:
                raise serializers.ValidationError('La date de naissance est dans le futur.')
            if (today.year - value.year) > 120:
                raise serializers.ValidationError('Date de naissance invraisemblable.')
        return value
