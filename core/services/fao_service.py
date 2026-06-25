"""
Service d'accès à l'API FAO Crop Calendar.
Documentation : https://api-cropcalendar.apps.fao.org/
"""
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from core.models import FaoCalendrier


class FaoApiError(Exception):
    """Erreur lors d'un appel à l'API FAO."""


class FaoService:
    """Client pour l'API FAO Crop Calendar (RDC = code CD)."""

    def __init__(
        self,
        country_code=None,
        language=None,
        base_url=None,
        timeout=None,
    ):
        self.country_code = country_code or settings.FAO_COUNTRY_CODE
        self.language = language or settings.FAO_LANGUAGE
        self.base_url = (base_url or settings.FAO_API_BASE_URL).rstrip('/')
        self.timeout = timeout or settings.FAO_API_TIMEOUT

    def _get(self, path, params=None):
        """Effectue une requête GET et retourne le JSON décodé."""
        params = dict(params or {})
        params.setdefault('language', self.language)
        query = urlencode(params)
        url = f'{self.base_url}{path}?{query}'
        request = Request(url, headers={'Accept': 'application/json'})

        try:
            with urlopen(request, timeout=self.timeout) as response:
                import json
                return json.loads(response.read().decode('utf-8'))
        except Exception as exc:
            raise FaoApiError(f'Appel FAO échoué ({url}) : {exc}') from exc

    def get_crops(self):
        """Liste des cultures disponibles pour le pays configuré."""
        return self._get(f'/countries/{self.country_code}/crops')

    def get_agro_ecological_zones(self):
        """Zones agro-écologiques du pays."""
        return self._get(f'/countries/{self.country_code}/aez')

    def get_crop_calendar(self, crop_id=None, aez_id=None):
        """
        Calendrier cultural complet pour le pays.
        Filtres optionnels : crop_id, aez_id.
        """
        params = {}
        if crop_id:
            params['crop'] = crop_id
        if aez_id:
            params['aez'] = aez_id
        return self._get(f'/countries/{self.country_code}/cropCalendar', params)


def parse_month(value):
    """Convertit un mois FAO (chaîne ou entier) en entier 1-12."""
    if value is None or value == '':
        return None
    try:
        month = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if 1 <= month <= 12:
        return month
    return None


def parse_growing_period_days(value):
    """
    Extrait la durée moyenne en jours depuis une valeur FAO.
    Ex. '110 - 130' → 120, '90' → 90.
    """
    if not value:
        return None
    numbers = [int(n) for n in re.findall(r'\d+', str(value))]
    if not numbers:
        return None
    return sum(numbers) // len(numbers)


def extract_month_range(early_date, late_date):
    """Retourne (mois_min, mois_max) à partir de deux dates FAO."""
    months = [
        m for m in (
            parse_month((early_date or {}).get('month')),
            parse_month((late_date or {}).get('month')),
        )
        if m is not None
    ]
    if not months:
        return None, None
    return min(months), max(months)


def normalize_calendar_entries(entries):
    """
    Transforme les entrées brutes de l'API en dictionnaires prêts pour l'import DB.
    """
    normalized = []

    for entry in entries:
        crop = entry.get('crop') or {}
        aez = entry.get('aez') or {}
        crop_id = crop.get('id')
        crop_name = crop.get('name')
        if not crop_id or not crop_name:
            continue

        for session in entry.get('sessions') or []:
            sow_start, sow_end = extract_month_range(
                session.get('early_sowing'),
                session.get('later_sowing'),
            )
            harvest_start, harvest_end = extract_month_range(
                session.get('early_harvest'),
                session.get('late_harvest'),
            )

            if None in (sow_start, sow_end, harvest_start, harvest_end):
                continue

            growing_period = (session.get('growing_period') or {}).get('value')
            normalized.append({
                'fao_crop_id': str(crop_id),
                'crop_name': crop_name.strip(),
                'pays_code': entry.get('id_country') or '',
                'zone_id': str(aez.get('id') or ''),
                'zone_aez': (aez.get('name') or 'Zone inconnue').strip(),
                'session_info': (session.get('additional_information') or '').strip(),
                'mois_semis_debut': sow_start,
                'mois_semis_fin': sow_end,
                'mois_recolte_debut': harvest_start,
                'mois_recolte_fin': harvest_end,
                'growing_period_jours': parse_growing_period_days(growing_period),
                'fao_last_updated': entry.get('lastUpdated') or '',
            })

    return normalized


# ---------------------------------------------------------------------------
# Consultation du calendrier FAO en base (importé depuis l'API réelle)
# ---------------------------------------------------------------------------

MOIS_FR = [
    '', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
]


def mois_dans_periode(mois, debut, fin):
    """Vérifie si un mois (1-12) est dans une période, y compris chevauchement d'année."""
    if debut <= fin:
        return debut <= mois <= fin
    return mois >= debut or mois <= fin


def get_calendriers_culture(culture, pays_code=None):
    """Retourne les calendriers FAO en base pour une culture donnée."""
    pays_code = pays_code or settings.FAO_COUNTRY_CODE
    return FaoCalendrier.objects.filter(culture=culture, pays_code=pays_code)


def est_dans_periode_semis(culture, mois, pays_code=None):
    """Indique si le mois donné est une période de semis FAO pour cette culture."""
    calendriers = get_calendriers_culture(culture, pays_code)
    for cal in calendriers:
        if mois_dans_periode(mois, cal.mois_semis_debut, cal.mois_semis_fin):
            return True, cal
    return False, None


def est_dans_periode_recolte(culture, mois, pays_code=None):
    """Indique si le mois donné est une période de récolte FAO pour cette culture."""
    calendriers = get_calendriers_culture(culture, pays_code)
    for cal in calendriers:
        if mois_dans_periode(mois, cal.mois_recolte_debut, cal.mois_recolte_fin):
            return True, cal
    return False, None


def get_periodes_semis_texte(culture, pays_code=None):
    """Résumé textuel des périodes de semis FAO pour une culture."""
    calendriers = get_calendriers_culture(culture, pays_code)
    if not calendriers.exists():
        return 'Aucune donnée FAO disponible pour cette culture.'

    periodes = []
    seen = set()
    for cal in calendriers:
        key = (cal.mois_semis_debut, cal.mois_semis_fin, cal.zone_aez)
        if key in seen:
            continue
        seen.add(key)
        debut = MOIS_FR[cal.mois_semis_debut]
        fin = MOIS_FR[cal.mois_semis_fin]
        label = f'{debut} – {fin}'
        if cal.zone_aez:
            label += f' ({cal.zone_aez})'
        if cal.session_info:
            label += f', {cal.session_info}'
        periodes.append(label)

    return ' ; '.join(periodes[:5])

