from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.authentication.views import UserViewSet
from apps.chambres.views import CategorieViewSet, ChambreViewSet, EquipementViewSet
from apps.clients.views import ClientViewSet
from apps.dashboard.views import DashboardView
from apps.factures.views import FactureViewSet
from apps.paiements.views import PaiementViewSet
from apps.reservations.views import ReservationViewSet, ServiceViewSet

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('categories', CategorieViewSet, basename='categorie')
router.register('equipements', EquipementViewSet, basename='equipement')
router.register('chambres', ChambreViewSet, basename='chambre')
router.register('clients', ClientViewSet, basename='client')
router.register('services', ServiceViewSet, basename='service')
router.register('reservations', ReservationViewSet, basename='reservation')
router.register('paiements', PaiementViewSet, basename='paiement')
router.register('factures', FactureViewSet, basename='facture')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')),
    path('api/', include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
