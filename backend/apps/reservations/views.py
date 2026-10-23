from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.authentication.models import User
from apps.authentication.permissions import IsAdmin, IsAdminOrReadOnly, IsStaffRole
from apps.chambres.models import Chambre
from apps.clients.services import get_client_profile
from apps.common.mixins import ProtectedDeleteMixin

from .models import Reservation, Service
from .serializers import DevisSerializer, ReservationSerializer, ServiceSerializer


class ServiceViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    """Prestations payantes : lecture publique (services actifs), écriture réservée à l'administrateur."""
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['nom']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger (utilisateur anonyme)
            return Service.objects.none()
        qs = Service.objects.all()
        u = self.request.user
        return qs if (u.is_authenticated and u.role == User.Role.ADMIN) else qs.filter(actif=True)


class ReservationViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    filterset_fields = ['statut', 'chambre', 'client']
    search_fields = ['numero_reservation', 'client__nom', 'client__prenom', 'chambre__numero']
    ordering_fields = ['date_reservation', 'date_arrivee', 'montant_total']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger (utilisateur anonyme)
            return Reservation.objects.none()
        qs = Reservation.objects.select_related('client', 'chambre', 'chambre__categorie').prefetch_related('paiements')
        user = self.request.user
        return qs if user.is_staff_member else qs.filter(client__user=user)

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdmin()]
        if self.action in ('update', 'partial_update', 'confirmer', 'checkin', 'checkout'):
            return [IsStaffRole()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'])
    def devis(self, request):
        """POST /api/reservations/devis/ : récapitulatif de prix calculé par le serveur (aucune écriture)."""
        ser = DevisSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        return Response(ser.validated_data['devis'])

    def perform_create(self, serializer):
        user = self.request.user
        extra = {'cree_par': user}
        if user.role == User.Role.CLIENT:
            extra['client'] = get_client_profile(user)
        serializer.save(**extra)

    def _changer(self, request, pk, attendus, nouveau, msg):
        resa = self.get_object()
        if resa.statut not in attendus:
            raise serializers.ValidationError(msg)
        resa.statut = nouveau
        resa.save(update_fields=['statut'])
        return resa

    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        resa = self.get_object()
        if resa.statut not in Reservation.ACTIVES:
            raise serializers.ValidationError('Cette réservation ne peut plus être annulée.')
        if request.user.role == User.Role.CLIENT:  # RG8 : délai d'annulation pour le client
            debut = timezone.make_aware(datetime.combine(resa.date_arrivee, time.min))
            if debut - timezone.now() < timedelta(hours=settings.CANCEL_DEADLINE_HOURS):
                raise serializers.ValidationError(
                    f"Annulation impossible à moins de {settings.CANCEL_DEADLINE_HOURS} h de l'arrivée. Contactez l'hôtel.")
        resa.statut = Reservation.Statut.ANNULEE
        resa.save(update_fields=['statut'])
        return Response(self.get_serializer(resa).data)

    @action(detail=True, methods=['post'])
    def confirmer(self, request, pk=None):
        resa = self._changer(request, pk, [Reservation.Statut.EN_ATTENTE], Reservation.Statut.CONFIRMEE,
                             'Seule une réservation en attente peut être confirmée.')
        return Response(self.get_serializer(resa).data)

    @action(detail=True, methods=['post'])
    def checkin(self, request, pk=None):
        """Arrivée du client : la chambre devient occupée."""
        resa = self.get_object()
        if resa.statut != Reservation.Statut.CONFIRMEE:
            raise serializers.ValidationError('La réservation doit être confirmée.')
        if resa.date_arrivee > timezone.localdate():
            raise serializers.ValidationError("L'arrivée n'a pas encore eu lieu.")
        Chambre.objects.filter(pk=resa.chambre_id).update(statut=Chambre.Statut.OCCUPEE)
        return Response(self.get_serializer(resa).data)

    @action(detail=True, methods=['post'])
    def checkout(self, request, pk=None):
        """Départ : réservation terminée, chambre en nettoyage."""
        resa = self.get_object()
        if resa.statut != Reservation.Statut.CONFIRMEE or resa.chambre.statut != Chambre.Statut.OCCUPEE:
            raise serializers.ValidationError("Un check-in est nécessaire avant le check-out.")
        resa.statut = Reservation.Statut.TERMINEE
        resa.save(update_fields=['statut'])
        Chambre.objects.filter(pk=resa.chambre_id).update(statut=Chambre.Statut.NETTOYAGE)
        return Response(self.get_serializer(resa).data)
