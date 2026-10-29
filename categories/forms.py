from django import forms

from .models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'category_type']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['category_type'].choices = [
            ('', 'Selecione'),
            *Category.TYPE_CHOICES,
        ]

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        category_type = cleaned_data.get('category_type')
        if name and category_type:
            duplicates = Category.objects.filter(
                user=self.user,
                name__iexact=name,
                category_type=category_type,
            )
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise forms.ValidationError(
                    'Você já possui uma categoria com este nome e tipo.'
                )
        return cleaned_data
