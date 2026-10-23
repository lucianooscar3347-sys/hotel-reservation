from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.authentication.permissions import IsAdmin

from .models import Paiement
from .serializers import PaiementSerializer


class PaiementViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = PaiementSerializer
    filterset_fields = ['statut', 'mode_paiement', 'reservation']
    search_fields = ['reference', 'reservation__numero_reservation', 'reservation__client__nom']
    ordering_fields = ['date_paiement', 'montant']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger (utilisateur anonyme)
            return Paiement.objects.none()
        qs = Paiement.objects.select_related('reservation', 'reservation__client')
        user = self.request.user
        return qs if user.is_staff_member else qs.filter(reservation__client__user=user)

    def get_permissions(self):
        if self.action in ('destroy', 'rembourser'):
            return [IsAdmin()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def rembourser(self, request, pk=None):
        paiement = self.get_object()
        if paiement.statut == Paiement.Statut.REMBOURSE:
            raise serializers.ValidationError('Déjà remboursé.')
        paiement.statut = Paiement.Statut.REMBOURSE
        paiement.save(update_fields=['statut'])
        return Response(self.get_serializer(paiement).data)
