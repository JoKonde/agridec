from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ExploitationForm, LoginForm, RegisterForm
from .models import Analyse, Exploitation
from .services.decision_engine import DecisionEngine
from .services.weather_service import WeatherApiError

def home(request):
    """Page d'accueil publique."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


def register_view(request):
    """Inscription d'un nouvel agriculteur."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Bienvenue ! Votre compte a été créé avec succès.')
            return redirect('dashboard')
        messages.error(request, 'Veuillez corriger les erreurs du formulaire.')
    else:
        form = RegisterForm()

    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    """Connexion d'un agriculteur existant."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, f'Bon retour, {request.user.username} !')
            return redirect('dashboard')
        messages.error(request, 'Identifiants incorrects. Veuillez réessayer.')
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """Déconnexion de l'utilisateur."""
    logout(request)
    messages.info(request, 'Vous êtes déconnecté.')
    return redirect('home')


@login_required
def dashboard_view(request):
    """Tableau de bord de l'agriculteur connecté."""
    exploitations = Exploitation.objects.filter(utilisateur=request.user)
    context = {
        'exploitation_count': exploitations.count(),
        'exploitations': exploitations.select_related('culture', 'type_sol'),
    }
    return render(request, 'dashboard.html', context)


@login_required
def exploitation_create_view(request):
    """Enregistrement d'une nouvelle culture pour l'agriculteur connecté."""
    if request.method == 'POST':
        form = ExploitationForm(request.POST)
        if form.is_valid():
            exploitation = form.save(utilisateur=request.user)
            messages.success(
                request,
                f'La culture « {exploitation.culture.nom} » a été enregistrée avec succès.',
            )
            return redirect('dashboard')
        messages.error(request, 'Veuillez corriger les erreurs du formulaire.')
    else:
        form = ExploitationForm()

    return render(request, 'cultures/form.html', {'form': form})


@login_required
def exploitation_analyse_view(request, pk):
    """Analyse agricole complète d'une exploitation."""
    exploitation = get_object_or_404(
        Exploitation,
        pk=pk,
        utilisateur=request.user,
    )

    try:
        resultat = DecisionEngine().analyze(exploitation)
    except WeatherApiError as exc:
        messages.error(
            request,
            f'Impossible de récupérer les données météo : {exc}',
        )
        return redirect('dashboard')
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('dashboard')

    Analyse.objects.create(exploitation=exploitation, resultat=resultat)

    return render(request, 'cultures/analyse.html', {
        'exploitation': exploitation,
        'resultat': resultat,
    })


@login_required
def analyses_list_view(request):
    """Historique des analyses de l'agriculteur connecté."""
    analyses = (
        Analyse.objects
        .filter(exploitation__utilisateur=request.user)
        .select_related('exploitation', 'exploitation__culture')
        .order_by('-date_analyse')
    )
    return render(request, 'analyses/list.html', {'analyses': analyses})


@login_required
def analyse_detail_view(request, pk):
    """Consultation d'une analyse passée (données sauvegardées)."""
    analyse = get_object_or_404(
        Analyse,
        pk=pk,
        exploitation__utilisateur=request.user,
    )
    return render(request, 'cultures/analyse.html', {
        'exploitation': analyse.exploitation,
        'resultat': analyse.resultat,
        'analyse_date': analyse.date_analyse,
        'lecture_seule': True,
    })


def error_404_view(request, exception):
    """Page 404 personnalisée."""
    return render(request, 'errors/404.html', status=404)


def error_403_view(request, exception):
    """Page 403 personnalisée."""
    return render(request, 'errors/403.html', status=403)
