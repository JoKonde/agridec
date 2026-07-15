# AgriDec — Agriculture Decision System

> **Projet académique** — Application web d'aide à la décision agricole pour la République Démocratique du Congo (RDC).

AgriDec aide les agriculteurs à décider **quand semer**, **s'il faut arroser**, **quand récolter** et **quels risques** surveiller, en croisant :

- le **calendrier cultural FAO** (données officielles RDC) ;
- les **prévisions météo Open-Meteo** (temps réel) ;
- un **modèle de machine learning** entraîné sur des observations agricoles africaines (**One Acre Fund** + **LSMS-ISA**).

Pas de données fictives métier : APIs réelles, enquêtes terrain Afrique, et règles FAO en secours si le modèle n’est pas chargé.

**Dépôt GitHub :** [github.com/JoKonde/agirdec](https://github.com/JoKonde/agirdec)

---

## Fonctionnalités

- Inscription et connexion des agriculteurs
- Création d'une exploitation (culture, type de sol, géolocalisation GPS)
- Analyse automatique : semis, irrigation, récolte, risques
- Recommandations assistées par **ML** (modèle entraîné Afrique) + calendrier FAO + météo
- Historique des analyses sauvegardées
- Import du calendrier FAO pour la RDC (code pays `CD`)

---

## Stack technique

| Couche        | Technologie                          |
|---------------|--------------------------------------|
| Backend       | Django 6.x, Python 3.10+             |
| Base de données | MySQL 8+                           |
| Frontend      | Django Templates, CSS pur, JS Vanilla |
| APIs externes | FAO Crop Calendar, Open-Meteo      |
| Machine learning | scikit-learn (Random Forest multi-sorties), pandas, joblib |

---

## Datasets ML (One Acre Fund + LSMS-ISA)

AgriDec utilise deux sources **ouvertes** d’observations agricoles en Afrique pour entraîner le modèle qui aide à répondre aux 4 questions : **semer**, **arroser**, **récolter**, **risques**.

### 1) One Acre Fund — Maize survey (Afrique subsaharienne)

| | |
|--|--|
| **Page / DOI** | [Zenodo record 11122388](https://zenodo.org/records/11122388) |
| **URL de téléchargement CSV** | https://zenodo.org/records/11122388/files/One_Acre_Fund_MEL_maize_survey_data_2016-2022.csv?download=1 |
| **Fichier local attendu** | `ml/datasets/raw/one_acre_fund_maize.csv` |
| **Contenu** | ~14 700 parcelles de **maïs** (2016–2022) : pays (Kenya, Tanzanie, Rwanda, Zambie, Burundi, Nigeria, Ouganda…), GPS, **date de semis**, **date de récolte**, sol, climat saisonnier, rendement, adversités (`water_excess`, `disease`, `pest`, `striga`…) |

### 2) LSMS-ISA — Banque mondiale (Afrique)

| | |
|--|--|
| **Page projet** | [LSMS-ISA (World Bank)](https://www.worldbank.org/en/programs/lsms/initiatives/lsms-isa) |
| **Jeu harmonisé (article)** | [Scientific Data — panel Afrique](https://www.nature.com/articles/s41597-025-05639-9) |
| **Téléchargement Zenodo v2.0** | [zenodo.org/records/15773365](https://zenodo.org/records/15773365) |
| **URL Plotcrop (semis / récolte / chocs)** | https://zenodo.org/records/15773365/files/Plotcrop_dataset.dta?download=1 |
| **URL Plot (irrigation, sol)** | https://zenodo.org/records/15773365/files/Plot_dataset.dta?download=1 |
| **Fichiers locaux attendus** | `ml/datasets/raw/lsms_plotcrop.dta`, `ml/datasets/raw/lsms_plot.dta` |
| **Contenu utile** | Cultures variées, **mois de semis** / **mois de récolte**, production, chocs (`drought_shock`, `rain_shock`, `flood_shock`, `pests_shock`…), et sur le fichier Plot : **`irrigated`** (parcelle irriguée ou non) |

> Les mois LSMS sont au format **Stata** (nombre de mois depuis janvier 1960). Le script d’adaptation les convertit en mois calendaires 1–12.

### Pays, cultures et types de sol (contenu réel des fichiers téléchargés)

Inventaire issu des fichiers dans `ml/datasets/raw/` (pas inventé).

#### One Acre Fund (`one_acre_fund_maize.csv`) — **14 773** observations

| Dimension | Contenu |
|-----------|---------|
| **Pays** | Kenya (7 258), Tanzanie (3 710), Rwanda (2 080), Zambie (861), Burundi (640), Nigeria (115), Ouganda (109) — codes ISO : `KEN`, `TZA`, `RWA`, `ZMB`, `BDI`, `NGA`, `UGA` |
| **Culture** | **Maïs uniquement** (dataset dédié « maize survey ») |
| **Type de sol** | Pas de libellé « Sablonneux / Argileux… » : le fichier donne surtout **`soil_clay`** (% d’argile), **`soil_pH`**, carbone organique, etc. |

Répartition approximative du sol via `% argile` (`soil_clay`, quand renseigné) — mapping utilisé ensuite par AgriDec :

| Type AgriDec (approx.) | Critère | Observations |
|------------------------|---------|--------------|
| Sablonneux | argile &lt; 20 % | 412 |
| Limoneux | 20–35 % | 3 108 |
| Argileux | 35–50 % | 6 778 |
| Latéritique / très argileux | ≥ 50 % | 34 |
| Non renseigné | `soil_clay` manquant | 4 441 |

pH du sol (quand renseigné) : environ **4,7 à 7,0** (moyenne ~5,7).

#### LSMS-ISA Plotcrop (`lsms_plotcrop.dta`) — **514 665** lignes culture × parcelle

| Dimension | Contenu |
|-----------|---------|
| **Pays** | Ouganda (179 496), Éthiopie (98 415), Tanzanie (74 585), Nigeria (62 905), Malawi (40 332), Mali (34 984), Niger (23 948) |
| **Cultures** | Très nombreuses dénominations brutes (~1 400 libellés, souvent synonymes / langues locales). Principales familles après regroupement : **maïs**, **manioc**, **haricots**, **sorgho**, **banane**, **mil**, **arachide**, **café**, **riz**, **mangue**, **pomme de terre**, **niébé**, **patate douce**, **teff**, **igname**, **enset**, **blé**, **avocat**, **orge**, **coton**, **soja**, etc. |
| **Type de sol** | **Absent** dans Plotcrop (pas de colonne type de sol textuel) |

#### LSMS-ISA Plot (`lsms_plot.dta`) — **263 195** parcelles

| Dimension | Contenu |
|-----------|---------|
| **Pays** | Éthiopie (76 622), Ouganda (56 610), Mali (33 720), Nigeria (32 141), Tanzanie (27 783), Malawi (25 930), Niger (10 389) |
| **Culture** | Culture principale de la parcelle (`main_crop` / parts par famille) — détail culture × parcelle surtout dans **Plotcrop** |
| **Type de sol** | Pas de nom de sol type AgriDec ; plutôt **`soil_fertility_index`** (indice numérique) + zone agro-écologique (`agro_ecological_zone`). L’adaptation AgriDec convertit l’indice en **Sablonneux / Limoneux / Argileux** (voir `build_agridec_dataset.py`). |
| **Irrigation** | `irrigated` : oui ≈ 6 338 · non ≈ 244 882 · manquant ≈ 11 975 |

> **Note RDC :** aucun des deux jeux ne contient la **République Démocratique du Congo**. Ce sont des données **Afrique subsaharienne** proches du contexte (cultures, climat tropical, petits producteurs). AgriDec les utilise comme base d’apprentissage, puis croise avec le **calendrier FAO RDC** et la **météo Open-Meteo** du GPS de l’agriculteur.

### Ce que ces datasets ont (utile pour AgriDec)

| Info | One Acre Fund | LSMS-ISA |
|------|---------------|----------|
| Dates / mois de **semis** | Oui (`plant_date`) | Oui (`planting_month`) |
| Dates / mois de **récolte** | Oui (`harvest_date`) | Oui (`harvest_end_month`) |
| **Risques** / chocs terrain | Oui (excès d’eau, maladies, ravageurs…) | Oui (sécheresse, pluie, inondation, ravageurs…) |
| Sol / localisation | Oui | Oui (GPS EA + indices sol) |
| Culture | Maïs | Plusieurs cultures |
| Irrigation | Non (proxy via pluie saisonnière) | Oui (`irrigated` sur Plot) |

### Ce qui manque par rapport aux 4 questions AgriDec

Les sources **ne contiennent pas** telles quelles les colonnes :

- `peut_semer` (Oui/Non pour le mois courant)
- `doit_arroser` (Oui/Non aujourd’hui)
- `pret_a_recolter` (Oui/Non pour le mois courant)
- `risque_*` déjà formatés pour l’UI AgriDec

Il n’y a pas non plus de météo **journalière** type Open-Meteo liée à chaque décision (surtout LSMS).  
L’**arrosage quotidien** n’est pas observé : on dispose surtout d’une pratique d’irrigation (LSMS) ou d’un proxy saisonnier (One Acre Fund).

### Comment on les a adaptés → dataset AgriDec

Fichier produit : `ml/datasets/processed/agridec_training.csv`  
Script : `ml/scripts/build_agridec_dataset.py`

**Idée d’adaptation (mois observés → labels Oui/Non) :**

1. Pour chaque parcelle, on lit le **mois de semis** et le **mois de récolte** réellement observés.
2. On crée **12 lignes** (mois = 1 … 12) avec les mêmes caractéristiques (culture, sol, GPS, météo/saison, risques).
3. Labels :
   - `peut_semer = 1` **uniquement** si `mois == mois_de_semis_observé` (sinon 0) ;
   - `pret_a_recolter = 1` **uniquement** si `mois == mois_de_recolte_observé` ;
   - `doit_arroser = 1` pendant la saison de culture si la parcelle est **irriguée** (LSMS) ou si la saison est **peu pluvieuse** (One Acre Fund) ;
   - `risque_secheresse`, `risque_pluie_forte`, `risque_ravageurs`, `risque_maladie` = chocs / adversités déclarés sur la parcelle.

Ainsi le modèle apprend : *« pour ce type de culture / lieu / conditions, tel mois est un mois de semis (ou de récolte), et tel profil est associé à un besoin d’eau ou à un risque »*.

### Scripts de téléchargement, adaptation et entraînement

Tous les scripts sont dans `ml/scripts/` (avec commentaires explicatifs) :

| Script | Rôle |
|--------|------|
| `download_datasets.py` | **Télécharge** One Acre Fund + LSMS-ISA vers `ml/datasets/raw/` |
| `build_agridec_dataset.py` | **Adapte** les mois observés → labels `peut_semer` / `doit_arroser` / `pret_a_recolter` / risques |
| `train_agridec_model.py` | **Entraîne** le Random Forest multi-sorties |
| `run_ml_pipeline.py` | Enchaîne les 3 étapes automatiquement |

```bash
# Option A — pipeline complet (recommandé)
python ml/scripts/run_ml_pipeline.py

# Option B — étape par étape
python ml/scripts/download_datasets.py
# ou : python manage.py download_ml_datasets

python ml/scripts/build_agridec_dataset.py
# ou : python manage.py build_ml_dataset

python ml/scripts/train_agridec_model.py
# ou : python manage.py train_ml_model

# Re-télécharger même si les fichiers existent déjà
python ml/scripts/download_datasets.py --force
```

Artefact : `ml/artifacts/agridec_model.joblib`  
Utilisation : `core/services/ml_predictor.py` appelé par `decision_engine.py`  
Si le modèle est absent, AgriDec continue avec les **règles métier** seules (`USE_ML_MODEL` dans `settings.py`).

---

## Prérequis

Avant de commencer, assurez-vous d'avoir installé :

- **Python 3.10** ou supérieur
- **MySQL 8** (ou MariaDB compatible)
- **Git**
- Une **connexion Internet** (requise pour les APIs FAO et météo)

---

## Installation

### 1. Cloner le projet

```bash
git clone https://github.com/JoKonde/agirdec.git
cd agirdec
```

### 2. Créer un environnement virtuel

**Windows (PowerShell / CMD) :**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS :**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Créer la base de données MySQL

Connectez-vous à MySQL et créez la base `agridec` :

```sql
CREATE DATABASE IF NOT EXISTS agridec
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Ou en une ligne depuis le terminal :

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS agridec CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 5. Configurer les variables d'environnement (recommandé)

Copiez le fichier d'exemple et adaptez les valeurs si besoin :

**Windows :**

```bash
copy .env.example .env
```

**Linux / macOS :**

```bash
cp .env.example .env
```

Paramètres par défaut dans `.env` :

```env
DJANGO_SECRET_KEY=changez-moi-en-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=agridec
DB_USER=root
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=3306
```

#### `DJANGO_SECRET_KEY` — à quoi ça sert ?

La **clé secrète Django** (`SECRET_KEY`) est une chaîne aléatoire utilisée par le framework pour des opérations cryptographiques internes, notamment :

- le **chiffrement des sessions** utilisateur (connexion, panier, etc.) ;
- la protection **CSRF** (jetons anti-falsification des formulaires) ;
- la signature des **cookies** et de certains liens temporaires ;
- le hachage de données sensibles côté Django.

**En développement**, AgriDec peut fonctionner avec la clé par défaut définie dans `settings.py`.  
**En production** (ou sur un serveur accessible au public), vous **devez** générer une clé unique et la placer dans `.env` — ne jamais la partager ni la commiter sur GitHub.

#### Comment générer une `DJANGO_SECRET_KEY` ?

Avec Django déjà installé (`pip install -r requirements.txt`), exécutez :

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Exemple de sortie :

```
django-insecure-a8k2!x9m#p4v@7n$q1w&z5e_r3t6y+u0i-o=p
```

Copiez la valeur affichée et collez-la dans votre fichier `.env` :

```env
DJANGO_SECRET_KEY=django-insecure-a8k2!x9m#p4v@7n$q1w&z5e_r3t6y+u0i-o=p
```

> Ne commitez **jamais** le fichier `.env` (il contient des secrets). Le fichier `.gitignore` du projet l'exclut déjà.

---

## Démarrage du projet

Une fois l'installation terminée, exécutez les commandes suivantes **dans l'ordre** :

```bash
# Générer les fichiers de migration (si nécessaire)
python manage.py makemigrations

# Appliquer les migrations sur MySQL
python manage.py migrate

# Charger les types de sol de référence
python manage.py load_initial_data

# Importer les cultures et le calendrier FAO pour la RDC
python manage.py import_fao_data --clear

# (Optionnel) Machine learning — après avoir placé les datasets dans ml/datasets/raw/
# python manage.py build_ml_dataset
# python manage.py train_ml_model

# Lancer le serveur de développement
python manage.py runserver
```

Ouvrez ensuite votre navigateur à l'adresse :

**http://127.0.0.1:8000/**

---

## Parcours utilisateur

| Étape | URL | Description |
|-------|-----|-------------|
| 1 | `/inscription/` | Créer un compte agriculteur |
| 2 | `/connexion/` | Se connecter |
| 3 | `/dashboard/` | Tableau de bord |
| 4 | `/cultures/nouvelle/` | Ajouter une culture (GPS automatique) |
| 5 | `/cultures/<id>/analyser/` | Lancer une analyse |
| 6 | `/analyses/` | Consulter l'historique |

---

## Commandes utiles

| Commande | Description |
|----------|-------------|
| `python manage.py runserver` | Démarrer le serveur local |
| `python manage.py makemigrations` | Générer les migrations Django |
| `python manage.py migrate` | Appliquer les migrations |
| `python manage.py load_initial_data` | Charger les types de sol |
| `python manage.py import_fao_data --clear` | Importer le calendrier FAO (RDC) |
| `python manage.py test_weather` | Tester l'API météo (Kinshasa) |
| `python manage.py download_ml_datasets` | Télécharger One Acre Fund + LSMS-ISA (raw) |
| `python manage.py build_ml_dataset` | Adapter One Acre Fund + LSMS → CSV d'entraînement |
| `python manage.py train_ml_model` | Entraîner et sauvegarder le modèle ML |
| `python manage.py test` | Lancer les tests (APIs réelles) |
| `python manage.py check` | Vérifier la configuration Django |

---

## Architecture

```
AgriDec/
├── manage.py
├── requirements.txt
├── core/
│   ├── models.py              # Culture, Exploitation, Analyse, FaoCalendrier…
│   ├── views.py               # Pages web
│   ├── forms.py               # Formulaires
│   ├── services/
│   │   ├── fao_service.py     # API + consultation FAO en base
│   │   ├── weather_service.py # API Open-Meteo
│   │   ├── ml_predictor.py    # Chargement / prédiction du modèle ML
│   │   └── decision_engine.py # FAO + météo + ML (règles en secours)
│   └── management/commands/
│       ├── load_initial_data.py
│       ├── import_fao_data.py
│       ├── build_ml_dataset.py
│       └── train_ml_model.py
├── ml/
│   ├── datasets/raw/          # CSV/DTA téléchargés (non versionnés)
│   ├── datasets/processed/    # agridec_training.csv (généré)
│   ├── scripts/
│   │   ├── download_datasets.py      # téléchargement
│   │   ├── build_agridec_dataset.py  # adaptation
│   │   ├── train_agridec_model.py    # entraînement
│   │   └── run_ml_pipeline.py        # pipeline complet
│   └── artifacts/             # agridec_model.joblib (généré)
├── templates/                 # Pages HTML
└── static/                    # CSS et JavaScript
```

---

## APIs et données externes utilisées

| Service | URL | Usage |
|---------|-----|-------|
| FAO Crop Calendar | [api-cropcalendar.apps.fao.org](https://api-cropcalendar.apps.fao.org/) | Périodes de semis et récolte (RDC) |
| Open-Meteo | [open-meteo.com](https://open-meteo.com/) | Prévisions météo par coordonnées GPS |
| One Acre Fund | [Zenodo 11122388](https://zenodo.org/records/11122388) | Dataset terrain maïs Afrique (ML) |
| LSMS-ISA | [Zenodo 15773365](https://zenodo.org/records/15773365) | Enquêtes agricoles Afrique (ML) |

---

## Contexte académique

Ce projet a été réalisé dans un **cadre pédagogique et de formation**. Il vise à démontrer :

- la conception d'une application web full-stack avec Django ;
- l'intégration d'APIs externes (FAO, météo) ;
- la modélisation de données agricoles ;
- un moteur de décision combinant **règles métier**, **calendrier FAO** et **machine learning** entraîné sur des observations africaines (One Acre Fund + LSMS-ISA).

AgriDec **n'est pas un produit commercial** et ne remplace pas l'avis d'un agronome ou d'un service d'extension agricole sur le terrain. Les recommandations sont indicatives et reposent sur les données disponibles au moment de l'analyse.

---

## Auteur

**JoKonde** — [github.com/JoKonde](https://github.com/JoKonde)

---

## Licence

Projet éducatif — libre d'utilisation à des fins d'apprentissage et de recherche.
