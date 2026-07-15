"""Commande Django : python manage.py build_ml_dataset"""
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Construit ml/datasets/processed/agridec_training.csv '
        'à partir de One Acre Fund + LSMS-ISA (fichiers dans ml/datasets/raw/).'
    )

    def handle(self, *args, **options):
        # __file__ = core/management/commands/… → parents[3] = racine projet
        script = Path(__file__).resolve().parents[3] / 'ml' / 'scripts' / 'build_agridec_dataset.py'
        self.stdout.write(f'Exécution : {script}')
        import runpy
        runpy.run_path(str(script), run_name='__main__')
        self.stdout.write(self.style.SUCCESS('Dataset AgriDec prêt.'))
