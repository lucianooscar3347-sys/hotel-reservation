"""Fabriques utilisées par les tests."""
import itertools
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.authentication.models import User
from apps.chambres.models import Categorie, Chambre
from apps.clients.models import Client
from apps.reservations.models import Reservation
from apps.reservations.pricing import calculer_devis

PWD = 'Passw0rd!x'
_n = itertools.count(1)


def make_user(role=User.Role.CLIENT, email=None):
    i = next(_n)
    return User.objects.create_user(email=email or f'u{i}@test.com', password=PWD, first_name='Test',
                                    last_name=f'User{i}', role=role)


def make_client(user=None):
    i = next(_n)
    return Client.objects.create(user=user, nom='Doe', prenom=f'John{i}', email=user.email if user else f'c{i}@test.com',
                                 telephone='0340000000', numero_piece_identite=f'ID{i}')


def make_chambre(numero=None, prix=25000, capacite=2, statut=Chambre.Statut.DISPONIBLE):
    i = next(_n)
    cat, _ = Categorie.objects.get_or_create(nom='Double')
    return Chambre.objects.create(numero=numero or str(100 + i), categorie=cat, type_chambre='Standard',
                                  prix_nuit=Decimal(prix), capacite=capacite, statut=statut)


def make_service(nom=None, prix=8000, mode='PERSONNE_NUIT', actif=True):
    from apps.reservations.models import Service
    i = next(_n)
    return Service.objects.create(nom=nom or f'Service {i}', prix=Decimal(prix), mode=mode, actif=actif)


def make_reservation(client, chambre, start=5, nights=2, statut=Reservation.Statut.CONFIRMEE):
    arrivee = timezone.localdate() + timedelta(days=start)
    depart = arrivee + timedelta(days=nights)
    dv = calculer_devis(prix_nuit=chambre.prix_nuit, arrivee=arrivee, depart=depart, nb_personnes=1)
    return Reservation.objects.create(client=client, chambre=chambre, date_arrivee=arrivee, date_depart=depart,
                                      prix_nuit=dv['prix_nuit'], nb_nuits=dv['nb_nuits'],
                                      hebergement_montant=dv['hebergement_montant'], montant_total=dv['montant_total'],
                                      statut=statut)
