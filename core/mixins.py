class UserQuerySetMixin:
    """Restringe o queryset da view aos objetos do usuário logado."""

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
