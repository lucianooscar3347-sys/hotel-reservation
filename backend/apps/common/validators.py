"""Validateurs réutilisables (mêmes règles que frontend/src/lib/validators.js)."""
import re
import unicodedata

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

# Lettres (accentuées incluses), séparées par un espace, une apostrophe ou un trait d'union.
_NOM_RE = re.compile(r"^[^\W\d_]+(?:[ '’\-][^\W\d_]+)*$", re.UNICODE)
_PHONE_LOCAL_MG = re.compile(r'^0\d{9}$')           # 034 12 345 67
_PHONE_INTL = re.compile(r'^\+[1-9]\d{7,14}$')      # E.164
CIN_LONGUEUR = 14
_CIN_RE = re.compile(r'[0-9]{%d}' % CIN_LONGUEUR)  # [0-9] et non \d : refuse les chiffres Unicode (arabes, etc.)


def a_caracteres_controle(value):
    return any(unicodedata.category(c) == 'Cc' for c in value)


def nettoyer(value):
    """Supprime les espaces superflus (début, fin, doublons)."""
    return ' '.join(str(value).split())


def valider_nom(value, libelle='Ce champ'):
    value = nettoyer(value)
    if a_caracteres_controle(value):
        raise serializers.ValidationError('Caractères non autorisés.')
    if len(value) < 2:
        raise serializers.ValidationError(f'{libelle} doit contenir au moins 2 caractères.')
    if len(value) > 100:
        raise serializers.ValidationError(f'{libelle} ne peut pas dépasser 100 caractères.')
    if not _NOM_RE.fullmatch(value):
        raise serializers.ValidationError("Utilisez uniquement des lettres, espaces, apostrophes et traits d'union.")
    return value


def valider_telephone(value):
    """Accepte 034 12 345 67, +261 34 12 345 67, 00261…, +33 6 12 34 56 78. Retourne la forme normalisée."""
    brut = nettoyer(value)
    if a_caracteres_controle(brut):
        raise serializers.ValidationError('Numéro de téléphone invalide.')
    num = re.sub(r'[ .\-()]', '', brut)
    if num.startswith('00'):
        num = '+' + num[2:]
    if _PHONE_LOCAL_MG.fullmatch(num):
        return num
    if _PHONE_INTL.fullmatch(num):
        if num.startswith('+261') and len(num) != 13:
            raise serializers.ValidationError('Un numéro malgache doit contenir 9 chiffres après +261.')
        return num
    raise serializers.ValidationError(
        'Numéro invalide. Exemples : 034 12 345 67 ou +261 34 12 345 67 (indicatif international accepté).')


def valider_email_domaine(value):
    value = nettoyer(value).lower()
    domaine = value.rpartition('@')[2]
    if '.' not in domaine or domaine.startswith('.') or domaine.endswith('.') or '..' in domaine:
        raise serializers.ValidationError('Adresse e-mail invalide.')
    return value


def valider_cin(value):
    """CIN (Carte d'Identité Nationale) : exactement 14 chiffres, sans espace, lettre ni symbole.
    Valeur vide -> None (colonne UNIQUE nullable : plusieurs clients sans CIN restent possibles)."""
    value = nettoyer(value)
    if not value:
        return None
    if not _CIN_RE.fullmatch(value):
        raise serializers.ValidationError(
            f'Le numéro de CIN doit contenir exactement {CIN_LONGUEUR} chiffres (chiffres uniquement, sans espace ni lettre).')
    return value


valider_piece_identite = valider_cin  # ancien nom conservé pour compatibilité


class ComplexitePasswordValidator:
    """Mot de passe : 10 caractères minimum, au moins une lettre et un chiffre."""

    def validate(self, password, user=None):
        if len(password) < 10:
            raise DjangoValidationError('Le mot de passe doit contenir au moins 10 caractères.', code='too_short')
        if len(password) > 128:
            raise DjangoValidationError('Le mot de passe ne peut pas dépasser 128 caractères.', code='too_long')
        if not re.search(r'[^\W\d_]', password) or not re.search(r'\d', password):
            raise DjangoValidationError('Le mot de passe doit contenir au moins une lettre et un chiffre.',
                                        code='no_mix')

    def get_help_text(self):
        return 'Au moins 10 caractères, avec une lettre et un chiffre.'
