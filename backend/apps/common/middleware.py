"""Sécurité de session : aucune réponse de l'API ne doit pouvoir être relue depuis le cache du navigateur.

Sans cela, après une déconnexion, le bouton « Retour » du navigateur pourrait ré-afficher des données
confidentielles (clients, réservations, factures) conservées en cache ou dans le cache « avant/arrière » (bfcache).
"""
from django.utils.cache import add_never_cache_headers, patch_vary_headers


class NoCacheMiddleware:
    """Ajoute Cache-Control: no-store, no-cache, must-revalidate (+ Pragma/Expires) aux réponses de l'API et de l'admin."""

    PREFIXES = ('/api/', '/admin/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self.PREFIXES):
            add_never_cache_headers(response)  # Cache-Control: max-age=0, no-cache, no-store, must-revalidate, private
            response['Pragma'] = 'no-cache'    # HTTP/1.0 et anciens proxys
            patch_vary_headers(response, ('Authorization',))
        return response
