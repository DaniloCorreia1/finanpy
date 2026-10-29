from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    template_name = 'core/landing.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
