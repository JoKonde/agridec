"""
Commande pour peupler les données de référence locales (types de sol).
Les cultures et calendriers FAO sont importés via : python manage.py import_fao_data
"""
from django.core.management.base import BaseCommand

from core.models import TypeSol


TYPES_SOL = [
    'Sablonneux',
    'Argileux',
    'Limoneux',
    'Humifère',
    'Lateritique',
]


class Command(BaseCommand):
    help = 'Charge les types de sol de référence (cultures FAO : import_fao_data).'

    def handle(self, *args, **options):
        for nom in TYPES_SOL:
            TypeSol.objects.update_or_create(nom=nom)

        self.stdout.write(self.style.SUCCESS(f'{len(TYPES_SOL)} types de sol chargés.'))
        self.stdout.write(
            'Pour les cultures FAO (RDC), exécutez : python manage.py import_fao_data'
        )
