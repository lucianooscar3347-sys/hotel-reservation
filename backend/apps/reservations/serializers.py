from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.authentication.models import User
from apps.chambres.models import Chambre
from apps.common.constants import PRIX_MINIMUM_NUIT
from apps.common.exceptions import Conflit
from apps.common.utils import format_ar

from .models import LigneService, Reservation, Service
from .pricing import PrixInvalide, calculer_devis, devis_vers_json, ligne_depuis_service
from .services import reservations_en_conflit, valider_sejour

# Champs de montant qu'un client malveillant pourrait tenter d'imposer : toute valeur différente du calcul serveur est refusée.
CHAMPS_MONTANT = ('prix_nuit', 'nb_nuits', 'hebergement_montant', 'services_montant', 'reduction_montant',
                  'taxes_montant', 'montant_total')


class ServiceSerializer(serializers.ModelSerializer):
    mode_libelle = serializers.CharField(source='get_mode_display', read_only=True)

    class Meta:
        model = Service
        fields = ['id', 'nom', 'description', 'prix', 'mode', 'mode_libelle', 'actif']

    def validate_nom(self, value):
        value = ' '.join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError('Le nom doit contenir au moins 2 caractères.')
        return value

    def validate_prix(self, value):
        if value <= 0:
            raise serializers.ValidationError('Le prix du service doit être positif.')
        if value > 10_000_000:
            raise serializers.ValidationError('Prix trop élevé.')
        return value


class LigneDemandeSerializer(serializers.Serializer):
    """Service demandé par le client : seul l'identifiant et la quantité sont acceptés, jamais le prix."""
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(actif=True),
        error_messages={'does_not_exist': "Ce service n'existe pas ou n'est plus proposé."})
    quantite = serializers.IntegerField(min_value=1, max_value=10, default=1)


class LigneServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigneService
        fields = ['id', 'nom', 'mode', 'prix_unitaire', 'quantite', 'montant']


def _services_uniques(valeur):
    ids = [l['service'].pk for l in valeur]
    if len(ids) != len(set(ids)):
        raise serializers.ValidationError('Un même service ne peut être sélectionné qu\'une fois.')
    return valeur


def _lignes(demandes):
    return [ligne_depuis_service(d['service'], d['quantite']) for d in demandes]


def _devis_ou_400(**kw):
    try:
        return calculer_devis(**kw)
    except PrixInvalide as e:
        raise serializers.ValidationError({'prix_nuit': str(e)})


class ReservationSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='client.nom_complet', read_only=True)
    chambre_numero = serializers.CharField(source='chambre.numero', read_only=True)
    chambre_categorie = serializers.CharField(source='chambre.categorie.nom', read_only=True)
    montant_paye = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    reste_a_payer = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    lignes = LigneServiceSerializer(source='lignes_services', many=True, read_only=True)
    services_demandes = LigneDemandeSerializer(many=True, write_only=True, required=False)
    # Montant affiché au client avant confirmation : si le tarif a changé entre-temps, la réservation est refusée.
    montant_attendu = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True, required=False)

    class Meta:
        model = Reservation
        fields = ['id', 'numero_reservation', 'client', 'client_nom', 'chambre', 'chambre_numero', 'chambre_categorie', 'date_arrivee',
                  'date_depart', 'nb_adultes', 'nb_enfants', 'prix_nuit', 'nb_nuits', 'hebergement_montant',
                  'services_montant', 'reduction_montant', 'taxes_montant', 'montant_total', 'montant_paye',
                  'reste_a_payer', 'statut', 'date_reservation', 'lignes', 'services_demandes', 'montant_attendu']
        read_only_fields = ['numero_reservation', 'prix_nuit', 'nb_nuits', 'hebergement_montant', 'services_montant',
                            'reduction_montant', 'taxes_montant', 'montant_total', 'statut', 'date_reservation']
        extra_kwargs = {'client': {'required': False},
                        'nb_adultes': {'min_value': 1, 'max_value': 20},
                        'nb_enfants': {'min_value': 0, 'max_value': 20}}

    def validate_services_demandes(self, value):
        return _services_uniques(value)

    def validate(self, attrs):
        inst = self.instance
        user = self.context['request'].user
        arrivee = attrs.get('date_arrivee', inst.date_arrivee if inst else None)
        depart = attrs.get('date_depart', inst.date_depart if inst else None)
        chambre = attrs.get('chambre', inst.chambre if inst else None)
        adultes = attrs.get('nb_adultes', inst.nb_adultes if inst else 1)
        enfants = attrs.get('nb_enfants', inst.nb_enfants if inst else 0)

        if inst and inst.statut in (Reservation.Statut.ANNULEE, Reservation.Statut.TERMINEE):
            raise serializers.ValidationError('Une réservation annulée ou terminée ne peut plus être modifiée.')
        if not inst and user.role != User.Role.CLIENT and not attrs.get('client'):
            raise serializers.ValidationError({'client': 'Le client est obligatoire.'})
        valider_sejour(chambre, arrivee, depart, adultes, enfants,
                       verifier_passe=(not inst or 'date_arrivee' in attrs))
        return attrs

    def _verrouiller_et_verifier(self, chambre, arrivee, depart, exclude_id=None):
        # SELECT ... FOR UPDATE : sérialise les réservations concurrentes d'une même chambre.
        # Le prix est relu ICI, en base, au moment de la confirmation.
        chambre = Chambre.objects.select_for_update().get(pk=chambre.pk)
        if chambre.statut == Chambre.Statut.MAINTENANCE:
            raise serializers.ValidationError({'chambre': 'Cette chambre est en maintenance.'})
        if reservations_en_conflit(chambre.pk, arrivee, depart, exclude_id).exists():
            raise Conflit({'chambre': 'Cette chambre vient d\'être réservée sur cette période. Choisissez d\'autres dates ou une autre chambre.'})
        return chambre

    def _controler_montants(self, devis, attendu):
        """Rejette toute valeur de montant envoyée par le client qui diffère du calcul serveur."""
        for champ in CHAMPS_MONTANT:
            brut = self.initial_data.get(champ) if hasattr(self.initial_data, 'get') else None
            if brut in (None, ''):
                continue
            try:
                envoye = Decimal(str(brut))
            except InvalidOperation:
                raise serializers.ValidationError({champ: 'Valeur invalide.'})
            if envoye != Decimal(devis[champ]):
                raise serializers.ValidationError(
                    {champ: 'Montant refusé : les tarifs sont calculés par le serveur et ne peuvent pas être imposés.'})
        if attendu is not None and attendu != devis['montant_total']:
            raise serializers.ValidationError({'montant_attendu': (
                f"Le tarif a changé : le total est maintenant de {format_ar(devis['montant_total'])} "
                f"(affiché : {format_ar(attendu)}). Vérifiez le récapitulatif puis confirmez à nouveau.")})

    def _enregistrer_lignes(self, resa, devis):
        resa.lignes_services.all().delete()
        LigneService.objects.bulk_create([
            LigneService(reservation=resa, service_id=l['service_id'], nom=l['nom'], mode=l['mode'],
                         prix_unitaire=l['prix_unitaire'], quantite=l['quantite'], montant=l['montant'])
            for l in devis['services']])

    @staticmethod
    def _champs_devis(devis):
        return {k: devis[k] for k in ('prix_nuit', 'nb_nuits', 'hebergement_montant', 'services_montant',
                                       'reduction_montant', 'taxes_montant', 'montant_total')}

    @staticmethod
    def _sauver(operation):
        """Exécute l'écriture dans un savepoint : si PostgreSQL refuse (contrainte d'exclusion = chevauchement
        détecté par la base malgré les contrôles applicatifs), on renvoie un 409 propre au lieu d'une 500."""
        try:
            with transaction.atomic():
                return operation()
        except IntegrityError as e:
            if 'excl_resa_chevauchement' in str(e):
                raise Conflit({'chambre': 'Cette chambre vient d\'être réservée sur cette période. '
                                          'Choisissez d\'autres dates ou une autre chambre.'})
            raise

    @transaction.atomic
    def create(self, vd):
        demandes = vd.pop('services_demandes', [])
        attendu = vd.pop('montant_attendu', None)
        chambre = self._verrouiller_et_verifier(vd['chambre'], vd['date_arrivee'], vd['date_depart'])
        client = vd.get('client')
        if client and Reservation.objects.filter(
                client=client, chambre=chambre, date_arrivee=vd['date_arrivee'], date_depart=vd['date_depart'],
                statut__in=Reservation.ACTIVES).exists():
            raise Conflit({'detail': 'Une réservation identique existe déjà pour ce client (envoi en double ?).'})
        devis = _devis_ou_400(prix_nuit=chambre.prix_nuit, arrivee=vd['date_arrivee'], depart=vd['date_depart'],
                              nb_personnes=vd['nb_adultes'] + vd.get('nb_enfants', 0), lignes=_lignes(demandes))
        self._controler_montants(devis, attendu)
        vd.update(self._champs_devis(devis))
        resa = self._sauver(lambda: super(ReservationSerializer, self).create(vd))
        self._enregistrer_lignes(resa, devis)
        return resa

    @transaction.atomic
    def update(self, instance, vd):
        demandes = vd.pop('services_demandes', None)
        attendu = vd.pop('montant_attendu', None)
        chambre = vd.get('chambre', instance.chambre)
        arrivee = vd.get('date_arrivee', instance.date_arrivee)
        depart = vd.get('date_depart', instance.date_depart)
        chambre = self._verrouiller_et_verifier(chambre, arrivee, depart, exclude_id=instance.pk)
        # Prix figé conservé tant que la chambre ne change pas (et qu'il respecte le minimum, sinon tarif actuel).
        if chambre.pk == instance.chambre_id and instance.prix_nuit >= PRIX_MINIMUM_NUIT:
            prix = instance.prix_nuit
        else:
            prix = chambre.prix_nuit
        if demandes is not None:
            lignes = _lignes(demandes)
        else:  # on conserve les services déjà choisis, avec leur prix figé
            lignes = [{'service_id': l.service_id, 'nom': l.nom, 'mode': l.mode, 'prix_unitaire': l.prix_unitaire,
                       'quantite': l.quantite} for l in instance.lignes_services.all()]
        personnes = vd.get('nb_adultes', instance.nb_adultes) + vd.get('nb_enfants', instance.nb_enfants)
        devis = _devis_ou_400(prix_nuit=prix, arrivee=arrivee, depart=depart, nb_personnes=personnes, lignes=lignes)
        self._controler_montants(devis, attendu)
        vd.update(self._champs_devis(devis))
        resa = self._sauver(lambda: super(ReservationSerializer, self).update(instance, vd))
        self._enregistrer_lignes(resa, devis)
        return resa


class DevisSerializer(serializers.Serializer):
    """Simulation du prix (aucune écriture) : mêmes règles que la réservation réelle."""
    chambre = serializers.PrimaryKeyRelatedField(queryset=Chambre.objects.all())
    date_arrivee = serializers.DateField()
    date_depart = serializers.DateField()
    nb_adultes = serializers.IntegerField(min_value=1, max_value=20, default=1)
    nb_enfants = serializers.IntegerField(min_value=0, max_value=20, default=0)
    services_demandes = LigneDemandeSerializer(many=True, required=False)

    def validate_services_demandes(self, value):
        return _services_uniques(value)

    def validate(self, a):
        valider_sejour(a['chambre'], a['date_arrivee'], a['date_depart'], a['nb_adultes'], a['nb_enfants'])
        if reservations_en_conflit(a['chambre'].pk, a['date_arrivee'], a['date_depart']).exists():
            raise Conflit({'chambre': 'Cette chambre est déjà réservée sur cette période.'})
        a['devis'] = devis_vers_json(_devis_ou_400(
            prix_nuit=a['chambre'].prix_nuit, arrivee=a['date_arrivee'], depart=a['date_depart'],
            nb_personnes=a['nb_adultes'] + a['nb_enfants'], lignes=_lignes(a.get('services_demandes', []))))
        return a
