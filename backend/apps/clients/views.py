from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.authentication.permissions import IsAdmin, IsStaffRole
from apps.common.mixins import ProtectedDeleteMixin
from apps.reservations.serializers import ReservationSerializer

from .models import Client
from .serializers import ClientSerializer


class ClientViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    filterset_fields = ['sexe']
    search_fields = ['nom', 'prenom', 'email', 'telephone', 'numero_piece_identite']
    ordering_fields = ['nom', 'created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger (utilisateur anonyme)
            return Client.objects.none()
        qs = Client.objects.all()
        user = self.request.user
        return qs if user.is_staff_member else qs.filter(user=user)  # RG12

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdmin()]
        if self.action == 'create':
            return [IsStaffRole()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['get'])
    def reservations(self, request, pk=None):
        """Historique des réservations d'un client."""
        client = self.get_object()
        qs = client.reservations.select_related('client', 'chambre').order_by('-date_reservation')
        return Response(ReservationSerializer(qs, many=True, context={'request': request}).data)
