from datetime import date
from decimal import Decimal
from unittest import SkipTest

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from core.models import Culture, Exploitation, TypeSol
from core.services.decision_engine import DecisionEngine
from core.services.weather_service import (
    OpenMeteoWeatherService,
    fetch_weather,
)

KINSHASA_LAT = -4.325
KINSHASA_LON = 15.322


class WeatherServiceIntegrationTests(SimpleTestCase):
    """Tests d'intégration contre l'API Open-Meteo réelle."""

    def test_fetch_weather_from_real_api(self):
        data = fetch_weather(KINSHASA_LAT, KINSHASA_LON, days=3)
        self.assertEqual(data['source'], 'open-meteo')
        self.assertEqual(len(data['forecast']), 3)

    def test_open_meteo_service_direct_call(self):
        service = OpenMeteoWeatherService()
        data = service.get_forecast(KINSHASA_LAT, KINSHASA_LON, days=1)
        self.assertEqual(len(data['forecast']), 1)


class DecisionEngineIntegrationTests(TestCase):
    """Test du moteur de décision avec météo et FAO réelles en base."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not Culture.objects.filter(calendriers_fao__isnull=False).exists():
            call_command('import_fao_data', verbosity=0)
        cls.culture = Culture.objects.filter(
            calendriers_fao__isnull=False,
        ).distinct().first()
        if not cls.culture:
            raise SkipTest('Données FAO indisponibles — vérifiez l’API ou import_fao_data')

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testeur', password='test1234')
        cls.type_sol = TypeSol.objects.create(nom='Limoneux test')

    def test_decision_engine_produces_full_result(self):
        exploitation = Exploitation.objects.create(
            utilisateur=self.user,
            culture=self.culture,
            type_sol=self.type_sol,
            latitude=Decimal(str(KINSHASA_LAT)),
            longitude=Decimal(str(KINSHASA_LON)),
            statut=Exploitation.Statut.A_SEMER,
            date_prevue_semis=date.today(),
        )

        result = DecisionEngine().analyze(exploitation)

        self.assertIn('peut_semer', result)
        self.assertIn('reponse', result['peut_semer'])
        self.assertIn('explication', result['peut_semer'])
        self.assertIn('arroser', result)
        self.assertIn('recolte', result)
        self.assertIn('risques', result)
        self.assertIn('resume', result)
        self.assertEqual(result['meta']['source_meteo'], 'open-meteo')
