from django.core.cache import cache
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.common.testing import PWD, make_client, make_user


class AuthTests(APITestCase):
    def setUp(self):
        cache.clear()  # remet à zéro le compteur anti-force-brute

    def test_register_creates_client_profile(self):
        r = self.client.post('/api/auth/register/', {'email': 'a@b.com', 'password': PWD, 'first_name': 'Alice',
                                                     'last_name': 'Bernard', 'phone': '0340000001'})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(User.objects.get(email='a@b.com').client_profile)
        self.assertEqual(User.objects.get(email='a@b.com').role, 'CLIENT')

    def test_register_duplicate_email(self):
        make_user(email='dup@x.com')
        r = self.client.post('/api/auth/register/', {'email': 'dup@x.com', 'password': PWD, 'first_name': 'A',
                                                     'last_name': 'B', 'phone': '0340000001'})
        self.assertEqual(r.status_code, 400)

    def test_login_returns_jwt_and_role(self):
        make_user(email='l@x.com')
        r = self.client.post('/api/auth/login/', {'email': 'l@x.com', 'password': PWD})
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)
        self.assertEqual(r.data['user']['role'], 'CLIENT')

    def test_login_wrong_password(self):
        make_user(email='w@x.com')
        self.assertEqual(self.client.post('/api/auth/login/', {'email': 'w@x.com', 'password': 'bad'}).status_code, 401)

    def test_me_requires_auth_and_change_password(self):
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        u = make_user()
        self.client.force_authenticate(u)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        r = self.client.post('/api/auth/change-password/', {'old_password': PWD, 'new_password': 'N3w-Passw0rd!'})
        self.assertEqual(r.status_code, 200)
        u.refresh_from_db()
        self.assertTrue(u.check_password('N3w-Passw0rd!'))

    def test_users_endpoint_admin_only(self):
        self.client.force_authenticate(make_user(User.Role.RECEPTIONNISTE))
        self.assertEqual(self.client.get('/api/users/').status_code, 403)
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        self.assertEqual(self.client.get('/api/users/').status_code, 200)

    def test_dashboard_permissions(self):
        self.client.force_authenticate(make_user(User.Role.ADMIN))
        self.assertIn('total_chambres', self.client.get('/api/dashboard/').data)
        u = make_user()
        make_client(u)
        self.client.force_authenticate(u)
        self.assertNotIn('total_chambres', self.client.get('/api/dashboard/').data)

    BASE = {'email': 'n@x.com', 'password': PWD, 'first_name': 'Aina', 'last_name': 'Rakoto', 'phone': '034 12 345 67'}

    def test_register_validation(self):
        bad = [{'first_name': ' '}, {'last_name': 'R4koto'}, {'email': 'abc'}, {'phone': '12'}, {'password': 'court1'},
               {'password': 'pasdechiffreici'}, {'password': ''}]
        for i, extra in enumerate(bad):
            r = self.client.post('/api/auth/register/', {**self.BASE, 'email': f'b{i}@x.com', **extra})
            self.assertEqual(r.status_code, 400, extra)
        self.assertEqual(User.objects.count(), 0)

    def test_register_normalises_and_is_case_insensitive_on_email(self):
        r = self.client.post('/api/auth/register/', {**self.BASE, 'email': ' Aina@X.com ', 'first_name': ' Aina  '})
        self.assertEqual(r.status_code, 201, r.data)
        u = User.objects.get()
        self.assertEqual((u.email, u.first_name, u.phone), ('aina@x.com', 'Aina', '0341234567'))
        self.assertTrue(u.password.startswith('pbkdf2_'))  # mot de passe haché
        self.assertEqual(self.client.post('/api/auth/register/', {**self.BASE, 'email': 'AINA@x.com'}).status_code, 400)

    def test_register_refuses_email_of_existing_walk_in_client(self):
        make_client()  # fiche client créée à l'accueil, sans compte
        from apps.clients.models import Client
        email = Client.objects.get().email
        self.assertEqual(self.client.post('/api/auth/register/', {**self.BASE, 'email': email}).status_code, 400)

    def test_login_is_rate_limited(self):
        make_user(email='t@x.com')
        codes = [self.client.post('/api/auth/login/', {'email': 't@x.com', 'password': 'faux'}).status_code for _ in range(12)]
        self.assertEqual(codes[0], 401)
        self.assertEqual(codes[-1], 429)

    def test_login_ignores_email_case(self):
        """Compte créé avec une majuscule, formulaire qui envoie des minuscules : la connexion doit réussir."""
        u = make_user(email='x@x.com', role=User.Role.ADMIN)
        User.objects.filter(pk=u.pk).update(email='Arintsoa@Hotel.com')  # ancien compte avec majuscules
        for typed in ('Arintsoa@Hotel.com', 'arintsoa@hotel.com', 'ARINTSOA@HOTEL.COM', '  arintsoa@hotel.com '):
            r = self.client.post('/api/auth/login/', {'email': typed, 'password': PWD})
            self.assertEqual(r.status_code, 200, typed)
            self.assertEqual(r.data['user']['role'], 'ADMIN')
        self.assertEqual(self.client.post('/api/auth/login/', {'email': 'arintsoa@hotel.com', 'password': 'faux'}).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/login/', {'email': 'inconnu@hotel.com', 'password': PWD}).status_code, 401)

    def test_new_accounts_store_lowercase_email(self):
        self.assertEqual(User.objects.create_user(email='Majuscule@Hotel.COM', password=PWD).email, 'majuscule@hotel.com')
