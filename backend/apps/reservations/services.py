"""Logique métier : validation des séjours, disponibilités (vérifiées côté backend)."""
from django.utils import timezone
from rest_framework import serializers

from apps.chambres.models import Chambre
from apps.common.constants import NB_NUITS_MAX, NB_VOYAGEURS_MAX

from .models import Reservation
from .pricing import calculer_devis


def calcul(prix_nuit, arrivee, depart):
    """RG3 (hébergement seul) : nb_nuits = départ - arrivée ; montant = nuits x prix.
    Le montant complet (services, taxes…) vient de pricing.calculer_devis."""
    nuits = (depart - arrivee).days
    return nuits, prix_nuit * nuits


def valider_sejour(chambre, arrivee, depart, adultes, enfants, verifier_passe=True):
    """Règles communes à la création de réservation et au devis. Lève ValidationError (400)."""
    if arrivee is None or depart is None:
        raise serializers.ValidationError('Les dates d\'arrivée et de départ sont obligatoires.')
    if depart <= arrivee:
        raise serializers.ValidationError({'date_depart': "La date de départ doit être postérieure à la date d'arrivée."})
    if verifier_passe and arrivee < timezone.localdate():
        raise serializers.ValidationError({'date_arrivee': "La date d'arrivée ne peut pas être dans le passé."})
    if (depart - arrivee).days > NB_NUITS_MAX:
        raise serializers.ValidationError({'date_depart': f'Un séjour ne peut pas dépasser {NB_NUITS_MAX} nuits.'})
    if chambre.statut == Chambre.Statut.MAINTENANCE:
        raise serializers.ValidationError({'chambre': 'Cette chambre est en maintenance.'})
    if adultes < 1:
        raise serializers.ValidationError({'nb_adultes': 'Au moins un adulte est requis.'})
    if enfants < 0:
        raise serializers.ValidationError({'nb_enfants': 'Le nombre d\'enfants ne peut pas être négatif.'})
    if adultes + enfants > min(chambre.capacite, NB_VOYAGEURS_MAX):
        raise serializers.ValidationError(
            {'nb_adultes': f'Capacité dépassée : {chambre.capacite} personne(s) maximum dans cette chambre.'})


def reservations_en_conflit(chambre_id, arrivee, depart, exclude_id=None):
    """RG6 : deux périodes se chevauchent si A.arrivee < B.depart ET A.depart > B.arrivee."""
    qs = Reservation.objects.filter(chambre_id=chambre_id, statut__in=Reservation.ACTIVES,
                                    date_arrivee__lt=depart, date_depart__gt=arrivee)
    return qs.exclude(pk=exclude_id) if exclude_id else qs


def chambres_disponibles(arrivee, depart, categorie_id=None, personnes=None):
    occupees = Reservation.objects.filter(statut__in=Reservation.ACTIVES, date_arrivee__lt=depart,
                                          date_depart__gt=arrivee).values('chambre_id')
    qs = (Chambre.objects.exclude(statut=Chambre.Statut.MAINTENANCE).exclude(pk__in=occupees)
          .select_related('categorie').prefetch_related('equipements'))
    if categorie_id:
        qs = qs.filter(categorie_id=categorie_id)
    if personnes:
        qs = qs.filter(capacite__gte=personnes)
    return qs


__all__ = ['calcul', 'calculer_devis', 'valider_sejour', 'reservations_en_conflit', 'chambres_disponibles']
