"""python manage.py seed_demo : jeu de données de démonstration."""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.authentication.models import User
from apps.chambres.models import Categorie, Chambre, Equipement
from apps.clients.models import Client
from apps.paiements.models import Paiement
from apps.reservations.models import Reservation, Service
from apps.reservations.pricing import calculer_devis


class Command(BaseCommand):
    help = 'Crée des comptes, chambres et réservations de démonstration'

    def handle(self, *args, **opts):
        def user(email, pwd, role, fn, ln):
            u, created = User.objects.get_or_create(email=email, defaults=dict(role=role, first_name=fn, last_name=ln, phone='0340000000'))
            if created:
                u.set_password(pwd)
                u.save()
            return u

        user('admin@hotel.com', 'Admin123!', User.Role.ADMIN, 'Admin', 'Hôtel')
        user('reception@hotel.com', 'Reception123!', User.Role.RECEPTIONNISTE, 'Rina', 'Réception')
        cu = user('client@hotel.com', 'Client123!', User.Role.CLIENT, 'Jean', 'Client')
        jean, _ = Client.objects.get_or_create(user=cu, defaults=dict(
            nom='Client', prenom='Jean', email=cu.email, telephone='0340000000', sexe='M', numero_piece_identite='10120100000001'))
        marie, _ = Client.objects.get_or_create(email='marie@example.com', defaults=dict(
            nom='Rakoto', prenom='Marie', telephone='0321111111', sexe='F', numero_piece_identite='10120100000002'))

        cats = {n: Categorie.objects.get_or_create(nom=n)[0] for n in
                ['Simple', 'Double', 'Twin', 'Suite', 'Familiale', 'Deluxe']}
        equips = [Equipement.objects.get_or_create(nom=n)[0] for n in ['Wi-Fi', 'Climatisation', 'TV', 'Minibar', 'Balcon']]
        # Grille INDICATIVE en ariary par nuit (minimum légal du projet : 20 000 Ar) — à adapter aux tarifs réels.
        specs = [('Simple', 20000, 1), ('Double', 35000, 2), ('Twin', 38000, 2), ('Familiale', 60000, 4),
                 ('Suite', 120000, 3), ('Deluxe', 180000, 2)]
        for nom, desc, prix, mode in [
                ('Petit-déjeuner', 'Buffet continental', 8000, 'PERSONNE_NUIT'),
                ('Wi-Fi premium', 'Connexion haut débit', 5000, 'NUIT'),
                ('Transfert aéroport', 'Aller simple, Ivato ↔ hôtel', 40000, 'SEJOUR'),
                ('Dîner', 'Menu du soir, par personne', 25000, 'PERSONNE')]:
            Service.objects.get_or_create(nom=nom, defaults=dict(description=desc, prix=Decimal(prix), mode=mode))
        n = 100
        for etage in (1, 2):
            for nom, prix, cap in specs:
                n += 1
                ch, created = Chambre.objects.get_or_create(numero=str(n), defaults=dict(
                    categorie=cats[nom], type_chambre='Standard' if etage == 1 else 'Vue jardin',
                    prix_nuit=Decimal(prix if etage == 1 else round(prix * 1.15, -3)), capacite=cap, etage=etage, description=f'Chambre {nom} confortable.'))
                if created:
                    ch.equipements.set(equips[: 2 + (n % 4)])

        today = timezone.localdate()
        if not Reservation.objects.exists():
            for client, room, start, nights, st in [(jean, '101', 3, 3, 'CONFIRMEE'), (marie, '102', 1, 2, 'EN_ATTENTE'),
                                                    (jean, '104', -10, 4, 'TERMINEE'), (marie, '103', -40, 2, 'TERMINEE')]:
                ch = Chambre.objects.get(numero=room)
                a, d = today + timedelta(days=start), today + timedelta(days=start + nights)
                dv = calculer_devis(prix_nuit=ch.prix_nuit, arrivee=a, depart=d, nb_personnes=1)
                r = Reservation.objects.create(
                    client=client, chambre=ch, date_arrivee=a, date_depart=d, statut=st, prix_nuit=dv['prix_nuit'],
                    nb_nuits=dv['nb_nuits'], hebergement_montant=dv['hebergement_montant'], montant_total=dv['montant_total'])
                if st == 'TERMINEE':
                    Paiement.objects.create(reservation=r, montant=dv['montant_total'], mode_paiement='CARTE', statut='PAYE')
        self.stdout.write(self.style.SUCCESS('Données de démonstration créées.'))
