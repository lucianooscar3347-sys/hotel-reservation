"""Moteur de tarification : TOUS les montants sont calculés ici, côté serveur.

total = (prix_nuit x nuits) + services - réduction long séjour + taxes
Le prix d'hébergement par nuit ne peut jamais être inférieur à PRIX_MINIMUM_NUIT (20 000 Ar), réduction comprise.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

from apps.common.constants import PRIX_MINIMUM_NUIT
from apps.common.utils import format_ar

UN = Decimal('1')


class PrixInvalide(Exception):
    """Tarif de base inférieur au minimum autorisé (ou séjour incohérent)."""


def arrondi(x):
    """Ariary : pas de centimes, arrondi commercial."""
    return Decimal(x).quantize(UN, rounding=ROUND_HALF_UP)


def multiplicateur(mode, quantite, nuits, personnes):
    """Nombre d'unités facturées pour un service. `quantite` n'a d'effet que pour les services « par séjour »."""
    if mode == 'SEJOUR':
        return quantite
    if mode == 'NUIT':
        return nuits
    if mode == 'PERSONNE':
        return personnes
    if mode == 'PERSONNE_NUIT':
        return personnes * nuits
    raise PrixInvalide(f'Mode de facturation inconnu : {mode}')


def ligne_depuis_service(service, quantite=1):
    return {'service_id': service.pk, 'nom': service.nom, 'mode': service.mode, 'prix_unitaire': service.prix,
            'quantite': quantite}


def calculer_devis(*, prix_nuit, arrivee, depart, nb_personnes, lignes=()):
    nuits = (depart - arrivee).days
    if nuits < 1:
        raise PrixInvalide("La date de départ doit être postérieure à la date d'arrivée.")
    prix_nuit = Decimal(prix_nuit)
    if prix_nuit < PRIX_MINIMUM_NUIT:
        raise PrixInvalide(f'Le tarif minimum par nuit est de {format_ar(PRIX_MINIMUM_NUIT)} '
                           f'(tarif proposé : {format_ar(prix_nuit)}).')

    hebergement = arrondi(prix_nuit * nuits)

    details = []
    services_total = Decimal(0)
    for l in lignes:
        qte = l['quantite'] if l['mode'] == 'SEJOUR' else 1
        unites = multiplicateur(l['mode'], qte, nuits, nb_personnes)
        montant = arrondi(Decimal(l['prix_unitaire']) * unites)
        services_total += montant
        details.append({**l, 'quantite': qte, 'unites': unites, 'prix_unitaire': arrondi(l['prix_unitaire']),
                        'montant': montant})

    # Réduction long séjour (désactivée par défaut : REDUCTION_LONG_SEJOUR_POURCENT=0), plafonnée pour que le prix
    # d'hébergement par nuit reste >= minimum.
    reduction = Decimal(0)
    pct = Decimal(str(getattr(settings, 'REDUCTION_LONG_SEJOUR_POURCENT', 0)))
    if pct > 0 and nuits >= int(getattr(settings, 'REDUCTION_LONG_SEJOUR_NUITS', 7)):
        reduction = arrondi(hebergement * pct / 100)
        reduction = min(reduction, max(hebergement - PRIX_MINIMUM_NUIT * nuits, Decimal(0)))

    base = hebergement - reduction + services_total

    taxes = []
    taxe_sejour = arrondi(Decimal(str(getattr(settings, 'TAXE_SEJOUR_PAR_PERSONNE_NUIT', 0))) * nb_personnes * nuits)
    if taxe_sejour > 0:
        taxes.append({'libelle': 'Taxe de séjour', 'montant': taxe_sejour})
    tva = arrondi(base * Decimal(str(getattr(settings, 'TAUX_TVA', 0))) / 100)
    if tva > 0:
        taxes.append({'libelle': f"TVA ({getattr(settings, 'TAUX_TVA', 0)} %)", 'montant': tva})
    taxes_total = sum((t['montant'] for t in taxes), Decimal(0))

    return {
        'prix_nuit': arrondi(prix_nuit), 'nb_nuits': nuits, 'nb_personnes': nb_personnes,
        'hebergement_montant': hebergement, 'services': details, 'services_montant': services_total,
        'reduction_montant': reduction, 'taxes': taxes, 'taxes_montant': taxes_total,
        'montant_total': base + taxes_total,
    }


def devis_vers_json(devis):
    """Decimal -> str pour la réponse JSON (même convention que DRF)."""
    def conv(v):
        if isinstance(v, Decimal):
            return format(v.quantize(Decimal('0.01')), 'f')  # « 138000.00 », identique à la réponse d'une réservation
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [conv(x) for x in v]
        return v
    return conv(devis)
