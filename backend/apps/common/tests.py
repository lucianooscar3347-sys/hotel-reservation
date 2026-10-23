from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from rest_framework.exceptions import ValidationError

from .middleware import NoCacheMiddleware
from .utils import format_ar
from .validators import (ComplexitePasswordValidator, valider_cin, valider_email_domaine, valider_nom,
                         valider_telephone)


class ValidatorTests(SimpleTestCase):
    def test_names_accept_legitimate_values(self):
        for n in ("Jean-Pierre", "N'Diaye", "Éloïse", "  de   la Fontaine ", "Rakotoarivelo", "O’Brien"):
            self.assertTrue(valider_nom(n))
        self.assertEqual(valider_nom('  Jean   Paul '), 'Jean Paul')

    def test_names_reject_invalid_values(self):
        for n in ('', '   ', 'A', 'J0hn', 'Jean_Paul', '<script>', 'Jean\x00', 'a' * 101, '--', "''"):
            with self.assertRaises(ValidationError, msg=repr(n)):
                valider_nom(n)

    def test_phone_formats(self):
        self.assertEqual(valider_telephone('034 12 345 67'), '0341234567')
        self.assertEqual(valider_telephone('+261 34 12 345 67'), '+261341234567')
        self.assertEqual(valider_telephone('00261341234567'), '+261341234567')
        self.assertEqual(valider_telephone('+33 6 12 34 56 78'), '+33612345678')
        for bad in ('abc', '123', '', '034 12', '+261 34 12 345', '0341234567890123', '+0123456789'):
            with self.assertRaises(ValidationError, msg=bad):
                valider_telephone(bad)

    def test_email_domain(self):
        self.assertEqual(valider_email_domaine('  Jean@Example.COM '), 'jean@example.com')
        for bad in ('a@localhost', 'a@.com', 'a@b..com', 'a@com.'):
            with self.assertRaises(ValidationError, msg=bad):
                valider_email_domaine(bad)

    def test_password_policy(self):
        v = ComplexitePasswordValidator()
        v.validate('Passw0rd!xyz')
        for bad in ('court1', 'seulementdeslettres', '12345678901234'):
            with self.assertRaises(DjangoValidationError, msg=bad):
                v.validate(bad)

    def test_format_ar(self):
        self.assertEqual(format_ar(20000), '20 000 Ar')
        self.assertEqual(format_ar('1234567.00'), '1 234 567 Ar')


class CinTests(SimpleTestCase):
    def test_exactly_14_digits(self):
        self.assertEqual(valider_cin('12345678901234'), '12345678901234')
        self.assertEqual(valider_cin('  12345678901234  '), '12345678901234')  # espaces de début/fin retirés
        self.assertIsNone(valider_cin(''))
        self.assertIsNone(valider_cin('   '))

    def test_rejects_every_other_format(self):
        bad = ['1234567890123', '123456789012', '123456789012345', '12345678901A34', '1234 5678 9012 34',
               '1234-5678-9012-34', 'CIN-0001', '+26112345678901', '١٢٣٤٥٦٧٨٩٠١٢٣٤', '1234567890123\n4']
        for b in bad:
            with self.assertRaises(ValidationError, msg=repr(b)):
                valider_cin(b)


class NoCacheMiddlewareTests(SimpleTestCase):
    def _call(self, path):
        return NoCacheMiddleware(lambda request: HttpResponse('ok'))(RequestFactory().get(path))

    def test_api_and_admin_are_never_cached(self):
        for path in ('/api/clients/', '/api/auth/me/', '/admin/login/'):
            r = self._call(path)
            cc = r['Cache-Control']
            for directive in ('no-store', 'no-cache', 'must-revalidate', 'private', 'max-age=0'):
                self.assertIn(directive, cc, path)
            self.assertEqual(r['Pragma'], 'no-cache')
            self.assertIn('Authorization', r['Vary'])

    def test_other_paths_are_left_alone(self):
        self.assertNotIn('no-store', self._call('/media/chambres/photo.jpg').get('Cache-Control', ''))

    def test_headers_present_on_a_real_response(self):
        r = self.client.get('/api/auth/me/')  # sans jeton : 401, sans accès base de données
        self.assertEqual(r.status_code, 401)
        self.assertIn('no-store', r['Cache-Control'])
