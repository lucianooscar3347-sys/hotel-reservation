from .models import Client


def get_client_profile(user):
    """Retourne (ou crée) la fiche client liée à un utilisateur."""
    client, _ = Client.objects.get_or_create(
        user=user,
        defaults={'nom': user.last_name or 'Client', 'prenom': user.first_name or 'Client',
                  'email': user.email, 'telephone': user.phone or ''})
    return client
