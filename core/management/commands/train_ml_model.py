"""Commande Django : python manage.py train_ml_model"""
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Entraîne le modèle ML AgriDec et sauvegarde '
        'ml/artifacts/agridec_model.joblib'
    )

    def handle(self, *args, **options):
        script = Path(__file__).resolve().parents[3] / 'ml' / 'scripts' / 'train_agridec_model.py'
        self.stdout.write(f'Exécution : {script}')
        import runpy
        runpy.run_path(str(script), run_name='__main__')
        self.stdout.write(self.style.SUCCESS('Modèle entraîné et sauvegardé.'))
