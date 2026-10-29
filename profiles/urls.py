from django.urls import path

from .views import ProfileDetailView, ProfileUpdateView

app_name = 'profiles'

urlpatterns = [
    path('', ProfileDetailView.as_view(), name='detail'),
    path('editar/', ProfileUpdateView.as_view(), name='update'),
]
