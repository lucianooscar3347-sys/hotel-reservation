from django.http import HttpResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.authentication.permissions import IsAdmin

from .models import Facture
from .pdf import build_facture_pdf
from .serializers import FactureSerializer


class FactureViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = FactureSerializer
    search_fields = ['numero_facture', 'reservation__numero_reservation', 'reservation__client__nom']
    ordering_fields = ['date_emission', 'montant_total']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger (utilisateur anonyme)
            return Facture.objects.none()
        qs = Facture.objects.select_related('reservation', 'reservation__client', 'reservation__chambre')
        user = self.request.user
        return qs if user.is_staff_member else qs.filter(reservation__client__user=user)

    def get_permissions(self):
        return [IsAdmin()] if self.action == 'destroy' else [IsAuthenticated()]

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        facture = self.get_object()
        resp = HttpResponse(build_facture_pdf(facture), content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{facture.numero_facture}.pdf"'
        return resp
