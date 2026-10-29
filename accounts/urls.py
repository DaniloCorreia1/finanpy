from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.AccountListView.as_view(), name='list'),
    path('nova/', views.AccountCreateView.as_view(), name='create'),
    path(
        '<int:pk>/editar/', views.AccountUpdateView.as_view(), name='update'
    ),
    path(
        '<int:pk>/excluir/', views.AccountDeleteView.as_view(), name='delete'
    ),
]
