COURS DJANGO BASÉ SUR LE PROJET AGRIDEC
=======================================

But : te donner un **vrai cours Django** en français, en expliquant :
- chaque grande partie de Django (settings, models, views, forms, urls, templates, services)
- en même temps **comment c’est codé** dans ton projet AgriDec
- avec le “pourquoi” de la syntaxe, pour que tu puisses l’expliquer à un étudiant.

Garde ce fichier comme support de cours : tu peux le lire, le résumer, ou le présenter en live.

----------------------------------------------------------------
0. Rappel : c’est quoi Django ? (MVT)
----------------------------------------------------------------

Django est un framework web Python qui suit le pattern **MVT** :

- **Model** : décrit les données (ce qui est stocké en base, ex. Culture, Exploitation).
- **View** : logique métier / contrôleur qui décide quoi afficher (quelle page, quelles données).
- **Template** : HTML + balises Django pour afficher proprement les données.

Par rapport au fameux “MVC” :
- le **Model** = pareil
- la **View** Django = plutôt le **Controller** MVC
- le **Template** = la “vue” HTML.

Dans AgriDec, ce pattern est respecté :
- `core/models.py` → modèles
- `core/views.py` → vues
- `templates/*.html` → templates
- le reste (services, forms) sert à organiser le code proprement.

----------------------------------------------------------------
1. Architecture du projet : projet vs application
----------------------------------------------------------------

Dans Django, tu as :

- un **projet** (ici le dossier `AgriDec/` avec `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`)
- une ou plusieurs **applications** (ici surtout `core/`).

On peut voir ça comme :
- **Projet** = configuration globale + entrée du site.
- **Application** = module fonctionnel (ici : gestion agricole).

Dans AgriDec :

- `AgriDec/settings.py` : configuration globale (base de données, apps, templates, etc.)
- `AgriDec/urls.py` : point d’entrée pour les URLs (route vers `core.urls`)
- `core/` : le “vrai métier” (models, views, forms, urls, services).

Regarde `AgriDec/urls.py` :
  - `path('', include('core.urls'))`
  → cela signifie : **toutes les URL du site** (“/”, “/dashboard/”, “/inscription/”, …)
    sont définies dans `core/urls.py`.

Syntaxe importante :
- `from django.urls import path, include`
- `urlpatterns = [...]` = liste de routes.

----------------------------------------------------------------
2. Configuration globale : settings.py (le cerveau)
----------------------------------------------------------------

`AgriDec/settings.py` est le fichier de **configuration** du projet :

2.1. SECRET_KEY, DEBUG, ALLOWED_HOSTS
-------------------------------------

```python
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-...valeur par défaut...',
)
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [...]
```

- `SECRET_KEY` : clé secrète pour sécuriser les sessions, cookies, etc.
  - En dev : on peut mettre une valeur par défaut.
  - En prod : on doit la prendre depuis les variables d’environnement (`.env`).
- `DEBUG` : mode debug (affiche les erreurs détaillées). **Jamais True en prod**.
- `ALLOWED_HOSTS` : liste des domaines acceptés (ex. `localhost`, `127.0.0.1`).

2.2. INSTALLED_APPS
-------------------

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]
```

- Les apps Django “officielles” (`admin`, `auth`, etc.).
- `core` → ton application métier (il faut la déclarer ici pour qu’elle soit chargée).

2.3. TEMPLATES
--------------

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
```

- `DIRS` : Django va chercher les templates dans `BASE_DIR / 'templates'`.
- `APP_DIRS=True` : il cherche aussi dans `core/templates/` si tu en avais.
- `context_processors` : ajoutent des variables automatiques dans les templates (`user`, `messages`, etc.).

2.4. Base de données, fichiers statiques, etc.
----------------------------------------------

Dans ce projet :
- base MySQL configurée via variables d’environnement (`DB_NAME`, `DB_USER`…)
- `STATIC_URL`, `STATICFILES_DIRS` définissent où trouver le CSS/JS.

Idée à expliquer :
- `settings.py` = tout ce qui configure le framework (pas la logique métier).

----------------------------------------------------------------
3. Les modèles (models.py) : structure des données
----------------------------------------------------------------

Tout est regroupé dans `core/models.py` pour ce projet académique, pour que tu voies tout au même endroit.

3.1. Culture
------------

```python
class Culture(models.Model):
    nom = models.CharField('nom', max_length=150)
    fao_crop_id = models.CharField(
        'identifiant FAO',
        max_length=10,
        blank=True,
        unique=True,
        null=True,
    )
    duree_recolte_jours = models.PositiveIntegerField(
        'durée moyenne avant récolte (jours)',
        default=90,
    )
    class Meta:
        ordering = ['nom']
```

- `class Culture(models.Model)` : modèle Django = table `core_culture` en base.
- `CharField` = chaîne de caractères (colonne texte).
- `PositiveIntegerField` = entier positif.
- `Meta.ordering` = ordre par défaut des requêtes (`Culture.objects.all()`).

3.2. TypeSol
------------

- Un seul champ `nom` unique.
- Sert à limiter les valeurs de type de sol (liste de référence).

3.3. Exploitation
-----------------

```python
class Exploitation(models.Model):
    class Statut(models.TextChoices):
        A_SEMER = 'A_SEMER', 'Je vais semer'
        DEJA_SEME = 'DEJA_SEME', "J'ai déjà semé"

    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
    culture = models.ForeignKey(Culture, ...)
    type_sol = models.ForeignKey(TypeSol, ...)
    latitude = models.DecimalField(...)
    longitude = models.DecimalField(...)
    statut = models.CharField(max_length=20, choices=Statut.choices)
    date_prevue_semis = models.DateField(null=True, blank=True)
    date_reelle_semis = models.DateField(null=True, blank=True)
```

Points importants à expliquer :

- `ForeignKey` :
  - `Exploitation` → `User` (l’agriculteur)
  - `Exploitation` → `Culture`
  - `Exploitation` → `TypeSol`
- `TextChoices` :
  - permet d’avoir des constantes propres pour le statut (A_SEMER / DEJA_SEME)
  - en base on stocke `'A_SEMER'`, mais on affiche `get_statut_display()` → texte lisible.
- `DecimalField` : pour les coordonnées GPS (éviter les flottants approximatifs).
- `DateField` : dates de semis prévues ou réelles.

3.4. Analyse
------------

- Lien vers `Exploitation` (ForeignKey).
- `JSONField` pour stocker le résultat du moteur de décision (structure JSON).

3.5. FaoCalendrier
------------------

- Représente les lignes du calendrier FAO importé (pays, zone, mois début/fin semis, récolte…).
- Contrainte d’unicité (`UniqueConstraint`) pour éviter les doublons pour une même culture/zone/saison.

----------------------------------------------------------------
4. Les formulaires (forms.py) : gérer les formulaires proprement
----------------------------------------------------------------

Les formulaires sont dans `core/forms.py`.

4.1. RegisterForm (inscription)
-------------------------------

Hérite de `UserCreationForm`, ajoute un champ `email`, personnalise les labels et placeholders.

Syntaxe clé :
- `class Meta:` interne pour lier le formulaire au modèle `User` et définir les champs.
- `def save(self, commit=True)` pour ajouter la logique d’enregistrement de l’email.

4.2. LoginForm (connexion)
--------------------------

Hérite de `AuthenticationForm`. On modifie les labels et les placeholders dans `__init__`.

4.3. ExploitationForm (nouvelle culture)
----------------------------------------

`ModelForm` liée au modèle `Exploitation`.

- Champ supplémentaire `date_semis` (n’existe pas dans le modèle) pour simplifier le formulaire.
- `Meta` : précise quels champs du modèle afficher (`culture`, `type_sol`, `statut`, `latitude`, `longitude`).
- `widgets` : personnalise le rendu (radio buttons pour le statut, hidden pour lat/long).

Validation dans `clean()` :
- vérifie que lat/long sont présents (GPS obligatoire)
- contrôle les bornes (-90 / 90 pour latitude, -180 / 180 pour longitude).

Logique métier dans `save()` :

```python
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
```

Tu peux expliquer à l’étudiant :
- `cleaned_data` = données propres après validation.
- on dérive les deux dates du modèle à partir d’un seul champ de formulaire.

----------------------------------------------------------------
5. Les vues (views.py) : le “cerveau” de chaque page
----------------------------------------------------------------

Les vues sont des fonctions (ici, pas de class-based views pour rester simple).

5.1. Vue `home`
---------------

```python
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')
```

- Si l’utilisateur est connecté, on le redirige vers le dashboard.
- Sinon, on affiche la page publique `home.html`.

5.2. Authentification : register / login / logout
-------------------------------------------------

- `register_view` :
  - si `POST` → on crée `RegisterForm(request.POST)`, on valide, on enregistre l’utilisateur, on le connecte, et on redirige vers le dashboard.
  - si `GET` → on affiche un formulaire vide.
  - messages succès/erreur via `django.contrib.messages`.

- `login_view` :
  - même logique avec `LoginForm`, et `login(request, form.get_user())`.

- `logout_view` :
  - appelle `logout(request)` et redirige vers `home`.

5.3. Dashboard
--------------

```python
@login_required
def dashboard_view(request):
    exploitations = Exploitation.objects.filter(utilisateur=request.user)
    context = {
        'exploitation_count': exploitations.count(),
        'exploitations': exploitations.select_related('culture', 'type_sol'),
    }
    return render(request, 'dashboard.html', context)
```

- `@login_required` : si non connecté → redirection vers la page de login.
- on passe au template :
  - le nombre de cultures
  - la liste des exploitations pour la table.

5.4. Création d’une exploitation
--------------------------------

`exploitation_create_view` :
- si `GET` → `form = ExploitationForm()`, on affiche `cultures/form.html`.
- si `POST` → `form = ExploitationForm(request.POST)` :
  - `form.is_valid()` :
    - si OK → `form.save(utilisateur=request.user)` puis redirection vers `dashboard`.
    - si KO → on réaffiche le formulaire avec les erreurs.

5.5. Analyse d’une exploitation
-------------------------------

`exploitation_analyse_view` :

- récupère l’`Exploitation` de l’utilisateur.
- appelle `DecisionEngine().analyze(exploitation)` (service métier).
- gère les erreurs (API météo KO, etc.) avec des messages.
- enregistre une `Analyse` historique avec le `resultat` JSON.
- affiche `cultures/analyse.html` avec :
  - `exploitation`
  - `resultat` (recommandations à afficher).

5.6. Historique des analyses
----------------------------

- `analyses_list_view` :
  - liste toutes les `Analyse` liées aux exploitations de l’utilisateur.
  - affiche dans `analyses/list.html`.

- `analyse_detail_view` :
  - récupère une `Analyse` par son `pk`, vérifie l’utilisateur.
  - réutilise le template `cultures/analyse.html` en mode lecture seule.

5.7. Pages d’erreur 404/403
---------------------------

- `error_404_view` et `error_403_view` :
  - utilisent des templates dédiés `errors/404.html` et `errors/403.html`.
  - branchés dans `AgriDec/urls.py` via `handler404` et `handler403`.

----------------------------------------------------------------
6. Routage : urls.py (projet + app)
----------------------------------------------------------------

6.1. AgriDec/urls.py
--------------------

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]
handler404 = 'core.views.error_404_view'
handler403 = 'core.views.error_403_view'
```

- `admin/` → interface d’administration Django (par défaut).
- `'': include('core.urls')` → tout le reste est délégué à l’app `core`.

6.2. core/urls.py
-----------------

```python
urlpatterns = [
  path('', views.home, name='home'),
  path('inscription/', views.register_view, name='register'),
  path('connexion/', views.login_view, name='login'),
  path('deconnexion/', views.logout_view, name='logout'),
  path('dashboard/', views.dashboard_view, name='dashboard'),
  path('cultures/nouvelle/', views.exploitation_create_view, name='exploitation_create'),
  path('cultures/<int:pk>/analyser/', views.exploitation_analyse_view, name='exploitation_analyse'),
  path('analyses/', views.analyses_list_view, name='analyses_list'),
  path('analyses/<int:pk>/', views.analyse_detail_view, name='analyse_detail'),
]
```

Syntaxe importante :
- `path('url/', vue, name='nom')`
- `<int:pk>` : paramètre d’URL converti en entier et passé à la vue.
- `name=` : permet d’utiliser `{% url 'analyse_detail' pk=analyse.pk %}` dans les templates.

----------------------------------------------------------------
7. Templates : HTML + langage de template Django
----------------------------------------------------------------

7.1. base.html
--------------

Template de base commun à tout le site :

- charge les CSS : `variables.css`, `base.css`, `layout.css`, `components.css`, `pages.css`.
- définit des **blocs** (`block`) :
  - `title`
  - `extra_css`
  - `body`
  - `extra_js`

Principe :
- les autres templates font `{% extends 'base.html' %}` puis remplissent ces blocs.

7.2. base_app.html
------------------

Spécial pour la partie “application” (quand l’utilisateur est connecté) :

- étend `base.html`
- ajoute :
  - la sidebar (`{% include 'partials/sidebar.html' %}`)
  - la topbar avec le titre de page (`{% block topbar_title %}`)
  - les messages (`partials/messages.html`)
- définit le bloc `content` où les pages comme `dashboard.html` et `cultures/form.html` mettent leur HTML.

7.3. Exemples concrets
----------------------

- `home.html` :
  - étend `base_public.html` (version publique de la base).
  - bloc `content` : hero, features, CTA (inscription / connexion).

- `dashboard.html` :
  - étend `base_app.html`.
  - utilise :
    - `{{ user.username }}` (provenant du context processor `auth`).
    - `{{ exploitation_count }}` et `{{ exploitations }}` (envoyés par la vue).
  - boucle `{% for exp in exploitations %}` pour afficher la table.

- `cultures/form.html` :
  - affiche les champs du formulaire un par un (`{{ form.culture }}`, `{{ form.type_sol }}`, etc.).
  - utilise `{{ form.non_field_errors }}` et `form.<champ>.errors` pour les messages d’erreur.

7.4. Syntaxe de base du langage de template
-------------------------------------------

- `{{ variable }}` → affiche une variable.
- `{% tag ... %}` → balise de contrôle (extends, if, for, url, include, etc.).
- `{% url 'nom_de_route' arg %}` → génère une URL à partir du nom de route.

----------------------------------------------------------------
8. Services : fao_service, weather_service, decision_engine
----------------------------------------------------------------

Pour garder les **vues** propres, la logique métier et les appels d’API sont mis dans `core/services/`.

8.1. fao_service.py
-------------------

- gère l’appel à l’API FAO Crop Calendar.
- fonctions pour :
  - récupérer les données FAO en ligne
  - normaliser les données
  - les stocker dans le modèle `FaoCalendrier`.

8.2. weather_service.py
-----------------------

- gère l’appel à l’API Open-Meteo (météo réelle).
- renvoie une structure JSON utilisée par le `DecisionEngine`.

8.3. decision_engine.py
-----------------------

- contient la “vraie” intelligence métier :
  - combine FAO + météo + données de l’exploitation.
  - renvoie un dictionnaire avec :
    - `peut_semer`
    - `arroser`
    - `recolte`
    - `risques`
    - `resume`
    - `meta` (sources, etc.).

Ce découpage permet d’expliquer à l’étudiant :
- **Views** = orchestration (entrées/sorties).
- **Services** = logique métier pure (réutilisable, testable).

----------------------------------------------------------------
9. Cycle complet d’une requête HTTP dans AgriDec
----------------------------------------------------------------

Exemple : un agriculteur envoie une nouvelle culture et lance une analyse.

1. L’utilisateur va sur `/cultures/nouvelle/` (GET).
2. `core/urls.py` → `exploitation_create_view`.
3. Vue :
   - crée un `ExploitationForm()`
   - envoie au template `cultures/form.html`.
4. Le template affiche le formulaire + JS de géolocalisation.
5. L’utilisateur valide → POST vers `/cultures/nouvelle/`.
6. Vue :
   - `form = ExploitationForm(request.POST)`
   - `form.is_valid()` :
     - valide la localisation GPS, le statut, etc.
     - `form.save(utilisateur=request.user)` crée `Exploitation` en base.
7. Redirection vers `/dashboard/` → nouvelle ligne dans le tableau.
8. L’utilisateur clique “Analyser” → `/cultures/<pk>/analyser/`.
9. Vue `exploitation_analyse_view` :
   - récupère l’`Exploitation`.
   - appelle `DecisionEngine().analyze(exploitation)` → appelle la météo, lit le calendrier FAO.
   - enregistre une `Analyse`.
   - renvoie le template `cultures/analyse.html` avec le résultat.

Tu peux dessiner ce flux sur un tableau pour l’étudiant.

----------------------------------------------------------------
10. Comment présenter ce projet à un étudiant
----------------------------------------------------------------

Plan de cours possible (en 1–2 séances) :

1. **Vue d’ensemble** :
   - Montrer rapidement la démo : inscription, nouvelle culture, analyse, historique.
   - Expliquer le but : aide à la décision agricole (FAO + météo).

2. **Architecture globale** :
   - Dossier `AgriDec/` (settings, urls).
   - Dossier `core/` (models, views, forms, urls, services).

3. **Modèles** :
   - Expliquer `Culture`, `TypeSol`, `Exploitation`, `Analyse`, `FaoCalendrier`.
   - Montrer la correspondance avec les tables MySQL.

4. **Formulaires** :
   - Montrer `ExploitationForm` → comment un seul champ `date_semis` alimente deux champs modèle.

5. **Vues & URLs** :
   - Prendre “Nouvelle culture” et “Analyse” comme cas pratiques.
   - Montrer l’enchaînement URL → vue → formulaire → modèle → template.

6. **Templates** :
   - Expliquer `extends`, `block`, `include`, `url`.
   - Voir `dashboard.html` et `cultures/form.html`.

7. **Services & API externes** :
   - Expliquer pourquoi on sort la logique métier dans `services/`.

Avec ce cours, même si tu “ne maîtrises pas encore Django”, tu peux expliquer :
- les concepts de base
- et **comment ils sont appliqués concrètement** dans AgriDec.


