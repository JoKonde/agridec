"""
Service météo interchangeable pour AgriDec.
Implémentation par défaut : Open-Meteo (gratuit, sans clé API).
Documentation : https://open-meteo.com/en/docs

Toutes les données proviennent de l'API réelle — aucune donnée simulée.
"""
from abc import ABC, abstractmethod
from importlib import import_module
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class WeatherApiError(Exception):
    """Erreur lors d'un appel à l'API météo."""


class BaseWeatherService(ABC):
    """
    Interface commune pour tous les fournisseurs météo.
    Permet de remplacer facilement l'API sans modifier le moteur de décision.
    """

    @abstractmethod
    def get_forecast(self, latitude, longitude, days=None):
        """
        Retourne les prévisions météo structurées depuis l'API configurée.

        Format de sortie :
        {
            'latitude': float,
            'longitude': float,
            'source': str,
            'current': {
                'temperature': float,
                'humidite': int,
                'probabilite_pluie': int,
                'pluie_mm': float,
                'vent_kmh': float,
            },
            'forecast': [
                {
                    'date': 'YYYY-MM-DD',
                    'temperature': float,
                    'temperature_min': float,
                    'humidite': int,
                    'probabilite_pluie': int,
                    'pluie_mm': float,
                    'vent_kmh': float,
                },
                ...
            ],
        }
        """


class OpenMeteoWeatherService(BaseWeatherService):
    """Client Open-Meteo — appelle l'API réelle à chaque requête."""

    def __init__(self, base_url=None, timeout=None, forecast_days=None):
        self.base_url = (base_url or settings.WEATHER_API_BASE_URL).rstrip('/')
        self.timeout = timeout or settings.WEATHER_API_TIMEOUT
        self.forecast_days = forecast_days or settings.WEATHER_FORECAST_DAYS
        self.timezone = settings.TIME_ZONE

    def _fetch(self, latitude, longitude):
        """Appelle l'API Open-Meteo et retourne le JSON brut."""
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'daily': ','.join([
                'temperature_2m_max',
                'temperature_2m_min',
                'precipitation_probability_max',
                'precipitation_sum',
                'wind_speed_10m_max',
            ]),
            'hourly': 'relative_humidity_2m',
            'forecast_days': self.forecast_days,
            'timezone': self.timezone,
        }
        url = f'{self.base_url}/forecast?{urlencode(params)}'
        request = Request(url, headers={'Accept': 'application/json'})

        try:
            with urlopen(request, timeout=self.timeout) as response:
                import json
                return json.loads(response.read().decode('utf-8'))
        except Exception as exc:
            raise WeatherApiError(f'Appel météo échoué ({url}) : {exc}') from exc

    def get_forecast(self, latitude, longitude, days=None):
        raw = self._fetch(latitude, longitude)
        return parse_open_meteo_response(raw, days=days or self.forecast_days)


def parse_open_meteo_response(raw_data, days=None):
    """Transforme la réponse réelle Open-Meteo en structure AgriDec."""
    daily = raw_data.get('daily', {})
    hourly = raw_data.get('hourly', {})

    dates = daily.get('time', [])
    if days:
        dates = dates[:days]

    if not dates:
        raise WeatherApiError('Réponse API météo invalide : aucune date de prévision.')

    humidity_by_date = _average_humidity_by_date(
        hourly.get('time', []),
        hourly.get('relative_humidity_2m', []),
    )

    forecast = []
    for i, date_str in enumerate(dates):
        forecast.append({
            'date': date_str,
            'temperature': _safe_float(daily.get('temperature_2m_max', []), i),
            'temperature_min': _safe_float(daily.get('temperature_2m_min', []), i),
            'humidite': int(humidity_by_date.get(date_str, 0)),
            'probabilite_pluie': int(_safe_float(
                daily.get('precipitation_probability_max', []), i, 0
            )),
            'pluie_mm': round(_safe_float(daily.get('precipitation_sum', []), i, 0.0), 1),
            'vent_kmh': round(_safe_float(daily.get('wind_speed_10m_max', []), i, 0.0), 1),
        })

    current = forecast[0]

    return {
        'latitude': float(raw_data.get('latitude', 0)),
        'longitude': float(raw_data.get('longitude', 0)),
        'source': 'open-meteo',
        'current': {
            'temperature': current['temperature'],
            'humidite': current['humidite'],
            'probabilite_pluie': current['probabilite_pluie'],
            'pluie_mm': current['pluie_mm'],
            'vent_kmh': current['vent_kmh'],
        },
        'forecast': forecast,
    }


def _safe_float(values, index, default=0.0):
    """Extrait une valeur numérique depuis un champ de la réponse API."""
    try:
        value = values[index]
        if value is None:
            return default
        return float(value)
    except (IndexError, TypeError, ValueError):
        return default


def _average_humidity_by_date(hourly_times, humidities):
    """Calcule l'humidité moyenne par jour à partir des données horaires API."""
    buckets = {}

    for time_str, humidity in zip(hourly_times, humidities):
        if humidity is None:
            continue
        date_str = time_str[:10]
        buckets.setdefault(date_str, []).append(float(humidity))

    return {
        date: round(sum(values) / len(values))
        for date, values in buckets.items()
        if values
    }


def get_weather_service():
    """Instancie le service météo configuré dans settings.WEATHER_SERVICE_CLASS."""
    class_path = settings.WEATHER_SERVICE_CLASS
    module_path, class_name = class_path.rsplit('.', 1)
    module = import_module(module_path)
    service_class = getattr(module, class_name)
    return service_class()


def fetch_weather(latitude, longitude, days=None):
    """
    Récupère la météo depuis l'API configurée.
    Lève WeatherApiError si l'API est indisponible — pas de repli simulé.
    """
    service = get_weather_service()
    return service.get_forecast(latitude, longitude, days=days)
