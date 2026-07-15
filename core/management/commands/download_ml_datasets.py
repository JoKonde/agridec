"""Commande Django : python manage.py download_ml_datasets"""
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Telecharge One Acre Fund + LSMS-ISA dans ml/datasets/raw/ '
        '(script ml/scripts/download_datasets.py).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-telecharge meme si les fichiers existent deja.',
        )

    def handle(self, *args, **options):
        script = Path(__file__).resolve().parents[3] / 'ml' / 'scripts' / 'download_datasets.py'
        self.stdout.write(f'Execution : {script}')
        import runpy

        argv = []
        if options.get('force'):
            argv.append('--force')
        # Injecte les arguments CLI pour le script
        import sys
        old_argv = sys.argv
        try:
            sys.argv = [str(script), *argv]
            runpy.run_path(str(script), run_name='__main__')
        finally:
            sys.argv = old_argv
        self.stdout.write(self.style.SUCCESS('Telechargement termine.'))
