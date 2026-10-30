from django.contrib import admin
from django.urls import include, path

from core.views import DashboardView, LandingPageView

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('perfil/', include('profiles.urls')),
    path('contas/', include('accounts.urls')),
    path('categorias/', include('categories.urls')),
    path('transacoes/', include('transactions.urls')),
    path('ia/', include('ai.urls')),
]
