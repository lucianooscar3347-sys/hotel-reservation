from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.chambres.models import Chambre
from apps.common.testing import make_chambre, make_client, make_reservation, make_service, make_user
from apps.reservations.models import Reservation


def d(n):
    return str(timezone.localdate() + timedelta(days=n))


class ReservationTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.cl = make_client(self.user)
        self.ch = make_chambre(prix=25000, capacite=2)
        self.client.force_authenticate(self.user)

    def book(self, a, b, **extra):
        return self.client.post('/api/reservations/', {'chambre': self.ch.id, 'date_arrivee': d(a), 'date_depart': d(b),
                                                       'nb_adultes': 2, 'nb_enfants': 0, **extra})

    def test_amount_and_nights_calculation(self):
        r = self.book(10, 13)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['nb_nuits'], 3)
        self.assertEqual(Decimal(r.data['montant_total']), Decimal('75000'))
        self.assertEqual(r.data['statut'], 'EN_ATTENTE')

    def test_price_is_frozen(self):
        r = self.book(10, 12)
        self.ch.prix_nuit = Decimal('99999')
        self.ch.save()
        self.assertEqual(Reservation.objects.get(pk=r.data['id']).prix_nuit, 25000)

    def test_double_booking_prevented(self):
        self.assertEqual(self.book(10, 15).status_code, 201)
        self.assertEqual(self.book(12, 14).status_code, 409)  # inclus
        self.assertEqual(self.book(8, 11).status_code, 409)   # chevauche le début
        self.assertEqual(self.book(14, 18).status_code, 409)  # chevauche la fin

    def test_same_day_turnover_allowed(self):
        self.assertEqual(self.book(10, 15).status_code, 201)
        self.assertEqual(self.book(15, 17).status_code, 201)
        self.assertEqual(self.book(8, 10).status_code, 201)

    def test_cancelled_reservation_frees_room(self):
        r = self.book(10, 15)
        Reservation.objects.filter(pk=r.data['id']).update(statut='ANNULEE')
        self.assertEqual(self.book(10, 15).status_code, 201)

    def test_invalid_dates_and_capacity(self):
        self.assertEqual(self.book(5, 5).status_code, 400)
        self.assertEqual(self.book(7, 3).status_code, 400)
        self.assertEqual(self.book(-3, 2).status_code, 400)
        self.assertEqual(self.book(10, 12, nb_adultes=3).status_code, 400)

    def test_maintenance_room_not_bookable(self):
        Chambre.objects.filter(pk=self.ch.pk).update(statut='MAINTENANCE')
        self.assertEqual(self.book(10, 12).status_code, 400)

    def test_availability_endpoint(self):
        self.book(10, 15)
        other = make_chambre()
        r = self.client.get('/api/chambres/disponibles/', {'arrivee': d(11), 'depart': d(13)})
        ids = [c['id'] for c in r.data]
        self.assertNotIn(self.ch.id, ids)
        self.assertIn(other.id, ids)
        r = self.client.get('/api/chambres/disponibles/', {'arrivee': d(15), 'depart': d(16)})
        self.assertIn(self.ch.id, [c['id'] for c in r.data])
        self.assertEqual(self.client.get('/api/chambres/disponibles/', {'arrivee': d(5), 'depart': d(4)}).status_code, 400)

    def test_client_sees_only_own_reservations(self):
        make_reservation(make_client(), make_chambre())
        mine = make_reservation(self.cl, self.ch, start=30)
        ids = [r['id'] for r in self.client.get('/api/reservations/').data['results']]
        self.assertEqual(ids, [mine.id])

    def test_client_cancellation_deadline(self):
        soon = make_reservation(self.cl, self.ch, start=1, statut='CONFIRMEE')
        later = make_reservation(self.cl, make_chambre(), start=10, statut='CONFIRMEE')
        self.assertEqual(self.client.post(f'/api/reservations/{soon.id}/annuler/').status_code, 400)
        self.assertEqual(self.client.post(f'/api/reservations/{later.id}/annuler/').status_code, 200)
        self.client.force_authenticate(make_user(User.Role.RECEPTIONNISTE))  # le personnel peut toujours annuler
        self.assertEqual(self.client.post(f'/api/reservations/{soon.id}/annuler/').status_code, 200)

    def test_staff_workflow_confirm_checkin_checkout(self):
        resa = make_reservation(self.cl, self.ch, start=0, statut='EN_ATTENTE')
        self.client.force_authenticate(make_user(User.Role.RECEPTIONNISTE))
        self.assertEqual(self.client.post(f'/api/reservations/{resa.id}/confirmer/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/reservations/{resa.id}/checkout/').status_code, 400)
        self.assertEqual(self.client.post(f'/api/reservations/{resa.id}/checkin/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/reservations/{resa.id}/checkout/').status_code, 200)
        self.ch.refresh_from_db()
        self.assertEqual(self.ch.statut, 'NETTOYAGE')

    def test_client_cannot_confirm_or_delete(self):
        resa = make_reservation(self.cl, self.ch, statut='EN_ATTENTE')
        self.assertEqual(self.client.post(f'/api/reservations/{resa.id}/confirmer/').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/reservations/{resa.id}/').status_code, 403)


class TarificationApiTests(APITestCase):
    """Calcul serveur, services, minimum et tentatives de fraude."""

    def setUp(self):
        self.user = make_user()
        self.cl = make_client(self.user)
        self.ch = make_chambre(prix=30000, capacite=3)
        self.client.force_authenticate(self.user)
        self.pdj = make_service('Petit-déjeuner', 8000, 'PERSONNE_NUIT')
        self.transfert = make_service('Transfert', 40000, 'SEJOUR')
        self.base = {'chambre': self.ch.id, 'date_arrivee': d(10), 'date_depart': d(13), 'nb_adultes': 2, 'nb_enfants': 0}

    def post(self, **extra):
        return self.client.post('/api/reservations/', {**self.base, **extra}, format='json')

    def test_total_with_services(self):
        r = self.post(services_demandes=[{'service': self.pdj.id}, {'service': self.transfert.id, 'quantite': 2}])
        self.assertEqual(r.status_code, 201, r.data)
        # hébergement 30000x3 = 90000 ; petit-déj 8000x2 pers.x3 nuits = 48000 ; transfert 40000x2 = 80000
        self.assertEqual(Decimal(r.data['hebergement_montant']), Decimal('90000'))
        self.assertEqual(Decimal(r.data['services_montant']), Decimal('128000'))
        self.assertEqual(Decimal(r.data['montant_total']), Decimal('218000'))
        self.assertEqual(len(r.data['lignes']), 2)

    def test_quote_matches_booking(self):
        body = {**self.base, 'services_demandes': [{'service': self.pdj.id}]}
        q = self.client.post('/api/reservations/devis/', body, format='json')
        self.assertEqual(q.status_code, 200, q.data)
        r = self.post(services_demandes=[{'service': self.pdj.id}], montant_attendu=q.data['montant_total'])
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['montant_total'], q.data['montant_total'])

    def test_quote_requires_authentication_and_valid_dates(self):
        self.assertEqual(self.client.post('/api/reservations/devis/', {**self.base, 'date_depart': d(10)}, format='json').status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/reservations/devis/', self.base, format='json').status_code, 401)

    def test_client_cannot_impose_price(self):
        for champ, valeur in [('montant_total', '20000'), ('prix_nuit', '20000'), ('nb_nuits', 1), ('taxes_montant', '0.01')]:
            r = self.post(**{champ: valeur})
            self.assertEqual(r.status_code, 400, champ)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_stale_expected_amount_rejected(self):
        r = self.post(montant_attendu='1000')
        self.assertEqual(r.status_code, 400)
        self.assertIn('montant_attendu', r.data)

    def test_price_comes_from_database_not_from_client(self):
        r = self.post(prix_nuit='30000')  # valeur identique au calcul serveur : acceptée, mais jamais utilisée
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Decimal(r.data['prix_nuit']), Decimal('30000'))

    def test_inactive_unknown_and_duplicate_services_rejected(self):
        off = make_service('Ancien service', 5000, actif=False)
        self.assertEqual(self.post(services_demandes=[{'service': off.id}]).status_code, 400)
        self.assertEqual(self.post(services_demandes=[{'service': 999999}]).status_code, 400)
        self.assertEqual(self.post(services_demandes=[{'service': self.pdj.id}, {'service': self.pdj.id}]).status_code, 400)
        self.assertEqual(self.post(services_demandes=[{'service': self.pdj.id, 'quantite': 0}]).status_code, 400)

    def test_repeated_submission_creates_single_reservation(self):
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 409)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_invalid_numbers_rejected(self):
        for extra in ({'nb_adultes': 0}, {'nb_adultes': -1}, {'nb_adultes': 'abc'}, {'nb_enfants': -2},
                      {'nb_adultes': 2, 'nb_enfants': 5}, {'nb_adultes': 1000}):
            self.assertEqual(self.post(**extra).status_code, 400, extra)

    def test_too_long_stay_rejected(self):
        self.assertEqual(self.post(date_depart=d(200)).status_code, 400)

    def test_service_price_change_does_not_alter_existing_reservation(self):
        r = self.post(services_demandes=[{'service': self.transfert.id}])
        self.transfert.prix = Decimal('90000')
        self.transfert.save()
        resa = Reservation.objects.get(pk=r.data['id'])
        self.assertEqual(resa.lignes_services.get().prix_unitaire, Decimal('40000'))
        self.assertEqual(resa.montant_total, Decimal('130000'))

    def test_services_endpoint_hides_inactive_for_clients(self):
        make_service('Caché', 5000, actif=False)
        noms = [s['nom'] for s in self.client.get('/api/services/', {'page_size': 100}).data['results']]
        self.assertIn('Petit-déjeuner', noms)
        self.assertNotIn('Caché', noms)

    def test_only_admin_writes_services(self):
        data = {'nom': 'Spa', 'prix': '30000', 'mode': 'PERSONNE'}
        self.assertEqual(self.client.post('/api/services/', data).status_code, 403)
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        self.assertEqual(self.client.post('/api/services/', data).status_code, 201)
        self.assertEqual(self.client.post('/api/services/', {**data, 'nom': 'Spa 2', 'prix': '0'}).status_code, 400)

    def test_other_users_reservation_is_invisible_and_not_editable(self):
        autre = make_reservation(make_client(make_user()), make_chambre())
        self.assertEqual(self.client.get(f'/api/reservations/{autre.id}/').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/reservations/{autre.id}/', {'nb_enfants': 1}).status_code, 403)
        self.assertEqual(self.client.post(f'/api/reservations/{autre.id}/annuler/').status_code, 404)

    def test_staff_edit_recomputes_total_and_keeps_services(self):
        r = self.post(services_demandes=[{'service': self.transfert.id}])
        staff = make_user(User.Role.RECEPTIONNISTE)
        self.client.force_authenticate(staff)
        r2 = self.client.patch(f"/api/reservations/{r.data['id']}/", {'date_depart': d(14)}, format='json')
        self.assertEqual(r2.status_code, 200, r2.data)
        self.assertEqual(Decimal(r2.data['montant_total']), Decimal('30000') * 4 + Decimal('40000'))
        self.assertEqual(len(r2.data['lignes']), 1)
