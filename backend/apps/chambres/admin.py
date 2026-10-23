from django.contrib import admin

from .models import Categorie, Chambre, Equipement

admin.site.register([Categorie, Chambre, Equipement])
