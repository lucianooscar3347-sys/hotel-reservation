from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.authentication.permissions import IsAdminOrReadOnly, IsStaffRole
from apps.common.mixins import ProtectedDeleteMixin
from apps.reservations.services import chambres_disponibles

from .models import Categorie, Chambre, Equipement
from .serializers import (CategorieSerializer, ChambreSerializer, DisponibiliteQuerySerializer,
                          EquipementSerializer)


class CategorieViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = Categorie.objects.all()
    serializer_class = CategorieSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['nom']


class EquipementViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = Equipement.objects.all()
    serializer_class = EquipementSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['nom']


class ChambreViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = Chambre.objects.select_related('categorie').prefetch_related('equipements')
    serializer_class = ChambreSerializer
    permission_classes = [IsAdminOrReadOnly]  # lecture publique, écriture admin
    filterset_fields = ['categorie', 'statut', 'etage', 'capacite']
    search_fields = ['numero', 'type_chambre', 'description', 'categorie__nom']
    ordering_fields = ['numero', 'prix_nuit', 'capacite']

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def disponibles(self, request):
        """GET /api/chambres/disponibles/?arrivee=YYYY-MM-DD&depart=YYYY-MM-DD&categorie=1&personnes=2"""
        q = DisponibiliteQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        d = q.validated_data
        qs = chambres_disponibles(d['arrivee'], d['depart'], d.get('categorie'), d.get('personnes'))
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffRole])
    def statut(self, request, pk=None):
        """Le personnel change le statut opérationnel (ex. nettoyage -> disponible)."""
        chambre = self.get_object()
        value = request.data.get('statut')
        if value not in Chambre.Statut.values:
            raise serializers.ValidationError({'statut': 'Statut invalide.'})
        chambre.statut = value
        chambre.save(update_fields=['statut'])
        return Response(self.get_serializer(chambre).data)
