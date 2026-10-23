from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.common.testing import make_client, make_user

PAYLOAD = {'nom': 'Rabe', 'prenom': 'Paul', 'sexe': 'M', 'telephone': '0341234567', 'email': 'paul@x.com',
           'numero_piece_identite': '10120100000009'}


class ClientTests(APITestCase):
    def test_receptionist_creates_client(self):
        self.client.force_authenticate(make_user(User.Role.RECEPTIONNISTE))
        self.assertEqual(self.client.post('/api/clients/', PAYLOAD).status_code, 201)

    def test_duplicate_email_and_bad_phone(self):
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        self.client.post('/api/clients/', PAYLOAD)
        self.assertEqual(self.client.post('/api/clients/', PAYLOAD).status_code, 400)
        self.assertEqual(self.client.post('/api/clients/', {**PAYLOAD, 'email': 'n@x.com', 'telephone': 'abc'}).status_code, 400)

    def test_client_role_cannot_create_or_see_others(self):
        u = make_user()
        mine = make_client(u)
        other = make_client()
        self.client.force_authenticate(u)
        self.assertEqual(self.client.post('/api/clients/', PAYLOAD).status_code, 403)
        ids = [c['id'] for c in self.client.get('/api/clients/').data['results']]
        self.assertEqual(ids, [mine.id])
        self.assertEqual(self.client.get(f'/api/clients/{other.id}/').status_code, 404)

    def test_field_validation_and_normalisation(self):
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        bad = [{'nom': '   '}, {'nom': 'R4be'}, {'prenom': ''}, {'email': 'pas-un-email'}, {'email': 'a@localhost'},
               {'telephone': '+261 34 12'}, {'date_naissance': '2999-01-01'}, {'numero_piece_identite': '!!'}, {'numero_piece_identite': '123456789012'},
               {'numero_piece_identite': '123456789012345'}, {'numero_piece_identite': '1234567890123A'}]
        for i, extra in enumerate(bad):
            data = {**PAYLOAD, 'email': f'v{i}@x.com', 'numero_piece_identite': f'1012010001{i:04d}', **extra}
            self.assertEqual(self.client.post('/api/clients/', data).status_code, 400, extra)
        r = self.client.post('/api/clients/', {**PAYLOAD, 'nom': "  N'Diaye ", 'email': ' Ok@Example.COM ', 'telephone': '034 12 345 67'})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data['nom'], r.data['email'], r.data['telephone']), ("N'Diaye", 'ok@example.com', '0341234567'))

    def test_cin_must_have_exactly_14_digits(self):
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        for i, bad in enumerate(['123456789012', '1234567890123', '123456789012345', '1234567890123A', '1234 5678 9012 34',
                                 'CIN-0001', '١٢٣٤٥٦٧٨٩٠١٢٣٤']):  # 12, 13, 15 chiffres, lettre, espaces, texte, chiffres arabes
            r = self.client.post('/api/clients/', {**PAYLOAD, 'email': f'c{i}@x.com', 'numero_piece_identite': bad})
            self.assertEqual(r.status_code, 400, bad)
            self.assertIn('numero_piece_identite', r.data)
            self.assertIn('14 chiffres', str(r.data['numero_piece_identite']))
        ok = self.client.post('/api/clients/', {**PAYLOAD, 'email': 'ok14@x.com', 'numero_piece_identite': '12345678901234'})
        self.assertEqual(ok.status_code, 201, ok.data)
        self.assertEqual(ok.data['numero_piece_identite'], '12345678901234')

    def test_cin_stays_optional_and_unique(self):
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        for i in range(2):  # plusieurs clients sans CIN : autorisé
            r = self.client.post('/api/clients/', {**PAYLOAD, 'email': f'sans{i}@x.com', 'numero_piece_identite': ''})
            self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.client.post('/api/clients/', {**PAYLOAD, 'email': 'a1@x.com'}).status_code, 201)
        self.assertEqual(self.client.post('/api/clients/', {**PAYLOAD, 'email': 'a2@x.com'}).status_code, 400)  # même CIN
