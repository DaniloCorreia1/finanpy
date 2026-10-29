from django.contrib import admin
from django.urls import include, path

from core.views import LandingPageView

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing'),
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('perfil/', include('profiles.urls')),
    path('contas/', include('accounts.urls')),
    path('categorias/', include('categories.urls')),
    path('transacoes/', include('transactions.urls')),
]
