"""
Construit le dataset d'entraînement AgriDec à partir de :
  - One Acre Fund (maïs Afrique, Zenodo 11122388)
  - LSMS-ISA Plotcrop + Plot (Banque mondiale, Zenodo 15773365)

Sources / URLs des datasets :
  One Acre Fund — page Zenodo :
    https://zenodo.org/records/11122388
  One Acre Fund — fichier CSV :
    https://zenodo.org/records/11122388/files/One_Acre_Fund_MEL_maize_survey_data_2016-2022.csv?download=1

  LSMS-ISA (panel harmonisé) — page Zenodo :
    https://zenodo.org/records/15773365
  LSMS-ISA — Plotcrop (semis, récolte, chocs) :
    https://zenodo.org/records/15773365/files/Plotcrop_dataset.dta?download=1
  LSMS-ISA — Plot (irrigation, sol) :
    https://zenodo.org/records/15773365/files/Plot_dataset.dta?download=1
  Projet LSMS-ISA (Banque mondiale) :
    https://www.worldbank.org/en/programs/lsms/initiatives/lsms-isa

Adaptation (idée clé) :
  Les sources donnent des DATES / MOIS observés de semis et de récolte.
  On transforme chaque observation en 12 lignes (mois 1..12) avec une
  MÉTÉO / CLIMAT cohérent par mois (saison sèche ↔ pluies), pour que le
  modèle apprenne aussi humidité / pluie / température — pas seulement le mois.

  Labels :
    - peut_semer = 1  si mois == mois_de_semis_observé
    - pret_a_recolter = 1 si mois == mois_de_recolte_observé
    - doit_arroser = 1 si en saison de culture ET climat sec (ou parcelle irriguée / sécheresse)
    - risques liés aux chocs terrain ET au climat du mois

Prérequis :
  python ml/scripts/download_datasets.py

Usage :
  python ml/scripts/build_agridec_dataset.py
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
from dateutil.relativedelta import relativedelta

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'ml' / 'datasets' / 'raw'
OUT = ROOT / 'ml' / 'datasets' / 'processed' / 'agridec_training.csv'

STATA_MONTH_BASE = datetime(1960, 1, 1)
LSMS_MAX_ROWS = 40_000

# Profils alignés avec le curseur UI (ml-test-climate.js)
CLIMAT_PLUIES = {
    'temperature': 26.0,
    'humidite': 85.0,
    'pluie_mm': 18.0,
    'probabilite_pluie': 80.0,
    'vent_kmh': 12.0,
}
CLIMAT_SECHE = {
    'temperature': 30.0,
    'humidite': 42.0,
    'pluie_mm': 0.0,
    'probabilite_pluie': 5.0,
    'vent_kmh': 15.0,
}

# Indice de sécheresse par mois (0 = pluies, 1 = sèche) — zone tropicale type Afrique centrale
# Juin–septembre : saison sèche dominante ; octobre–mai : plus humide
DRYNESS_BY_MONTH = {
    1: 0.25, 2: 0.30, 3: 0.35, 4: 0.40,
    5: 0.55, 6: 0.85, 7: 0.95, 8: 1.00,
    9: 0.80, 10: 0.35, 11: 0.15, 12: 0.20,
}


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


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def climate_for_month(mois: int, dryness_bias: float = 0.0, rng: np.random.Generator | None = None) -> dict:
    """
    Météo synthétique cohérente pour un mois donné.
    dryness_bias (-0.3 .. +0.3) décale vers plus sec (+) ou plus humide (-).
    Petit bruit aléatoire pour éviter que toutes les lignes soient identiques.
    """
    t = float(np.clip(DRYNESS_BY_MONTH.get(mois, 0.5) + dryness_bias, 0.0, 1.0))
    meteo = {
        key: _lerp(CLIMAT_PLUIES[key], CLIMAT_SECHE[key], t)
        for key in CLIMAT_PLUIES
    }
    if rng is not None:
        meteo['temperature'] += float(rng.normal(0, 0.8))
        meteo['humidite'] = float(np.clip(meteo['humidite'] + rng.normal(0, 3), 20, 95))
        meteo['pluie_mm'] = float(max(0.0, meteo['pluie_mm'] + rng.normal(0, 1.5)))
        meteo['probabilite_pluie'] = float(
            np.clip(meteo['probabilite_pluie'] + rng.normal(0, 5), 0, 100)
        )
        meteo['vent_kmh'] = float(max(2.0, meteo['vent_kmh'] + rng.normal(0, 1.5)))
    return meteo


def est_climat_sec(meteo: dict) -> bool:
    """Critères proches des règles AgriDec / curseur saison sèche."""
    return (
        meteo['humidite'] < 55
        and meteo['pluie_mm'] < 3.0
        and meteo['probabilite_pluie'] < 35
    )


def est_climat_humide(meteo: dict) -> bool:
    return meteo['pluie_mm'] >= 10.0 or meteo['probabilite_pluie'] >= 65


def dans_fenetre_culture(mois: int, plant_month: int | None, harvest_month: int | None) -> bool:
    if plant_month is None:
        return False
    if harvest_month is not None:
        if plant_month <= harvest_month:
            return plant_month <= mois <= harvest_month
        return mois >= plant_month or mois <= harvest_month
    fin = plant_month + 3
    if fin <= 12:
        return plant_month <= mois <= fin
    return mois >= plant_month or mois <= (fin - 12)


def expand_months(
    base: dict,
    plant_month: int | None,
    harvest_month: int | None,
    *,
    dryness_bias: float,
    irrigated: bool,
    drought_shock: bool,
    rain_shock: bool,
    pest_shock: bool,
    disease_shock: bool,
    rng: np.random.Generator,
) -> list[dict]:
    """
    Une observation terrain → 12 lignes avec météo variable par mois.
    Les labels arrosage / risques dépendent aussi du climat du mois.
    """
    rows = []
    for mois in range(1, 13):
        meteo = climate_for_month(mois, dryness_bias=dryness_bias, rng=rng)

        # Chocs terrain → on force un climat cohérent (sécheresse = plus sec, etc.)
        if drought_shock and DRYNESS_BY_MONTH.get(mois, 0.5) >= 0.5:
            meteo = climate_for_month(mois, dryness_bias=max(dryness_bias, 0.25), rng=rng)
        if rain_shock and DRYNESS_BY_MONTH.get(mois, 0.5) <= 0.45:
            meteo = climate_for_month(mois, dryness_bias=min(dryness_bias, -0.25), rng=rng)

        peut_semer = int(plant_month is not None and mois == plant_month)
        pret_a_recolter = int(harvest_month is not None and mois == harvest_month)
        en_culture = dans_fenetre_culture(mois, plant_month, harvest_month)
        sec = est_climat_sec(meteo)
        humide = est_climat_humide(meteo)

        # Arrosage : lié au CLIMAT du mois (+ irrigation / sécheresse observée)
        doit_arroser = int(
            en_culture
            and not peut_semer
            and (sec or irrigated or (drought_shock and sec))
        )

        # Risques : chocs + climat du mois (pour que météo compte à l'entraînement)
        risque_secheresse = int(drought_shock or (sec and en_culture))
        risque_pluie_forte = int(rain_shock or (humide and meteo['pluie_mm'] >= 12))
        risque_ravageurs = int(pest_shock)
        risque_maladie = int(disease_shock)

        row = {
            **base,
            'mois': mois,
            'temperature': round(meteo['temperature'], 2),
            'humidite': int(round(meteo['humidite'])),
            'pluie_mm': round(meteo['pluie_mm'], 2),
            'probabilite_pluie': int(round(meteo['probabilite_pluie'])),
            'vent_kmh': round(meteo['vent_kmh'], 2),
            'peut_semer': peut_semer,
            'doit_arroser': doit_arroser,
            'pret_a_recolter': pret_a_recolter,
            'risque_secheresse': risque_secheresse,
            'risque_pluie_forte': risque_pluie_forte,
            'risque_ravageurs': risque_ravageurs,
            'risque_maladie': risque_maladie,
        }
        rows.append(row)
    return rows


def build_from_one_acre_fund() -> pd.DataFrame:
    """Adapte One Acre Fund avec climat mensuel dérivé de la pluie saisonnière."""
    path = RAW / 'one_acre_fund_maize.csv'
    df = pd.read_csv(path)
    df['plant_dt'] = pd.to_datetime(df['plant_date'], errors='coerce')
    df['harvest_dt'] = pd.to_datetime(df['harvest_date'], errors='coerce')
    df = df.dropna(subset=['plant_dt'])

    prec_median = df['season_prec'].median()
    rng = np.random.default_rng(42)
    records: list[dict] = []

    for _, r in df.iterrows():
        plant_m = int(r['plant_dt'].month)
        harvest_m = int(r['harvest_dt'].month) if pd.notna(r['harvest_dt']) else None

        # Bias sécheresse selon pluie saisonnière observée
        if pd.notna(r.get('season_prec')):
            # < médiane → plus sec ; > médiane → plus humide
            dryness_bias = float(np.clip(
                (prec_median - float(r['season_prec'])) / max(prec_median, 1.0) * 0.35,
                -0.35,
                0.35,
            ))
        else:
            dryness_bias = 0.0

        drought = bool(
            pd.notna(r.get('season_prec')) and r['season_prec'] < prec_median * 0.6
        )
        rain_ex = bool(r.get('water_excess'))

        base = {
            'source': 'one_acre_fund',
            'country': str(r.get('country', '')).lower(),
            'culture': 'maïs',
            'type_sol': clay_to_type_sol(r.get('soil_clay')),
            'latitude': float(r['lat']) if pd.notna(r.get('lat')) else np.nan,
            'longitude': float(r['lon']) if pd.notna(r.get('lon')) else np.nan,
        }
        records.extend(
            expand_months(
                base,
                plant_m,
                harvest_m,
                dryness_bias=dryness_bias,
                irrigated=False,
                drought_shock=drought,
                rain_shock=rain_ex,
                pest_shock=bool(r.get('pest')) or bool(r.get('striga')),
                disease_shock=bool(r.get('disease')),
                rng=rng,
            )
        )

    return pd.DataFrame(records)


def build_from_lsms() -> pd.DataFrame:
    """Adapte LSMS avec climat mensuel (plus de météo neutre fixe)."""
    crop, _ = pyreadstat.read_dta(str(RAW / 'lsms_plotcrop.dta'), encoding='latin1')
    plot, _ = pyreadstat.read_dta(
        str(RAW / 'lsms_plot.dta'),
        encoding='latin1',
        usecols=['country', 'wave', 'season', 'plot_id_merge', 'irrigated', 'soil_fertility_index'],
    )

    crop = crop.dropna(subset=['planting_month'])
    if len(crop) > LSMS_MAX_ROWS:
        crop = crop.sample(n=LSMS_MAX_ROWS, random_state=42)

    merged = crop.merge(
        plot,
        on=['country', 'wave', 'season', 'plot_id_merge'],
        how='left',
        suffixes=('', '_plot'),
    )

    rng = np.random.default_rng(7)
    records: list[dict] = []

    for _, r in merged.iterrows():
        plant_m = stata_month_to_calendar_month(r['planting_month'])
        harvest_m = stata_month_to_calendar_month(r.get('harvest_end_month'))
        if plant_m is None:
            continue

        culture = str(r.get('crop_name', 'inconnu')).strip().lower()
        if not culture or culture == 'nan':
            culture = 'inconnu'

        irrigated = bool(pd.notna(r.get('irrigated')) and float(r['irrigated']) == 1.0)
        drought = bool(pd.notna(r.get('drought_shock')) and float(r['drought_shock']) == 1.0)
        rain = bool(
            (pd.notna(r.get('rain_shock')) and float(r['rain_shock']) == 1.0)
            or (pd.notna(r.get('flood_shock')) and float(r['flood_shock']) == 1.0)
        )

        fertility = r.get('soil_fertility_index')
        if pd.isna(fertility):
            type_sol = 'Limoneux'
        elif float(fertility) < 0:
            type_sol = 'Sablonneux'
        elif float(fertility) < 1:
            type_sol = 'Limoneux'
        else:
            type_sol = 'Argileux'

        # Bias : parcelles irriguées / sécheresse → climat un peu plus sec en moyenne
        dryness_bias = 0.0
        if drought:
            dryness_bias += 0.2
        if irrigated:
            dryness_bias += 0.1
        if rain:
            dryness_bias -= 0.2

        base = {
            'source': 'lsms_isa',
            'country': str(r.get('country', '')).lower(),
            'culture': culture,
            'type_sol': type_sol,
            'latitude': float(r['lat_modified']) if pd.notna(r.get('lat_modified')) else np.nan,
            'longitude': float(r['lon_modified']) if pd.notna(r.get('lon_modified')) else np.nan,
        }
        records.extend(
            expand_months(
                base,
                plant_m,
                harvest_m,
                dryness_bias=float(np.clip(dryness_bias, -0.35, 0.35)),
                irrigated=irrigated,
                drought_shock=drought,
                rain_shock=rain,
                pest_shock=bool(pd.notna(r.get('pests_shock')) and float(r['pests_shock']) == 1.0),
                disease_shock=bool(pd.notna(r.get('crop_shock')) and float(r['crop_shock']) == 1.0),
                rng=rng,
            )
        )

    return pd.DataFrame(records)


def main():
    print('=== Construction dataset AgriDec (meteo/climat par mois) ===')
    print('1) One Acre Fund...')
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
    print(full['source'].value_counts().to_string())
    print('Labels positifs :')
    for col in [
        'peut_semer', 'doit_arroser', 'pret_a_recolter',
        'risque_secheresse', 'risque_pluie_forte', 'risque_ravageurs', 'risque_maladie',
    ]:
        print(f'  {col}: {int(full[col].sum())} / {len(full)}')

    # Contrôle rapide : corrélation climat ↔ arrosage
    sec = (
        (full['humidite'] < 55)
        & (full['pluie_mm'] < 3)
        & (full['probabilite_pluie'] < 35)
    )
    print('Taux doit_arroser si climat sec :', round(full.loc[sec, 'doit_arroser'].mean(), 3))
    print('Taux doit_arroser si climat non sec :', round(full.loc[~sec, 'doit_arroser'].mean(), 3))


if __name__ == '__main__':
    main()
