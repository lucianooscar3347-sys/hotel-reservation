"""Couche d'abstraction du paiement en ligne.

Pour brancher Stripe / Orange Money / MVola : créer une sous-classe de
BasePaymentProvider, implémenter charge() puis la retourner dans get_provider().
"""


class BasePaymentProvider:
    def charge(self, reservation, montant, mode):
        """Retourne {'success': bool, 'transaction_id': str, 'message': str}"""
        raise NotImplementedError


class ManualProvider(BasePaymentProvider):
    """Espèces / virement : encaissement constaté par la réception (réservé au personnel, voir PaiementSerializer)."""

    def charge(self, reservation, montant, mode):
        return {'success': True, 'transaction_id': '', 'message': 'Encaissement enregistré'}


class DisabledProvider(BasePaymentProvider):
    """Paiement en ligne non configuré : refuse, pour qu'un client ne puisse pas se déclarer « payé »."""

    def charge(self, reservation, montant, mode):
        return {'success': False, 'transaction_id': '',
                'message': "Le paiement en ligne n'est pas encore disponible. Réglez à la réception."}


class SimulatedProvider(BasePaymentProvider):
    """Paiement simulé (développement / projet universitaire) : toujours accepté."""

    def charge(self, reservation, montant, mode):
        return {'success': True, 'transaction_id': f'SIM-{reservation.pk}', 'message': 'Paiement simulé accepté'}


def get_provider(mode):
    from django.conf import settings
    if mode in ('ESPECES', 'VIREMENT'):
        return ManualProvider()
    return SimulatedProvider() if getattr(settings, 'PAIEMENT_SIMULE', False) else DisabledProvider()
