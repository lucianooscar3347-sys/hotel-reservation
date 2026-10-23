from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response


class ProtectedDeleteMixin:
    """Renvoie une 400 claire si l'objet est référencé (FK PROTECT)."""

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': "Suppression impossible : cet élément est lié à d'autres données (réservations, paiements...)."},
                status=status.HTTP_400_BAD_REQUEST)
