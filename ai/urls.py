from django.urls import path

from .views import GenerateInsightView

app_name = 'ai'

urlpatterns = [
    path('analises/gerar/', GenerateInsightView.as_view(), name='generate'),
]
