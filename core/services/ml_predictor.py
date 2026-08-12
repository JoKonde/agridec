"""
Charge le modèle ML AgriDec (entraîné sur One Acre Fund + LSMS-ISA)
et produit des prédictions pour les 4 familles de décisions.

Si le fichier modèle est absent, predict() retourne None
→ le DecisionEngine garde alors les règles métier classiques.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from django.conf import settings

# Chemin par défaut vers l'artefact entraîné
DEFAULT_MODEL_PATH = Path(settings.BASE_DIR) / 'ml' / 'artifacts' / 'agridec_model.joblib'

_bundle = None
_load_attempted = False
_loaded_mtime = None


def model_available() -> bool:
    """True si le fichier modèle existe sur le disque."""
    return Path(getattr(settings, 'ML_MODEL_PATH', DEFAULT_MODEL_PATH)).exists()


def _load():
    """Charge le pipeline (recharge si le fichier .joblib a changé)."""
    global _bundle, _load_attempted, _loaded_mtime

    path = Path(getattr(settings, 'ML_MODEL_PATH', DEFAULT_MODEL_PATH))
    if not path.exists():
        _bundle = None
        _load_attempted = True
        _loaded_mtime = None
        return None

    mtime = path.stat().st_mtime
    if _load_attempted and _bundle is not None and _loaded_mtime == mtime:
        return _bundle

    try:
        import joblib
        _bundle = joblib.load(path)
        _loaded_mtime = mtime
        _load_attempted = True
    except Exception:
        _bundle = None
        _load_attempted = True
        _loaded_mtime = None
    return _bundle


def predict_decisions(
    *,
    culture: str,
    type_sol: str,
    mois: int,
    latitude: float,
    longitude: float,
    temperature: float,
    pluie_mm: float,
    humidite: float,
    vent_kmh: float,
    probabilite_pluie: float,
) -> dict | None:
    """
    Retourne un dict de prédictions 0/1, ou None si modèle indisponible.

    Exemple :
    {
      'peut_semer': 1,
      'doit_arroser': 0,
      'pret_a_recolter': 0,
      'risque_secheresse': 0,
      ...
    }
    """
    bundle = _load()
    if bundle is None:
        return None

    pipe = bundle['pipeline']
    features_num = bundle['features_num']
    features_cat = bundle['features_cat']
    targets = bundle['targets']

    # Normalise le nom de culture (le modèle a vu surtout « maïs », noms LSMS…)
    culture_norm = (culture or '').strip().lower()
    # Alias fréquents RDC / FAO → vocabulaire d'entraînement
    if 'mais' in culture_norm or 'maize' in culture_norm or 'corn' in culture_norm:
        culture_norm = 'maïs'
    type_sol_norm = (type_sol or 'Limoneux').strip()

    row = {
        'mois': int(mois),
        'latitude': float(latitude),
        'longitude': float(longitude),
        'temperature': float(temperature),
        'pluie_mm': float(pluie_mm),
        'humidite': float(humidite),
        'vent_kmh': float(vent_kmh),
        'probabilite_pluie': float(probabilite_pluie),
        'culture': culture_norm,
        'type_sol': type_sol_norm,
    }
    X = pd.DataFrame([row])[features_num + features_cat]
    pred = pipe.predict(X)[0]
    return {name: int(pred[i]) for i, name in enumerate(targets)}
