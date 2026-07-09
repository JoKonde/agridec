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

================================================================
PARTIE 2 — COMMENT AGRIDEC FONCTIONNE (MÉTIER + CODE)
================================================================

Cette partie répond à la question : **à quoi sert vraiment AgriDec ?**
Et surtout : **comment FAO + GPS + météo + moteur de décision travaillent ensemble ?**

----------------------------------------------------------------
11. Vue d’ensemble : le problème qu’AgriDec résout
----------------------------------------------------------------

Un agriculteur en RDC se pose des questions simples mais importantes :

1. **Puis-je semer maintenant ?**
2. **Dois-je arroser aujourd’hui ?**
3. **Quand est-ce que je récolte ?**
4. **Y a-t-il des risques climatiques (pluie, chaleur, vent) ?**

AgriDec ne devine pas avec de l’IA. Il combine **3 sources de données réelles** :

| Source | Rôle | Quand ? |
|--------|------|---------|
| **FAO** (calendrier agricole) | Dit *en quels mois* on peut semer/récolter en RDC | Importé en base, consulté à l’analyse |
| **GPS** (latitude/longitude) | Dit *où* est la parcelle de l’agriculteur | Au formulaire “Nouvelle culture” |
| **Météo** (Open-Meteo) | Dit *quel temps* il fait et ce qui est prévu | À chaque analyse, en temps réel |

Le **moteur de décision** (`decision_engine.py`) est le chef d’orchestre :
il lit tout ça et produit des réponses en français compréhensibles.

Schéma du flux global :

```
[Agriculteur]
    │
    ├─► Inscription / Connexion
    │
    ├─► Nouvelle culture (formulaire + GPS)
    │       └─► Exploitation enregistrée en base (lat, lon, culture, sol, date)
    │
    └─► Bouton "Analyser"
            │
            ├─► Météo API (lat/lon) ──────────────┐
            ├─► Calendrier FAO (base MySQL) ────┤
            ├─► Données exploitation (base) ────┤
            │                                    ▼
            │                          DecisionEngine.analyze()
            │                                    │
            └─► Résultat JSON sauvegardé ◄───────┘
                    │
                    └─► Page analyse.html (recommandations)
```

----------------------------------------------------------------
12. L’API FAO : à quoi elle sert et comment on l’utilise
----------------------------------------------------------------

### 12.1. C’est quoi l’API FAO ?

La FAO (Organisation des Nations Unies pour l’alimentation) publie un **calendrier cultural**
pour chaque pays : quelles cultures, dans quelles zones, à quels mois semer et récolter.

- API officielle : https://api-cropcalendar.apps.fao.org/
- Pour la RDC : code pays `CD`
- Exemple d’URL : `/api/v1/countries/CD/cropCalendar`

**Utilité pour AgriDec :**
- savoir si **le mois actuel** est une bonne période de semis pour le maïs, le riz, etc.
- connaître la **durée de croissance** (ex. 110 jours) pour estimer la date de récolte
- afficher les **meilleures périodes** recommandées par zone (Sud-Ouest, Saison A…)

### 12.2. Pourquoi on n’appelle pas l’API FAO à chaque analyse ?

Parce que les calendriers FAO changent rarement. On fait donc :

1. **Import une fois** (ou quand on veut mettre à jour) → commande `import_fao_data`
2. **Stockage en base** → tables `Culture` et `FaoCalendrier`
3. **Consultation rapide** à l’analyse → lecture MySQL, pas d’appel HTTP

C’est plus rapide, plus fiable, et ça évite de dépendre de l’API FAO à chaque clic.

### 12.3. Où trouver le code FAO ?

| Fichier | Rôle |
|---------|------|
| `core/services/fao_service.py` | Client API + fonctions de consultation en base |
| `core/management/commands/import_fao_data.py` | Commande d’import `python manage.py import_fao_data --clear` |
| `core/models.py` → `Culture`, `FaoCalendrier` | Tables qui stockent les données importées |
| `AgriDec/settings.py` | Config : `FAO_API_BASE_URL`, `FAO_COUNTRY_CODE='CD'`, `FAO_LANGUAGE='fr'` |

### 12.4. Comment fonctionne l’import FAO (code expliqué)

**Étape 1 — Appel API** (`fao_service.py`, classe `FaoService`) :

```python
service = FaoService(country_code='CD', language='fr')
raw_entries = service.get_crop_calendar()
```

- `get_crop_calendar()` fait un GET HTTP vers l’API FAO
- retourne du JSON brut (liste de cultures, zones, sessions de semis/récolte)

**Étape 2 — Normalisation** (`normalize_calendar_entries()`) :

L’API renvoie un format complexe. Cette fonction le transforme en dictionnaires simples :

```python
{
    'fao_crop_id': '56',
    'crop_name': 'Maïs',
    'zone_aez': 'Sud Ouest',
    'session_info': 'Saison A',
    'mois_semis_debut': 9,
    'mois_semis_fin': 11,
    'mois_recolte_debut': 1,
    'mois_recolte_fin': 3,
    'growing_period_jours': 120,
}
```

**Étape 3 — Sauvegarde en base** (`import_fao_data.py`) :

- `Culture.objects.update_or_create(fao_crop_id=...)` → crée ou met à jour la culture
- `FaoCalendrier.objects.update_or_create(...)` → crée ou met à jour le calendrier

Commande à lancer :

```bash
python manage.py import_fao_data --clear
```

### 12.5. Comment le moteur lit le FAO à l’analyse ?

Fonctions dans `fao_service.py` (consultation base, pas API) :

| Fonction | Ce qu’elle fait |
|----------|-----------------|
| `get_calendriers_culture(culture)` | Tous les calendriers FAO d’une culture en RDC |
| `est_dans_periode_semis(culture, mois)` | Le mois actuel est-il une période de semis ? |
| `get_periodes_semis_texte(culture)` | Texte lisible : "septembre – novembre (Sud Ouest)" |
| `mois_dans_periode(mois, debut, fin)` | Gère les périodes qui chevauchent l’année (ex. nov → fév) |

Exemple d’utilisation dans `decision_engine.py` :

```python
mois_actuel = today.month  # ex. 9 = septembre
dans_periode, cal_ref = est_dans_periode_semis(culture, mois_actuel)
# dans_periode = True/False
# cal_ref = l’objet FaoCalendrier correspondant (zone, session)
```

----------------------------------------------------------------
13. La géolocalisation GPS : pourquoi et comment
----------------------------------------------------------------

### 13.1. Pourquoi le GPS est indispensable ?

La météo **n’est pas la même partout**. Kinshasa ≠ Lubumbashi ≠ Goma.

Sans GPS, AgriDec ne saurait pas quelle météo demander à Open-Meteo.
Le GPS transforme la position de l’agriculteur en **coordonnées numériques** :

- `latitude` : -4.325000 (ex. Kinshasa)
- `longitude` : 15.322000

Ces deux nombres sont ensuite utilisés pour l’appel météo.

### 13.2. Où trouver le code GPS ?

| Fichier | Rôle |
|---------|------|
| `static/js/geolocation.js` | Détecte la position via le navigateur (HTML5 Geolocation API) |
| `templates/cultures/form.html` | Affiche le bloc GPS + champs cachés lat/lon |
| `core/forms.py` → `ExploitationForm` | Valide que lat/lon sont présents et dans les bonnes bornes |
| `core/models.py` → `Exploitation` | Stocke `latitude` et `longitude` en base (`DecimalField`) |

### 13.3. Comment ça marche côté navigateur (geolocation.js)

Quand l’agriculteur ouvre “Nouvelle culture”, le JavaScript s’exécute :

```javascript
navigator.geolocation.getCurrentPosition(onSuccess, onError, {
  enableHighAccuracy: true,
  timeout: 15000,
});
```

**Si succès** (`onSuccess`) :
- récupère `position.coords.latitude` et `position.coords.longitude`
- remplit les champs cachés `#id_latitude` et `#id_longitude`
- active le bouton “Enregistrer”
- affiche les coordonnées à l’écran

**Si échec** (`onError`) :
- message d’erreur (permission refusée, GPS désactivé, timeout)
- bouton “Enregistrer” reste désactivé

**Pourquoi des champs cachés ?**
- L’utilisateur ne tape pas les coordonnées à la main
- Le JS les remplit automatiquement
- Django les reçoit comme des champs normaux du formulaire POST

### 13.4. Validation côté serveur (forms.py)

Le navigateur peut être contourné. Django vérifie donc côté serveur :

```python
def clean(self):
    latitude = cleaned_data.get('latitude')
    longitude = cleaned_data.get('longitude')
    if latitude is None or longitude is None:
        raise ValidationError('La localisation GPS est obligatoire.')
    if not (-90 <= float(latitude) <= 90):
        raise ValidationError({'latitude': 'Latitude invalide.'})
    if not (-180 <= float(longitude) <= 180):
        raise ValidationError({'longitude': 'Longitude invalide.'})
```

**Double sécurité** : JS côté client + validation Django côté serveur.

----------------------------------------------------------------
14. La météo Open-Meteo : à quoi elle sert
----------------------------------------------------------------

### 14.1. Pourquoi la météo ?

Le calendrier FAO dit *“septembre–novembre c’est la saison de semis”*.
Mais il ne dit pas s’il pleut **aujourd’hui** ou s’il fera 40°C demain.

La météo apporte le **contexte immédiat** :
- température actuelle et prévue
- humidité de l’air
- probabilité et quantité de pluie
- vitesse du vent

### 14.2. Où trouver le code météo ?

| Fichier | Rôle |
|---------|------|
| `core/services/weather_service.py` | Client Open-Meteo + parsing de la réponse |
| `AgriDec/settings.py` | Config : `WEATHER_API_BASE_URL`, `WEATHER_FORECAST_DAYS=7` |
| `core/management/commands/test_weather.py` | Commande test : `python manage.py test_weather` |
| `core/tests.py` | Tests d’intégration API réelle |

### 14.3. Comment fonctionne l’appel météo (code expliqué)

**Point d’entrée** — fonction `fetch_weather(latitude, longitude)` :

```python
def fetch_weather(latitude, longitude, days=None):
    service = get_weather_service()  # lit settings.WEATHER_SERVICE_CLASS
    return service.get_forecast(latitude, longitude, days=days)
```

**Appel HTTP** (`OpenMeteoWeatherService._fetch()`) :

Construit une URL comme :
```
https://api.open-meteo.com/v1/forecast?latitude=-4.325&longitude=15.322
  &daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,...
  &forecast_days=7&timezone=Africa/Kinshasa
```

**Parsing** (`parse_open_meteo_response()`) :

Transforme le JSON brut de l’API en structure AgriDec standardisée :

```python
{
    'source': 'open-meteo',
    'current': {
        'temperature': 28.5,
        'humidite': 72,
        'probabilite_pluie': 45,
        'pluie_mm': 2.1,
        'vent_kmh': 12.0,
    },
    'forecast': [
        {'date': '2026-07-09', 'temperature': 29.0, 'humidite': 68, ...},
        {'date': '2026-07-10', 'temperature': 31.0, 'humidite': 55, ...},
        # ... 7 jours
    ],
}
```

**Pourquoi cette structure standardisée ?**
- Le moteur de décision ne connaît pas Open-Meteo directement
- Il lit toujours `current` et `forecast` de la même façon
- On pourrait changer d’API météo sans toucher au moteur (pattern interface)

### 14.4. Quand la météo est-elle appelée ?

**À chaque analyse**, pas à l’import ni à l’enregistrement de la culture.

Dans `decision_engine.py`, ligne 43-46 :

```python
meteo = fetch_weather(
    float(exploitation.latitude),
    float(exploitation.longitude),
)
```

Les coordonnées GPS stockées dans `Exploitation` sont donc **réutilisées** ici.

----------------------------------------------------------------
15. Le moteur de décision : le cœur d’AgriDec
----------------------------------------------------------------

### 15.1. Où le trouver ?

| Fichier | Rôle |
|---------|------|
| `core/services/decision_engine.py` | Toute la logique de recommandation |
| `core/views.py` → `exploitation_analyse_view` | Appelle le moteur et affiche le résultat |
| `templates/cultures/analyse.html` | Affiche les recommandations à l’utilisateur |
| `core/models.py` → `Analyse` | Sauvegarde le résultat JSON en historique |

### 15.2. Comment il est déclenché ?

1. L’agriculteur clique “Analyser” sur le dashboard
2. URL : `/cultures/<pk>/analyser/`
3. Vue `exploitation_analyse_view` dans `core/views.py` :

```python
exploitation = get_object_or_404(Exploitation, pk=pk, utilisateur=request.user)
resultat = DecisionEngine().analyze(exploitation)
Analyse.objects.create(exploitation=exploitation, resultat=resultat)
return render(request, 'cultures/analyse.html', {
    'exploitation': exploitation,
    'resultat': resultat,
})
```

### 15.3. La méthode principale : `analyze(exploitation)`

Voici ce qu’elle fait, étape par étape :

```
analyze(exploitation)
│
├─ 1. fetch_weather(lat, lon)           → météo actuelle + 7 jours
├─ 2. get_calendriers_culture(culture)   → calendrier FAO en base
├─ 3. est_dans_periode_semis(culture, mois_actuel)  → bon mois FAO ?
│
├─ 4. _evaluer_semis()      → Puis-je semer ?
├─ 5. _evaluer_arrosage()   → Dois-je arroser ?
├─ 6. _evaluer_recolte()    → Quand récolter ?
├─ 7. _evaluer_risques()    → Quels risques climatiques ?
├─ 8. _generer_resume()     → Résumé en une phrase
│
└─ retourne un dict JSON structuré
```

### 15.4. Les règles métier (seuils)

En haut de `decision_engine.py`, des constantes définissent les seuils :

```python
SEUIL_TEMP_SEMIS_MIN = 18      # °C minimum pour semer
SEUIL_TEMP_SEMIS_MAX = 38      # °C maximum pour semer
SEUIL_PLUIE_SEMIS_MM = 15      # mm de pluie = trop pour semer
SEUIL_PROBA_PLUIE_SEMIS = 60   # % probabilité pluie = risque
SEUIL_HUMIDITE_ARROSAGE = 55   # % humidité en dessous = arroser
SEUIL_VENT_RISQUE = 35         # km/h = vent dangereux
```

Ce ne sont **pas** des valeurs magiques : ce sont des règles agronomiques simplifiées,
choisies pour un projet académique. Un agronome pourrait les ajuster.

### 15.5. Détail de chaque évaluation

#### A) Puis-je semer ? — `_evaluer_semis()`

**Conditions pour répondre OUI** (toutes doivent être vraies) :

| Critère | Source | Règle |
|---------|--------|-------|
| Période FAO | FAO (base) | Le mois actuel est dans la fenêtre de semis |
| Température | Météo (current) | Entre 18°C et 38°C |
| Pluie proche | Météo (forecast 3j) | Pas de forte pluie prévue |
| Sol | Exploitation | Sol sablonneux + humidité < 45% = trop sec |
| Statut | Exploitation | Si déjà semé → toujours NON |

**Exemple de réponse produite :**

```python
{
    'reponse': True,
    'explication': 'Nous sommes en période de semis FAO pour le Maïs (Sud Ouest, Saison A). '
                   'La température actuelle (27°C) est favorable au semis. '
                   'Les précipitations prévues sur les 3 prochains jours sont acceptables.'
}
```

#### B) Dois-je arroser ? — `_evaluer_arrosage()`

**Logique :**
- Si statut = `A_SEMER` (pas encore semé) → NON, pas besoin d’arroser
- Si statut = `DEJA_SEME` → on regarde :
  - humidité < 55% ?
  - peu de pluie prévue demain ?
  - → si oui aux deux : OUI, arroser

#### C) Quand récolter ? — `_evaluer_recolte()`

**Formule simple :**

```
date_recolte = date_semis + durée_croissance_jours
```

- `date_semis` = date réelle ou prévue selon le statut
- `durée_croissance` = `culture.duree_recolte_jours` ou `FaoCalendrier.growing_period_jours`

Exemple : semis le 01/09/2026 + 120 jours FAO → récolte estimée le 30/12/2026

#### D) Risques climatiques — `_evaluer_risques()`

Parcourt les 7 jours de prévision et détecte :

| Type de risque | Condition |
|----------------|-----------|
| Fortes pluies | pluie > 25 mm ou probabilité > 80% |
| Chaleur excessive | température > 38°C |
| Froid | température min < 10°C |
| Vent fort | vent > 35 km/h |
| Sécheresse | humidité < 40% et pluie < 1 mm |

Retourne une liste de risques avec niveau (faible / modéré / élevé) et description.

### 15.6. Structure du résultat final

```python
{
    'peut_semer': {'reponse': True/False, 'explication': '...'},
    'meilleure_periode_semis': {
        'periodes': 'septembre – novembre (Sud Ouest) ; ...',
        'explication': 'Selon le calendrier FAO...'
    },
    'arroser': {'reponse': True/False, 'explication': '...'},
    'recolte': {
        'date_estimee': '2026-12-30',
        'date_estimee_affichage': '30/12/2026',
        'explication': '...'
    },
    'risques': [
        {'type': 'Fortes pluies', 'niveau': 'élevé', 'description': '...'},
        ...
    ],
    'resume': 'Analyse pour votre Maïs (sol Limoneux). Les conditions semblent favorables...',
    'meta': {
        'culture': 'Maïs',
        'type_sol': 'Limoneux',
        'source_meteo': 'open-meteo',
        'date_analyse': '2026-07-09'
    }
}
```

Ce dict est :
1. **affiché** dans `templates/cultures/analyse.html`
2. **sauvegardé** dans `Analyse.resultat` (JSONField) pour l’historique

----------------------------------------------------------------
16. Comment tout se marie : le scénario complet
----------------------------------------------------------------

Prenons un agriculteur à Kinshasa qui veut planter du maïs.

### Étape 1 — Préparation (admin / une fois)

```bash
python manage.py import_fao_data --clear
```

→ 29 cultures + 173 calendriers FAO pour la RDC en base MySQL.

### Étape 2 — L’agriculteur s’inscrit

- Vue : `register_view` → crée un `User` Django
- Rien à voir avec FAO/météo pour l’instant.

### Étape 3 — Nouvelle culture

L’agriculteur remplit le formulaire :

| Champ | Valeur | Source |
|-------|--------|--------|
| Culture | Maïs | Liste `Culture` (importée FAO) |
| Type de sol | Limoneux | Liste `TypeSol` (load_initial_data) |
| Statut | Je vais semer | Choix utilisateur |
| Date | 15/09/2026 | Saisie utilisateur |
| Latitude | -4.325000 | **GPS automatique** (geolocation.js) |
| Longitude | 15.322000 | **GPS automatique** (geolocation.js) |

→ `Exploitation` créée en base avec toutes ces infos.

### Étape 4 — Analyse

L’agriculteur clique “Analyser”. Le moteur fait :

```
1. fetch_weather(-4.325, 15.322)
   → Open-Meteo renvoie : 27°C, humidité 72%, pluie 2mm demain...

2. est_dans_periode_semis(Maïs, septembre=9)
   → FAO dit : OUI, septembre est dans la fenêtre Sud Ouest Saison A

3. _evaluer_semis()
   → FAO OK + température OK + pas de forte pluie = OUI, vous pouvez semer

4. _evaluer_arrosage()
   → Statut = A_SEMER → NON, pas encore semé

5. _evaluer_recolte()
   → 15/09/2026 + 120 jours = récolte vers 13/01/2027

6. _evaluer_risques()
   → Pas de risque majeur sur les 7 prochains jours

7. Résultat affiché + sauvegardé dans Analyse
```

### Étape 5 — Historique

L’agriculteur peut revoir cette analyse plus tard via `/analyses/`
sans refaire d’appel API (données déjà en JSON dans `Analyse.resultat`).

----------------------------------------------------------------
17. Carte complète du code : où trouver quoi ?
----------------------------------------------------------------

### Par fonctionnalité

| Fonctionnalité | Fichiers principaux |
|----------------|---------------------|
| **Inscription / Connexion** | `core/forms.py` (RegisterForm, LoginForm), `core/views.py`, `templates/auth/` |
| **Dashboard** | `core/views.py` → `dashboard_view`, `templates/dashboard.html` |
| **GPS / Géolocalisation** | `static/js/geolocation.js`, `templates/cultures/form.html`, `core/forms.py` (validation) |
| **Formulaire culture** | `core/forms.py` → `ExploitationForm`, `templates/cultures/form.html` |
| **Import FAO** | `core/services/fao_service.py`, `core/management/commands/import_fao_data.py` |
| **Consultation FAO** | `core/services/fao_service.py` (get_calendriers, est_dans_periode_semis…) |
| **API Météo** | `core/services/weather_service.py` |
| **Moteur de décision** | `core/services/decision_engine.py` |
| **Page d’analyse** | `core/views.py` → `exploitation_analyse_view`, `templates/cultures/analyse.html` |
| **Historique analyses** | `core/views.py` → `analyses_list_view`, `analyse_detail_view`, `templates/analyses/` |
| **Modèles / Base de données** | `core/models.py`, `core/migrations/` |
| **Configuration APIs** | `AgriDec/settings.py` (lignes FAO_* et WEATHER_*) |
| **Routes URL** | `core/urls.py`, `AgriDec/urls.py` |
| **CSS / JS** | `static/css/`, `static/js/` |
| **Tests** | `core/tests.py` |
| **Commandes management** | `core/management/commands/` |

### Par couche technique

```
COUCHE PRÉSENTATION (ce que voit l'utilisateur)
├── templates/                    → HTML Django
├── static/css/                   → Styles
└── static/js/                    → JavaScript (GPS, menu mobile)

COUCHE CONTRÔLEUR (orchestration)
├── core/views.py                 → Vues Django
├── core/forms.py                 → Formulaires
└── core/urls.py                  → Routage

COUCHE MÉTIER (logique agricole)
├── core/services/decision_engine.py  → Moteur de décision
├── core/services/fao_service.py      → FAO (API + consultation)
└── core/services/weather_service.py  → Météo Open-Meteo

COUCHE DONNÉES (persistance)
├── core/models.py                → Modèles Django / tables MySQL
└── core/migrations/              → Évolution du schéma

COUCHE CONFIGURATION
├── AgriDec/settings.py           → Config globale
├── AgriDec/urls.py               → URLs racine
└── .env                          → Secrets (non commité)

COUCHE OUTILS
└── core/management/commands/     → import_fao_data, load_initial_data, test_weather
```

----------------------------------------------------------------
18. Ce qu’il faut retenir pour expliquer à un étudiant
----------------------------------------------------------------

**En une phrase :**
> AgriDec aide un agriculteur congolais à décider quand semer, arroser et récolter,
> en croisant le calendrier officiel FAO, la météo réelle à sa position GPS,
> et des règles métier simples et transparentes.

**Les 4 piliers à retenir :**

1. **FAO** = le “quand” agronomique (mois de semis/récolte) → importé en base
2. **GPS** = le “où” (coordonnées de la parcelle) → détecté par le navigateur
3. **Météo** = le “maintenant” (température, pluie, vent) → API temps réel
4. **Moteur** = le “donc” (recommandation finale) → règles Python explicites

**Ce qu’AgriDec n’est PAS :**
- Pas d’intelligence artificielle / machine learning
- Pas de données fictives ou simulées
- Pas un substitut à un agronome sur le terrain
- Pas un produit commercial (projet académique)

**Plan de démo pour un étudiant (15 minutes) :**

1. Montrer la page d’accueil → expliquer le but
2. S’inscrire → montrer que c’est du Django classique (form + view)
3. Créer une culture → montrer le GPS en action (autoriser la localisation)
4. Lancer une analyse → expliquer que 3 sources de données sont croisées
5. Lire les recommandations → montrer le template analyse.html
6. Ouvrir le code : decision_engine.py → montrer les règles simples
7. Montrer l’historique → expliquer la sauvegarde JSON

Avec ce cours complet (Partie 1 Django + Partie 2 Métier), tu as tout ce qu’il faut
pour comprendre et expliquer AgriDec de A à Z.

