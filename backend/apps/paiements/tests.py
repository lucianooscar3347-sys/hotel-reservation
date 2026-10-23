from decimal import Decimal

from django.test import override_settings
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.common.testing import make_chambre, make_client, make_reservation, make_user
from apps.factures.models import Facture


@override_settings(PAIEMENT_SIMULE=True)
class PaiementTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.cl = make_client(self.user)
        self.resa = make_reservation(self.cl, make_chambre(prix=25000), nights=2)  # total = 50000
        self.client.force_authenticate(self.user)

    def pay(self, montant, resa=None):
        return self.client.post('/api/paiements/', {'reservation': (resa or self.resa).id, 'montant': montant,
                                                    'mode_paiement': 'CARTE'})

    def test_partial_then_full_payment(self):
        r = self.pay('10000')
        self.assertEqual((r.status_code, r.data['statut']), (201, 'PARTIEL'))
        r = self.pay('40000')
        self.assertEqual((r.status_code, r.data['statut']), (201, 'PAYE'))
        self.assertEqual(self.resa.montant_paye, Decimal('50000'))

    def test_overpayment_and_invalid_amount_rejected(self):
        self.assertEqual(self.pay('60000').status_code, 400)
        self.assertEqual(self.pay('-10').status_code, 400)

    def test_cannot_pay_someone_elses_reservation(self):
        other = make_reservation(make_client(), make_chambre())
        self.assertEqual(self.pay('10', other).status_code, 400)

    def test_refund_admin_only(self):
        pid = self.pay('10000').data['id']
        self.assertEqual(self.client.post(f'/api/paiements/{pid}/rembourser/').status_code, 403)
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        r = self.client.post(f'/api/paiements/{pid}/rembourser/')
        self.assertEqual(r.data['statut'], 'REMBOURSE')
        self.assertEqual(self.resa.montant_paye, 0)

    def test_invoice_only_for_confirmed_and_unique(self):
        pending = make_reservation(self.cl, make_chambre(), start=40, statut='EN_ATTENTE')
        self.assertEqual(self.client.post('/api/factures/', {'reservation': pending.id}).status_code, 400)
        r = self.client.post('/api/factures/', {'reservation': self.resa.id})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.post('/api/factures/', {'reservation': self.resa.id}).status_code, 400)
        pdf = self.client.get(f'/api/factures/{r.data["id"]}/pdf/')
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertEqual(Facture.objects.count(), 1)


@override_settings(PAIEMENT_SIMULE=False)
class PaiementSecuriteTests(APITestCase):
    """Un client ne peut pas se déclarer « payé » : pas de paiement en ligne réel => refus ; espèces = réception."""

    def setUp(self):
        self.user = make_user()
        self.resa = make_reservation(make_client(self.user), make_chambre(prix=25000), nights=2)
        self.client.force_authenticate(self.user)

    def pay(self, mode):
        return self.client.post('/api/paiements/', {'reservation': self.resa.id, 'montant': '10000', 'mode_paiement': mode})

    def test_online_payment_refused_when_not_configured(self):
        self.assertEqual(self.pay('CARTE').status_code, 400)
        self.assertEqual(self.resa.montant_paye, 0)

    def test_client_cannot_record_cash(self):
        self.assertEqual(self.pay('ESPECES').status_code, 400)
        self.assertEqual(self.pay('VIREMENT').status_code, 400)

    def test_staff_can_record_cash(self):
        self.client.force_authenticate(make_user(User.Role.RECEPTIONNISTE))
        r = self.pay('ESPECES')
        self.assertEqual((r.status_code, r.data['statut']), (201, 'PARTIEL'))
