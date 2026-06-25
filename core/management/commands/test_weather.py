"""Commande de test pour le service météo."""
from django.core.management.base import BaseCommand

from core.services.weather_service import fetch_weather, get_weather_service


class Command(BaseCommand):
    help = 'Teste le service météo avec des coordonnées GPS (défaut : Kinshasa).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--lat',
            type=float,
            default=-4.325,
            help='Latitude (défaut : Kinshasa -4.325).',
        )
        parser.add_argument(
            '--lon',
            type=float,
            default=15.322,
            help='Longitude (défaut : Kinshasa 15.322).',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Nombre de jours de prévision.',
        )

    def handle(self, *args, **options):
        lat = options['lat']
        lon = options['lon']
        days = options['days']

        self.stdout.write(f'Météo pour ({lat}, {lon}) — {days} jours…')

        service = get_weather_service()
        self.stdout.write(f'Service : {service.__class__.__name__}')

        data = fetch_weather(lat, lon, days=days)

        self.stdout.write(self.style.SUCCESS(f"Source : {data['source']}"))
        current = data['current']
        self.stdout.write(
            f"Actuel — Temp: {current['temperature']}°C | "
            f"Humidité: {current['humidite']}% | "
            f"Pluie: {current['probabilite_pluie']}% | "
            f"{current['pluie_mm']} mm | "
            f"Vent: {current['vent_kmh']} km/h"
        )

        self.stdout.write('\nPrévisions :')
        for day in data['forecast']:
            self.stdout.write(
                f"  {day['date']} — "
                f"{day['temperature_min']:.0f}-{day['temperature']:.0f}°C | "
                f"Hum: {day['humidite']}% | "
                f"Pluie: {day['probabilite_pluie']}% ({day['pluie_mm']} mm) | "
                f"Vent: {day['vent_kmh']} km/h"
            )
