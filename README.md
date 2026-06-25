# AgriDec — Agriculture Decision System

> **Projet académique** — Application web d'aide à la décision agricole pour la République Démocratique du Congo (RDC).

AgriDec aide les agriculteurs à décider **quand semer**, **s'il faut arroser** et **quand récolter**, en croisant le **calendrier cultural FAO** (données officielles) et les **prévisions météo Open-Meteo** (temps réel).  
Aucune intelligence artificielle, aucune donnée fictive : uniquement des APIs réelles et un moteur de règles métier transparent.

**Dépôt GitHub :** [github.com/JoKonde/agirdec](https://github.com/JoKonde/agirdec)

---

## Fonctionnalités

- Inscription et connexion des agriculteurs
- Création d'une exploitation (culture, type de sol, géolocalisation GPS)
- Analyse automatique : semis, irrigation, récolte, risques
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
│   │   └── decision_engine.py # Moteur de règles métier
│   └── management/commands/
│       ├── load_initial_data.py
│       └── import_fao_data.py
├── templates/                 # Pages HTML
└── static/                    # CSS et JavaScript
```

---

## APIs externes utilisées

| Service | URL | Usage |
|---------|-----|-------|
| FAO Crop Calendar | [api-cropcalendar.apps.fao.org](https://api-cropcalendar.apps.fao.org/) | Périodes de semis et récolte (RDC) |
| Open-Meteo | [open-meteo.com](https://open-meteo.com/) | Prévisions météo par coordonnées GPS |

---

## Contexte académique

Ce projet a été réalisé dans un **cadre pédagogique et de formation**. Il vise à démontrer :

- la conception d'une application web full-stack avec Django ;
- l'intégration d'APIs externes (FAO, météo) ;
- la modélisation de données agricoles ;
- un moteur de décision basé sur des règles métier explicites.

AgriDec **n'est pas un produit commercial** et ne remplace pas l'avis d'un agronome ou d'un service d'extension agricole sur le terrain. Les recommandations sont indicatives et reposent sur les données disponibles au moment de l'analyse.

---

## Auteur

**JoKonde** — [github.com/JoKonde](https://github.com/JoKonde)

---

## Licence

Projet éducatif — libre d'utilisation à des fins d'apprentissage et de recherche.
