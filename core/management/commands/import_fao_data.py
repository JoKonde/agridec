"""
Importe les cultures et calendriers FAO depuis l'API officielle.
RDC : https://api-cropcalendar.apps.fao.org/api/v1/countries/CD/cropCalendar
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Culture, FaoCalendrier
from core.services.fao_service import FaoApiError, FaoService, normalize_calendar_entries


class Command(BaseCommand):
    help = 'Importe les cultures et le calendrier FAO pour la RDC (code CD).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--country',
            default='CD',
            help='Code pays ISO FAO (défaut : CD = RDC).',
        )
        parser.add_argument(
            '--language',
            default='fr',
            help='Langue des libellés FAO (défaut : fr).',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprime les calendriers FAO existants pour ce pays avant import.',
        )

    def handle(self, *args, **options):
        country_code = options['country']
        language = options['language']
        service = FaoService(country_code=country_code, language=language)

        self.stdout.write(
            f'Récupération des données FAO pour {country_code} '
            f'({language})…'
        )

        try:
            raw_entries = service.get_crop_calendar()
        except FaoApiError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        entries = normalize_calendar_entries(raw_entries)
        if not entries:
            self.stderr.write(self.style.ERROR('Aucune entrée valide reçue de l\'API FAO.'))
            return

        entries = self._disambiguate_crop_names(entries)

        if options['clear']:
            FaoCalendrier.objects.all().delete()
            Culture.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cultures et calendriers FAO réinitialisés.'))

        cultures_created = 0
        cultures_updated = 0
        calendriers_saved = 0

        with transaction.atomic():
            for item in entries:
                defaults = {'nom': item['crop_name']}
                if item['growing_period_jours']:
                    defaults['duree_recolte_jours'] = item['growing_period_jours']

                culture, created = Culture.objects.update_or_create(
                    fao_crop_id=item['fao_crop_id'],
                    defaults=defaults,
                )
                if created:
                    cultures_created += 1
                else:
                    cultures_updated += 1
                    if item['growing_period_jours']:
                        culture.duree_recolte_jours = item['growing_period_jours']
                        culture.save(update_fields=['duree_recolte_jours', 'nom'])

                _, cal_created = FaoCalendrier.objects.update_or_create(
                    culture=culture,
                    pays_code=item['pays_code'] or country_code,
                    zone_aez=item['zone_aez'],
                    session_info=item['session_info'],
                    defaults={
                        'zone_id': item['zone_id'],
                        'mois_semis_debut': item['mois_semis_debut'],
                        'mois_semis_fin': item['mois_semis_fin'],
                        'mois_recolte_debut': item['mois_recolte_debut'],
                        'mois_recolte_fin': item['mois_recolte_fin'],
                        'growing_period_jours': item['growing_period_jours'],
                        'fao_last_updated': item['fao_last_updated'],
                    },
                )
                if cal_created:
                    calendriers_saved += 1
                else:
                    calendriers_saved += 1

        self.stdout.write(self.style.SUCCESS(
            f'Import FAO terminé : {cultures_created} cultures créées, '
            f'{cultures_updated} mises à jour, {calendriers_saved} calendriers enregistrés.'
        ))

    def _disambiguate_crop_names(self, entries):
        """
        Évite les conflits quand l'API FAO renvoie le même nom pour plusieurs crop_id.
        Ex. deux « Patate douce » avec des identifiants différents.
        """
        ids_by_name = {}
        for item in entries:
            key = item['crop_name'].lower()
            ids_by_name.setdefault(key, set()).add(item['fao_crop_id'])

        for item in entries:
            key = item['crop_name'].lower()
            if len(ids_by_name[key]) > 1:
                item['crop_name'] = f"{item['crop_name']} (FAO {item['fao_crop_id']})"

        return entries
