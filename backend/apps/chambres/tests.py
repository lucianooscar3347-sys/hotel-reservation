from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.chambres.models import Categorie, Chambre
from apps.common.testing import make_chambre, make_user


class ChambreTests(APITestCase):
    def setUp(self):
        self.cat = Categorie.objects.create(nom='Suite')
        self.data = {'numero': '501', 'categorie': self.cat.id, 'type_chambre': 'Vue mer', 'prix_nuit': '45000.00',
                     'capacite': 3, 'etage': 5}

    def test_public_can_list(self):
        make_chambre()
        self.assertEqual(self.client.get('/api/chambres/').status_code, 200)

    def test_admin_crud(self):
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        r = self.client.post('/api/chambres/', self.data)
        self.assertEqual(r.status_code, 201)
        pk = r.data['id']
        self.assertEqual(self.client.patch(f'/api/chambres/{pk}/', {'prix_nuit': '60000.00'}).status_code, 200)
        self.assertEqual(Chambre.objects.get(pk=pk).prix_nuit, 60000)
        self.assertEqual(self.client.delete(f'/api/chambres/{pk}/').status_code, 204)

    def test_non_admin_forbidden(self):
        for role in (User.Role.RECEPTIONNISTE, User.Role.CLIENT):
            self.client.force_authenticate(make_user(role))
            self.assertEqual(self.client.post('/api/chambres/', self.data).status_code, 403)

    def test_validation_unique_number_price_capacity(self):
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        self.client.post('/api/chambres/', self.data)
        self.assertEqual(self.client.post('/api/chambres/', self.data).status_code, 400)
        self.assertEqual(self.client.post('/api/chambres/', {**self.data, 'numero': '502', 'prix_nuit': '-5'}).status_code, 400)
        self.assertEqual(self.client.post('/api/chambres/', {**self.data, 'numero': '503', 'capacite': 0}).status_code, 400)

    def test_minimum_price_20000_per_night(self):
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        for i, prix in enumerate(['19999.99', '19999', '1', '0', '-5', 'abc']):
            r = self.client.post('/api/chambres/', {**self.data, 'numero': f'6{i}', 'prix_nuit': prix})
            self.assertEqual(r.status_code, 400, prix)
            self.assertIn('prix_nuit', r.data)
        self.assertEqual(self.client.post('/api/chambres/', {**self.data, 'numero': '690', 'prix_nuit': '20000'}).status_code, 201)

    def test_minimum_price_enforced_on_update(self):
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        ch = make_chambre()
        self.assertEqual(self.client.patch(f'/api/chambres/{ch.id}/', {'prix_nuit': '15000'}).status_code, 400)
        ch.refresh_from_db()
        self.assertEqual(ch.prix_nuit, Decimal('25000'))

    def test_database_constraint_blocks_price_below_minimum(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_chambre(prix=19999)

    def test_capacity_upper_bound(self):
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        self.assertEqual(self.client.post('/api/chambres/', {**self.data, 'numero': '701', 'capacite': 500}).status_code, 400)
