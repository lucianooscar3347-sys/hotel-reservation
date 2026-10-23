"""Connexion insensible à la casse de l'adresse e-mail.

Le formulaire du site envoie l'e-mail en minuscules, alors qu'un compte peut avoir été créé avec des majuscules
(ex. « Arintsoa@hotel.com » via createsuperuser) : la recherche exacte de Django ne le retrouvait pas, d'où
« Email ou mot de passe incorrect » avec pourtant le bon mot de passe. L'unicité est déjà garantie sans tenir
compte de la casse par l'index LOWER(email) : une seule correspondance est possible.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CaseInsensitiveEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        email = username if username is not None else kwargs.get(User.USERNAME_FIELD)
        if email is None or password is None:
            return None
        try:
            user = User._default_manager.get(email__iexact=str(email).strip())
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            User().set_password(password)  # même durée de calcul : ne révèle pas si le compte existe
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
