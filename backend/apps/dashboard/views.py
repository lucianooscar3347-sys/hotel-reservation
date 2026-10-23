from datetime import date

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import User
from apps.chambres.models import Categorie, Chambre
from apps.clients.models import Client
from apps.paiements.models import Paiement
from apps.reservations.models import Reservation
from apps.reservations.serializers import ReservationSerializer


def _derniers_mois(n=12):
    today = timezone.localdate()
    y, m = today.year, today.month
    mois = []
    for _ in range(n):
        mois.append(date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return mois[::-1]


def _serie(qs, key, mois):
    data = {row['m'].strftime('%Y-%m'): row['v'] for row in qs}
    return [{'mois': d.strftime('%Y-%m'), 'valeur': float(data.get(d.strftime('%Y-%m'), 0) or 0)} for d in mois]


class DashboardView(APIView):
    """GET /api/dashboard/ : statistiques (personnel) ou résumé personnel (client)."""

    @extend_schema(responses={200: dict})
    def get(self, request):
        user = request.user
        if not user.is_staff_member:
            qs = Reservation.objects.filter(client__user=user)
            return Response({
                'role': User.Role.CLIENT,
                'mes_reservations': qs.count(),
                'en_attente': qs.filter(statut='EN_ATTENTE').count(),
                'confirmees': qs.filter(statut='CONFIRMEE').count(),
                'total_paye': float(Paiement.objects.filter(reservation__client__user=user, statut__in=['PAYE', 'PARTIEL'])
                                    .aggregate(s=Sum('montant'))['s'] or 0),
            })

        today = timezone.localdate()
        total = Chambre.objects.count()
        maintenance = Chambre.objects.filter(statut='MAINTENANCE').count()
        occupees = Chambre.objects.filter(statut='OCCUPEE').count()
        reservees = (Reservation.objects.filter(statut__in=Reservation.ACTIVES, date_arrivee__lte=today, date_depart__gt=today)
                     .exclude(chambre__statut='OCCUPEE').values('chambre').distinct().count())
        nettoyage = Chambre.objects.filter(statut='NETTOYAGE').count()
        disponibles = max(total - occupees - reservees - maintenance - nettoyage, 0)
        exploitables = total - maintenance
        mois = _derniers_mois()
        debut = mois[0]
        paiements = Paiement.objects.filter(statut__in=['PAYE', 'PARTIEL'])

        resa_mois = (Reservation.objects.filter(date_arrivee__gte=debut).exclude(statut='ANNULEE')
                     .annotate(m=TruncMonth('date_arrivee')).values('m').annotate(v=Count('id')))
        rev_mois = (paiements.filter(date_paiement__date__gte=debut).annotate(m=TruncMonth('date_paiement'))
                    .values('m').annotate(v=Sum('montant')))
        repartition = Categorie.objects.annotate(v=Count('chambres')).values('nom', 'v')
        dernieres = Reservation.objects.select_related('client', 'chambre')[:5]

        return Response({
            'role': user.role,
            'total_chambres': total,
            'chambres_disponibles': disponibles,
            'chambres_occupees': occupees,
            'chambres_reservees': reservees,
            'total_clients': Client.objects.count(),
            'total_reservations': Reservation.objects.count(),
            'reservations_en_attente': Reservation.objects.filter(statut='EN_ATTENTE').count(),
            'chiffre_affaires': float(paiements.aggregate(s=Sum('montant'))['s'] or 0),
            'taux_occupation': round(occupees * 100 / exploitables, 1) if exploitables else 0,
            'reservations_par_mois': _serie(resa_mois, 'v', mois),
            'revenus_par_mois': _serie(rev_mois, 'v', mois),
            'repartition_types': [{'nom': r['nom'], 'valeur': r['v']} for r in repartition],
            'dernieres_reservations': ReservationSerializer(dernieres, many=True, context={'request': request}).data,
        })
