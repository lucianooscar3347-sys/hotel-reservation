"""Tests propres à PostgreSQL : contrainte d'exclusion, concurrence réelle, fuseau horaire, intégrité."""
import threading
from datetime import date, timedelta
from decimal import Decimal

from django.db import IntegrityError, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.chambres.models import Chambre
from apps.common.testing import make_chambre, make_client, make_user
from apps.reservations.models import Reservation


def creer(client, chambre, a, b, statut='CONFIRMEE'):
    return Reservation.objects.create(
        client=client, chambre=chambre, date_arrivee=a, date_depart=b, prix_nuit=chambre.prix_nuit,
        nb_nuits=(b - a).days, hebergement_montant=chambre.prix_nuit * (b - a).days,
        montant_total=chambre.prix_nuit * (b - a).days, statut=statut)


class ContrainteBaseTests(TestCase):
    """La BASE refuse le chevauchement même si le code Python est contourné (ORM direct, script, SQL manuel)."""

    def setUp(self):
        self.cl, self.ch = make_client(), make_chambre()
        self.d = date(2030, 6, 10)

    def test_overlap_rejected_by_database(self):
        creer(self.cl, self.ch, self.d, self.d + timedelta(days=5))
        with self.assertRaises(IntegrityError), transaction.atomic():
            creer(self.cl, self.ch, self.d + timedelta(days=2), self.d + timedelta(days=4))

    def test_same_day_turnover_and_other_room_allowed(self):
        creer(self.cl, self.ch, self.d, self.d + timedelta(days=5))
        creer(self.cl, self.ch, self.d + timedelta(days=5), self.d + timedelta(days=7))  # départ = arrivée suivante
        creer(self.cl, make_chambre(), self.d, self.d + timedelta(days=5))               # autre chambre

    def test_cancelled_does_not_block_and_cannot_be_reactivated_over_active(self):
        r = creer(self.cl, self.ch, self.d, self.d + timedelta(days=3), statut='ANNULEE')
        creer(self.cl, self.ch, self.d, self.d + timedelta(days=3))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reservation.objects.filter(pk=r.pk).update(statut='EN_ATTENTE')

    def test_check_constraints(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            creer(self.cl, self.ch, self.d, self.d)                                   # départ = arrivée
        with self.assertRaises(IntegrityError), transaction.atomic():
            Chambre.objects.filter(pk=self.ch.pk).update(prix_nuit=Decimal('19999'))  # < 20 000 Ar
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reservation.objects.create(client=self.cl, chambre=self.ch, date_arrivee=self.d,
                                       date_depart=self.d + timedelta(days=1), prix_nuit=25000, nb_nuits=1,
                                       montant_total=0)                                # total nul

    def test_email_unique_case_insensitive(self):
        make_user(email='Jean@Test.com')
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_user(email='jean@test.com')

    def test_money_columns_are_numeric(self):
        with connection.cursor() as c:
            c.execute("SELECT data_type FROM information_schema.columns "
                      "WHERE table_name='reservations' AND column_name IN ('montant_total','prix_nuit')")
            self.assertEqual({r[0] for r in c.fetchall()}, {'numeric'})


class FuseauHoraireTests(TestCase):
    def test_hotel_timezone_is_madagascar(self):
        from django.conf import settings
        self.assertEqual(settings.TIME_ZONE, 'Indian/Antananarivo')
        self.assertEqual(timezone.localtime().utcoffset(), timedelta(hours=3))

    def test_arrival_today_in_hotel_timezone_is_accepted(self):
        user = make_user(); make_client(user); ch = make_chambre()
        api = APIClient(); api.force_authenticate(user)
        today = timezone.localdate()
        r = api.post('/api/reservations/', {'chambre': ch.id, 'date_arrivee': str(today),
                                            'date_depart': str(today + timedelta(days=1)), 'nb_adultes': 1})
        self.assertEqual(r.status_code, 201, r.data)
        r = api.post('/api/reservations/', {'chambre': ch.id, 'date_arrivee': str(today - timedelta(days=1)),
                                            'date_depart': str(today + timedelta(days=3)), 'nb_adultes': 1})
        self.assertEqual(r.status_code, 400)


class ConcurrenceTests(TransactionTestCase):
    """Vraies connexions PostgreSQL simultanées : une seule réservation doit aboutir."""

    N = 8

    def _course(self, user_ids, chambre_id, a, b):
        resultats, barriere = [], threading.Barrier(self.N)

        def tache(uid):
            try:
                from apps.authentication.models import User
                api = APIClient(); api.force_authenticate(User.objects.get(pk=uid))
                barriere.wait(timeout=10)
                r = api.post('/api/reservations/', {'chambre': chambre_id, 'date_arrivee': str(a), 'date_depart': str(b),
                                                    'nb_adultes': 1})
                resultats.append(r.status_code)
            except Exception as e:  # pragma: no cover
                resultats.append(repr(e))
            finally:
                connections.close_all()

        ths = [threading.Thread(target=tache, args=(u,)) for u in user_ids]
        [t.start() for t in ths]; [t.join(30) for t in ths]
        return resultats

    def test_simultaneous_bookings_same_room_only_one_wins(self):
        ch = make_chambre()
        users = []
        for _ in range(self.N):
            u = make_user(); make_client(u); users.append(u.pk)
        a = timezone.localdate() + timedelta(days=20)
        res = self._course(users, ch.pk, a, a + timedelta(days=3))
        self.assertEqual(sorted(res), [201] + [409] * (self.N - 1), res)
        self.assertEqual(Reservation.objects.filter(chambre=ch).count(), 1)

    def test_simultaneous_bookings_different_rooms_all_succeed(self):
        users, chambres = [], [make_chambre() for _ in range(self.N)]
        for _ in range(self.N):
            u = make_user(); make_client(u); users.append(u.pk)
        a = timezone.localdate() + timedelta(days=20)
        resultats, barriere = [], threading.Barrier(self.N)

        def tache(uid, cid):
            try:
                from apps.authentication.models import User
                api = APIClient(); api.force_authenticate(User.objects.get(pk=uid))
                barriere.wait(timeout=10)
                resultats.append(api.post('/api/reservations/', {
                    'chambre': cid, 'date_arrivee': str(a), 'date_depart': str(a + timedelta(days=2)),
                    'nb_adultes': 1}).status_code)
            finally:
                connections.close_all()

        ths = [threading.Thread(target=tache, args=(u, c.pk)) for u, c in zip(users, chambres)]
        [t.start() for t in ths]; [t.join(30) for t in ths]
        self.assertEqual(resultats, [201] * self.N)
