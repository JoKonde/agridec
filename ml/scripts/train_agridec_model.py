"""
Entraîne le modèle AgriDec (Random Forest multi-sorties) sur agridec_training.csv.

Sorties prédites :
  - peut_semer
  - doit_arroser
  - pret_a_recolter
  - risque_secheresse, risque_pluie_forte, risque_ravageurs, risque_maladie

Artefacts sauvegardés dans ml/artifacts/ :
  - agridec_model.joblib
  - agridec_encoders.joblib
  - metrics.json

Usage :
  python ml/scripts/train_agridec_model.py
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'ml' / 'datasets' / 'processed' / 'agridec_training.csv'
ARTIFACTS = ROOT / 'ml' / 'artifacts'

FEATURE_NUM = [
    'mois', 'latitude', 'longitude',
    'temperature', 'pluie_mm', 'humidite', 'vent_kmh', 'probabilite_pluie',
]
FEATURE_CAT = ['culture', 'type_sol']
TARGETS = [
    'peut_semer',
    'doit_arroser',
    'pret_a_recolter',
    'risque_secheresse',
    'risque_pluie_forte',
    'risque_ravageurs',
    'risque_maladie',
]


def main():
    if not DATA.exists():
        raise SystemExit(
            f'Dataset introuvable : {DATA}\n'
            'Exécutez d\'abord : python ml/scripts/build_agridec_dataset.py'
        )

    print('Chargement…', DATA)
    df = pd.read_csv(DATA)
    df = df.dropna(subset=FEATURE_NUM + FEATURE_CAT + TARGETS)

    X = df[FEATURE_NUM + FEATURE_CAT]
    y = df[TARGETS].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Encodage des catégories (culture, sol) + passage des numériques
    preprocess = ColumnTransformer(
        transformers=[
            ('num', 'passthrough', FEATURE_NUM),
            ('cat', OneHotEncoder(handle_unknown='ignore'), FEATURE_CAT),
        ]
    )

    # Random Forest : robuste, interprétable pour une soutenance
    clf = MultiOutputClassifier(
        RandomForestClassifier(
            n_estimators=120,
            max_depth=16,
            min_samples_leaf=5,
            n_jobs=-1,
            random_state=42,
            class_weight='balanced_subsample',
        )
    )

    pipe = Pipeline([
        ('prep', preprocess),
        ('model', clf),
    ])

    print('Entraînement…')
    pipe.fit(X_train, y_train)

    print('Évaluation…')
    y_pred = pipe.predict(X_test)
    metrics = {}
    for i, name in enumerate(TARGETS):
        metrics[name] = {
            'f1': round(float(f1_score(y_test.iloc[:, i], y_pred[:, i], zero_division=0)), 4),
            'positifs_test': int(y_test.iloc[:, i].sum()),
        }
        print(f'  {name}: F1={metrics[name]["f1"]}')

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS / 'agridec_model.joblib'
    meta_path = ARTIFACTS / 'model_meta.json'

    joblib.dump(
        {
            'pipeline': pipe,
            'features_num': FEATURE_NUM,
            'features_cat': FEATURE_CAT,
            'targets': TARGETS,
        },
        model_path,
    )
    meta_path.write_text(
        json.dumps({'metrics': metrics, 'n_train': len(X_train), 'n_test': len(X_test)}, indent=2),
        encoding='utf-8',
    )
    print(f'Modèle sauvegardé : {model_path}')
    print(f'Métriques : {meta_path}')


if __name__ == '__main__':
    main()
