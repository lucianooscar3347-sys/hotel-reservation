from rest_framework import status
from rest_framework.exceptions import APIException


class Conflit(APIException):
    """HTTP 409 : la requête est valide mais entre en conflit avec l'état actuel (ex. chambre déjà réservée)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Conflit avec l\'état actuel des données.'
    default_code = 'conflict'
