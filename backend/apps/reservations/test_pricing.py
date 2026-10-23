from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from .pricing import PrixInvalide, calculer_devis

A, D3, D8 = date(2030, 1, 10), date(2030, 1, 13), date(2030, 1, 18)


def svc(mode, prix, qte=1):
    return {'service_id': 1, 'nom': 'S', 'mode': mode, 'prix_unitaire': Decimal(prix), 'quantite': qte}


class PricingTests(SimpleTestCase):
    def test_basic_amount(self):
        dv = calculer_devis(prix_nuit=25000, arrivee=A, depart=D3, nb_personnes=2)
        self.assertEqual((dv['nb_nuits'], dv['montant_total']), (3, Decimal('75000')))

    def test_minimum_exactly_20000_accepted(self):
        self.assertEqual(calculer_devis(prix_nuit=20000, arrivee=A, depart=D3, nb_personnes=1)['montant_total'], Decimal('60000'))

    def test_below_minimum_rejected(self):
        for p in (0, 1, '19999.99', 19999):
            with self.assertRaises(PrixInvalide):
                calculer_devis(prix_nuit=p, arrivee=A, depart=D3, nb_personnes=1)

    def test_invalid_dates_rejected(self):
        for a, b in ((A, A), (D3, A)):
            with self.assertRaises(PrixInvalide):
                calculer_devis(prix_nuit=25000, arrivee=a, depart=b, nb_personnes=1)

    def test_service_modes(self):
        # 2 personnes, 3 nuits
        cas = [('SEJOUR', 40000, 2, '80000'), ('NUIT', 5000, 1, '15000'), ('PERSONNE', 25000, 1, '50000'),
               ('PERSONNE_NUIT', 8000, 1, '48000')]
        for mode, prix, qte, attendu in cas:
            dv = calculer_devis(prix_nuit=25000, arrivee=A, depart=D3, nb_personnes=2, lignes=[svc(mode, prix, qte)])
            self.assertEqual(dv['services_montant'], Decimal(attendu), mode)
            self.assertEqual(dv['montant_total'], Decimal('75000') + Decimal(attendu), mode)

    def test_quantity_ignored_except_per_stay(self):
        dv = calculer_devis(prix_nuit=25000, arrivee=A, depart=D3, nb_personnes=1, lignes=[svc('NUIT', 5000, 9)])
        self.assertEqual(dv['services_montant'], Decimal('15000'))

    @override_settings(TAUX_TVA=20, TAXE_SEJOUR_PAR_PERSONNE_NUIT=1000)
    def test_taxes_shown_separately(self):
        dv = calculer_devis(prix_nuit=25000, arrivee=A, depart=D3, nb_personnes=2)
        self.assertEqual([t['montant'] for t in dv['taxes']], [Decimal('6000'), Decimal('15000')])
        self.assertEqual(dv['montant_total'], Decimal('75000') + Decimal('21000'))

    def test_no_tax_line_when_disabled(self):
        self.assertEqual(calculer_devis(prix_nuit=25000, arrivee=A, depart=D3, nb_personnes=2)['taxes'], [])

    @override_settings(REDUCTION_LONG_SEJOUR_POURCENT=10, REDUCTION_LONG_SEJOUR_NUITS=7)
    def test_long_stay_discount(self):
        court = calculer_devis(prix_nuit=30000, arrivee=A, depart=D3, nb_personnes=1)
        self.assertEqual(court['reduction_montant'], 0)
        long = calculer_devis(prix_nuit=30000, arrivee=A, depart=D8, nb_personnes=1)  # 8 nuits
        self.assertEqual((long['reduction_montant'], long['montant_total']), (Decimal('24000'), Decimal('216000')))

    @override_settings(REDUCTION_LONG_SEJOUR_POURCENT=50, REDUCTION_LONG_SEJOUR_NUITS=7)
    def test_discount_never_goes_below_minimum_nightly_rate(self):
        dv = calculer_devis(prix_nuit=25000, arrivee=A, depart=D8, nb_personnes=1)  # 8 nuits x 25000 = 200000
        self.assertEqual(dv['hebergement_montant'] - dv['reduction_montant'], Decimal('20000') * 8)

    def test_rounding_to_whole_ariary(self):
        dv = calculer_devis(prix_nuit=Decimal('20000.40'), arrivee=A, depart=D3, nb_personnes=1)
        self.assertEqual(dv['hebergement_montant'], Decimal('60001'))
