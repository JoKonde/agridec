"""
Construit le dataset d'entraînement AgriDec à partir de :
  - One Acre Fund (maïs Afrique, Zenodo 11122388)
  - LSMS-ISA Plotcrop + Plot (Banque mondiale, Zenodo 15773365)

Adaptation (idée clé) :
  Les sources donnent des DATES / MOIS observés de semis et de récolte,
  pas des colonnes « peut_semer aujourd'hui ».
  On transforme chaque observation en 12 lignes (mois 1..12) :
    - peut_semer = 1  si mois == mois_de_semis_observé
    - pret_a_recolter = 1 si mois == mois_de_recolte_observé
    - doit_arroser = 1 pendant la saison de culture si besoin d'eau
      (parcelle irriguée LSMS, ou saison peu pluvieuse OAF)
    - risques = chocs / adversités déclarés sur la parcelle

Prérequis :
  Avoir téléchargé les bruts avec :
    python ml/scripts/download_datasets.py

Usage :
  python ml/scripts/build_agridec_dataset.py

Pipeline complet (téléchargement + adaptation + entraînement) :
  python ml/scripts/run_ml_pipeline.py
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
from dateutil.relativedelta import relativedelta

# Chemins relatifs à la racine du projet AgriDec
ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'ml' / 'datasets' / 'raw'
OUT = ROOT / 'ml' / 'datasets' / 'processed' / 'agridec_training.csv'

# Mois Stata = nombre de mois depuis janvier 1960
STATA_MONTH_BASE = datetime(1960, 1, 1)

# Limite LSMS pour rester raisonnable en mémoire / temps CPU
LSMS_MAX_ROWS = 40_000


def stata_month_to_calendar_month(value) -> int | None:
    """Convertit un mois Stata (ex. 617) en mois calendaire 1..12."""
    if pd.isna(value):
        return None
    try:
        dt = STATA_MONTH_BASE + relativedelta(months=int(value))
        return int(dt.month)
    except (ValueError, TypeError, OverflowError):
        return None


def clay_to_type_sol(clay) -> str:
    """Approxime un type de sol AgriDec à partir du % d'argile."""
    if pd.isna(clay):
        return 'Limoneux'
    clay = float(clay)
    if clay < 20:
        return 'Sablonneux'
    if clay < 35:
        return 'Limoneux'
    if clay < 50:
        return 'Argileux'
    return 'Lateritique'


def expand_months(
    base: dict,
    plant_month: int | None,
    harvest_month: int | None,
    doit_arroser_saison: bool,
) -> list[dict]:
    """
    Une observation terrain → 12 lignes (une par mois).
    C'est ici qu'on crée les labels Oui/Non pour semer / récolter / arroser.
    """
    rows = []
    for mois in range(1, 13):
        # Mois de semis observé = bon mois pour semer
        peut_semer = int(plant_month is not None and mois == plant_month)
        # Mois de récolte observé = bon mois pour récolter
        pret_a_recolter = int(harvest_month is not None and mois == harvest_month)

        # Arrosage : pendant la fenêtre semis→récolte (ou 3 mois après semis)
        dans_saison = False
        if plant_month is not None:
            if harvest_month is not None:
                if plant_month <= harvest_month:
                    dans_saison = plant_month <= mois <= harvest_month
                else:
                    # Saison qui chevauche l'année (ex. semis nov → récolte mars)
                    dans_saison = mois >= plant_month or mois <= harvest_month
            else:
                fin = plant_month + 3
                if fin <= 12:
                    dans_saison = plant_month <= mois <= fin
                else:
                    dans_saison = mois >= plant_month or mois <= (fin - 12)

        doit_arroser = int(dans_saison and doit_arroser_saison and not peut_semer)

        row = {
            **base,
            'mois': mois,
            'peut_semer': peut_semer,
            'doit_arroser': doit_arroser,
            'pret_a_recolter': pret_a_recolter,
        }
        rows.append(row)
    return rows


def build_from_one_acre_fund() -> pd.DataFrame:
    """Adapte le CSV One Acre Fund (observations maïs Afrique)."""
    path = RAW / 'one_acre_fund_maize.csv'
    df = pd.read_csv(path)
    df['plant_dt'] = pd.to_datetime(df['plant_date'], errors='coerce')
    df['harvest_dt'] = pd.to_datetime(df['harvest_date'], errors='coerce')
    df = df.dropna(subset=['plant_dt'])

    # Seuil pluie basse = besoin d'eau plus probable (proxy arrosage)
    prec_median = df['season_prec'].median()

    records: list[dict] = []
    for _, r in df.iterrows():
        plant_m = int(r['plant_dt'].month)
        harvest_m = int(r['harvest_dt'].month) if pd.notna(r['harvest_dt']) else None
        # Peu de pluie saisonnière OU pas d'excès d'eau → tendance à devoir irriguer
        besoin_eau = bool(
            (pd.notna(r['season_prec']) and r['season_prec'] < prec_median)
            or (pd.isna(r.get('water_excess')) is False and r.get('water_excess') is False
                and pd.notna(r['season_prec']) and r['season_prec'] < prec_median * 0.8)
        )

        base = {
            'source': 'one_acre_fund',
            'country': str(r.get('country', '')).lower(),
            'culture': 'maïs',
            'type_sol': clay_to_type_sol(r.get('soil_clay')),
            'latitude': float(r['lat']) if pd.notna(r.get('lat')) else np.nan,
            'longitude': float(r['lon']) if pd.notna(r.get('lon')) else np.nan,
            'temperature': float(r['avg_season_tavg']) if pd.notna(r.get('avg_season_tavg')) else np.nan,
            'pluie_mm': float(r['season_prec']) / 90.0 if pd.notna(r.get('season_prec')) else np.nan,
            # Humidité proxy : saison sèche → humidité plus basse
            'humidite': float(
                min(90.0, max(25.0, 40.0 + (float(r['season_prec']) / 20.0)))
            ) if pd.notna(r.get('season_prec')) else 55.0,
            'vent_kmh': 10.0,
            'probabilite_pluie': float(
                min(95.0, max(5.0, float(r['season_prec']) / 10.0))
            ) if pd.notna(r.get('season_prec')) else 40.0,
            'risque_secheresse': int(
                pd.notna(r.get('season_prec')) and r['season_prec'] < prec_median * 0.6
            ),
            'risque_pluie_forte': int(bool(r.get('water_excess'))),
            'risque_ravageurs': int(bool(r.get('pest')) or bool(r.get('striga'))),
            'risque_maladie': int(bool(r.get('disease'))),
        }
        records.extend(expand_months(base, plant_m, harvest_m, besoin_eau))

    return pd.DataFrame(records)


def build_from_lsms() -> pd.DataFrame:
    """Adapte LSMS-ISA Plotcrop (+ irrigation du Plot)."""
    crop_path = RAW / 'lsms_plotcrop.dta'
    plot_path = RAW / 'lsms_plot.dta'

    crop, _ = pyreadstat.read_dta(str(crop_path), encoding='latin1')
    plot, _ = pyreadstat.read_dta(
        str(plot_path),
        encoding='latin1',
        usecols=['country', 'wave', 'season', 'plot_id_merge', 'irrigated', 'soil_fertility_index'],
    )

    crop = crop.dropna(subset=['planting_month'])
    # Échantillon stratifié simple pour limiter la taille
    if len(crop) > LSMS_MAX_ROWS:
        crop = crop.sample(n=LSMS_MAX_ROWS, random_state=42)

    merged = crop.merge(
        plot,
        on=['country', 'wave', 'season', 'plot_id_merge'],
        how='left',
        suffixes=('', '_plot'),
    )

    records: list[dict] = []
    for _, r in merged.iterrows():
        plant_m = stata_month_to_calendar_month(r['planting_month'])
        harvest_m = stata_month_to_calendar_month(r.get('harvest_end_month'))
        if plant_m is None:
            continue

        culture = str(r.get('crop_name', 'inconnu')).strip().lower()
        if not culture or culture == 'nan':
            culture = 'inconnu'

        irrigated = r.get('irrigated')
        # Parcelle irriguée = besoin d'arrosage / pratique d'irrigation observée
        besoin_eau = bool(pd.notna(irrigated) and float(irrigated) == 1.0)
        # Si non irrigué mais choc sécheresse → aussi besoin d'eau
        if not besoin_eau and pd.notna(r.get('drought_shock')) and float(r['drought_shock']) == 1.0:
            besoin_eau = True

        fertility = r.get('soil_fertility_index')
        if pd.isna(fertility):
            type_sol = 'Limoneux'
        elif float(fertility) < 0:
            type_sol = 'Sablonneux'
        elif float(fertility) < 1:
            type_sol = 'Limoneux'
        else:
            type_sol = 'Argileux'

        base = {
            'source': 'lsms_isa',
            'country': str(r.get('country', '')).lower(),
            'culture': culture,
            'type_sol': type_sol,
            'latitude': float(r['lat_modified']) if pd.notna(r.get('lat_modified')) else np.nan,
            'longitude': float(r['lon_modified']) if pd.notna(r.get('lon_modified')) else np.nan,
            # Pas de météo journalière dans LSMS → valeurs neutres (le modèle s'appuie surtout sur mois/culture/lieu)
            'temperature': 26.0,
            'pluie_mm': 5.0,
            'humidite': 60.0,
            'vent_kmh': 10.0,
            'probabilite_pluie': 40.0,
            'risque_secheresse': int(pd.notna(r.get('drought_shock')) and float(r['drought_shock']) == 1.0),
            'risque_pluie_forte': int(
                (pd.notna(r.get('rain_shock')) and float(r['rain_shock']) == 1.0)
                or (pd.notna(r.get('flood_shock')) and float(r['flood_shock']) == 1.0)
            ),
            'risque_ravageurs': int(pd.notna(r.get('pests_shock')) and float(r['pests_shock']) == 1.0),
            'risque_maladie': int(pd.notna(r.get('crop_shock')) and float(r['crop_shock']) == 1.0),
        }
        records.extend(expand_months(base, plant_m, harvest_m, besoin_eau))

    return pd.DataFrame(records)


def main():
    print('=== Construction dataset AgriDec ===')
    print('1) One Acre Fund…')
    oaf = build_from_one_acre_fund()
    print(f'   -> {len(oaf)} lignes')

    print('2) LSMS-ISA...')
    lsms = build_from_lsms()
    print(f'   -> {len(lsms)} lignes')

    full = pd.concat([oaf, lsms], ignore_index=True)
    full = full.dropna(subset=['latitude', 'longitude', 'mois'])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(OUT, index=False)
    print(f'3) Dataset final : {len(full)} lignes -> {OUT}')
    print('Répartition sources :')
    print(full['source'].value_counts().to_string())
    print('Labels positifs :')
    for col in ['peut_semer', 'doit_arroser', 'pret_a_recolter',
                'risque_secheresse', 'risque_pluie_forte', 'risque_ravageurs', 'risque_maladie']:
        print(f'  {col}: {int(full[col].sum())} / {len(full)}')


if __name__ == '__main__':
    main()
