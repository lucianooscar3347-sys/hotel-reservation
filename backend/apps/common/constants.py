"""Constantes métier partagées (une seule source de vérité)."""
from decimal import Decimal

# Tarif d'hébergement minimum PAR NUIT, en ariary. Doit rester identique à la contrainte SQL `chk_prix`
# (migration chambres/0002) et à PRIX_MINIMUM_NUIT dans frontend/src/services/api.js.
PRIX_MINIMUM_NUIT = Decimal('20000')
NB_VOYAGEURS_MAX = 20
NB_NUITS_MAX = 60
