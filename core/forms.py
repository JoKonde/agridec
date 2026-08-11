from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Culture, Exploitation, TypeSol


class RegisterForm(UserCreationForm):
    """Formulaire d'inscription personnalisé pour les agriculteurs."""

    email = forms.EmailField(
        required=True,
        label='Adresse e-mail',
        widget=forms.EmailInput(attrs={
            'placeholder': 'exemple@email.com',
            'autocomplete': 'email',
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': "Nom d'utilisateur",
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Choisissez un identifiant',
                'autocomplete': 'username',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Mot de passe sécurisé',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirmez le mot de passe',
            'autocomplete': 'new-password',
        })
        self.fields['password1'].label = 'Mot de passe'
        self.fields['password2'].label = 'Confirmation'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Formulaire de connexion avec champs stylisés."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Nom d'utilisateur"
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Votre identifiant',
            'autocomplete': 'username',
        })
        self.fields['password'].label = 'Mot de passe'
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Votre mot de passe',
            'autocomplete': 'current-password',
        })


class ExploitationForm(forms.ModelForm):
    """Formulaire d'enregistrement d'une nouvelle culture / exploitation."""

    date_semis = forms.DateField(
        label='Date',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-date',
        }),
        help_text='Date prévue de semis ou date réelle selon le statut choisi.',
    )

    class Meta:
        model = Exploitation
        fields = ('culture', 'type_sol', 'statut', 'latitude', 'longitude')
        labels = {
            'culture': 'Culture',
            'type_sol': 'Type de sol',
            'statut': 'Statut',
        }
        widgets = {
            'latitude': forms.HiddenInput(attrs={'id': 'id_latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'id_longitude'}),
            'statut': forms.RadioSelect(attrs={'class': 'statut-radio'}),
            'culture': forms.Select(attrs={'class': 'form-select'}),
            'type_sol': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['culture'].queryset = Culture.objects.all()
        self.fields['type_sol'].queryset = TypeSol.objects.all()
        self.fields['statut'].choices = Exploitation.Statut.choices

        # Pré-remplir la date si édition ultérieure
        if self.instance.pk:
            date_effective = self.instance.date_semis_effective
            if date_effective:
                self.fields['date_semis'].initial = date_effective

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')

        if latitude is None or longitude is None:
            raise ValidationError(
                'La localisation GPS est obligatoire. '
                'Autorisez l\'accès à votre position ou réessayez.'
            )

        if not (-90 <= float(latitude) <= 90):
            raise ValidationError({'latitude': 'Latitude invalide.'})

        if not (-180 <= float(longitude) <= 180):
            raise ValidationError({'longitude': 'Longitude invalide.'})

        return cleaned_data

    def save(self, commit=True, utilisateur=None):
        exploitation = super().save(commit=False)
        date_semis = self.cleaned_data['date_semis']

        if exploitation.statut == Exploitation.Statut.A_SEMER:
            exploitation.date_prevue_semis = date_semis
            exploitation.date_reelle_semis = None
        else:
            exploitation.date_reelle_semis = date_semis
            exploitation.date_prevue_semis = None

        if utilisateur is not None:
            exploitation.utilisateur = utilisateur

        if commit:
            exploitation.save()

        return exploitation


class MlTestForm(forms.Form):
    """
    Formulaire pour tester le modèle ML seul (sans règles métier / FAO).
    Permet de rejouer une situation culture + sol + mois + météo.
    """

    culture = forms.ModelChoiceField(
        label='Culture',
        queryset=Culture.objects.none(),
        empty_label=None,
    )
    type_sol = forms.ModelChoiceField(
        label='Type de sol',
        queryset=TypeSol.objects.none(),
        empty_label=None,
    )
    mois = forms.TypedChoiceField(
        label='Mois à tester',
        coerce=int,
        choices=[
            (1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'),
            (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'),
            (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre'),
        ],
    )
    latitude = forms.FloatField(label='Latitude', initial=-4.325)
    longitude = forms.FloatField(label='Longitude', initial=15.322)
    temperature = forms.FloatField(label='Température (°C)', initial=28.0)
    humidite = forms.IntegerField(label='Humidité (%)', min_value=0, max_value=100, initial=64)
    pluie_mm = forms.FloatField(label='Pluie (mm)', initial=0.0, min_value=0)
    probabilite_pluie = forms.IntegerField(
        label='Probabilité de pluie (%)', min_value=0, max_value=100, initial=0,
    )
    vent_kmh = forms.FloatField(label='Vent (km/h)', initial=10.0, min_value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['culture'].queryset = Culture.objects.all().order_by('nom')
        self.fields['type_sol'].queryset = TypeSol.objects.all().order_by('nom')
        for name, field in self.fields.items():
            css = 'form-input'
            if isinstance(field.widget, forms.Select):
                css = 'form-select'
            field.widget.attrs.setdefault('class', css)
