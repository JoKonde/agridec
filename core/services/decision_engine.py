"""
Moteur de décision agricole AgriDec.
Combine calendrier FAO (base), météo (API), règles métier,
et un modèle ML entraîné sur One Acre Fund + LSMS-ISA (si disponible).
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.models import Exploitation
from core.services.fao_service import (
    MOIS_FR,
    est_dans_periode_semis,
    get_calendriers_culture,
    get_periodes_semis_texte,
)
from core.services.ml_predictor import model_available, predict_decisions
from core.services.weather_service import fetch_weather


# Seuils météorologiques (règles métier — secours si ML indisponible)
SEUIL_TEMP_SEMIS_MIN = 18
SEUIL_TEMP_SEMIS_MAX = 38
SEUIL_PLUIE_SEMIS_MM = 15
SEUIL_PROBA_PLUIE_SEMIS = 60
SEUIL_HUMIDITE_ARROSAGE = 70
SEUIL_PROBA_PLUIE_ARROSAGE = 40
SEUIL_PLUIE_ARROSAGE_MM = 2
SEUIL_VENT_RISQUE = 35
SEUIL_PLUIE_FORTE_MM = 25
SEUIL_PROBA_PLUIE_FORTE = 80
SEUIL_TEMP_CHALEUR = 38
SEUIL_HUMIDITE_SECHERESSE = 40


class DecisionEngine:
    """Analyse une exploitation et produit des recommandations agricoles."""

    def analyze(self, exploitation):
        """
        Point d'entrée principal.
        Retourne un dict structuré sauvegardé dans Analyse.resultat.
        """
        meteo = fetch_weather(
            float(exploitation.latitude),
            float(exploitation.longitude),
        )
        today = timezone.localdate()
        mois_actuel = today.month

        culture = exploitation.culture
        calendriers = get_calendriers_culture(culture)
        if not calendriers.exists():
            raise ValueError(
                f'Aucun calendrier FAO en base pour « {culture.nom} ». '
                'Exécutez : python manage.py import_fao_data'
            )

        dans_periode, cal_ref = est_dans_periode_semis(culture, mois_actuel)
        current = meteo['current']
        forecast = meteo['forecast']

        # Prédiction ML (One Acre Fund + LSMS) — None si modèle absent
        ml_pred = None
        if getattr(settings, 'USE_ML_MODEL', True) and model_available():
            ml_pred = predict_decisions(
                culture=culture.nom,
                type_sol=exploitation.type_sol.nom,
                mois=mois_actuel,
                latitude=float(exploitation.latitude),
                longitude=float(exploitation.longitude),
                temperature=float(current['temperature']),
                pluie_mm=float(current['pluie_mm']),
                humidite=float(current['humidite']),
                vent_kmh=float(current['vent_kmh']),
                probabilite_pluie=float(current['probabilite_pluie']),
            )

        peut_semer = self._evaluer_semis(
            exploitation, dans_periode, cal_ref, current, forecast, mois_actuel, ml_pred
        )
        arroser = self._evaluer_arrosage(exploitation, current, forecast, ml_pred)
        recolte = self._evaluer_recolte(exploitation, forecast, ml_pred)
        risques = self._evaluer_risques(forecast, ml_pred)
        resume = self._generer_resume(
            exploitation, peut_semer, arroser, recolte, risques
        )

        return {
            'peut_semer': peut_semer,
            'meilleure_periode_semis': {
                'periodes': get_periodes_semis_texte(culture),
                'explication': self._explication_meilleure_periode(
                    culture, forecast, dans_periode
                ),
            },
            'arroser': arroser,
            'recolte': recolte,
            'risques': risques,
            'resume': resume,
            'meta': {
                'culture': culture.nom,
                'type_sol': exploitation.type_sol.nom,
                'source_meteo': meteo['source'],
                'date_analyse': today.isoformat(),
                'modele_ml': bool(ml_pred),
                'source_ml': 'One Acre Fund + LSMS-ISA' if ml_pred else None,
            },
        }

    def _evaluer_semis(
        self, exploitation, dans_periode, cal_ref, current, forecast, mois, ml_pred
    ):
        culture = exploitation.culture

        if exploitation.statut == Exploitation.Statut.DEJA_SEME:
            return {
                'reponse': False,
                'explication': (
                    f'Vous avez déjà semé votre {culture.nom}. '
                    'Cette question concerne une future plantation.'
                ),
            }

        raisons_positives = []
        raisons_negatives = []

        if dans_periode:
            zone = cal_ref.zone_aez if cal_ref else ''
            session = cal_ref.session_info if cal_ref else ''
            detail = f' ({zone}, {session})' if zone else ''
            raisons_positives.append(
                f'Nous sommes en période de semis FAO pour le {culture.nom}{detail}.'
            )
        else:
            raisons_negatives.append(
                f'Le mois de {MOIS_FR[mois]} ne fait pas partie des périodes de semis '
                f'FAO recommandées pour le {culture.nom} en RDC.'
            )

        temp = current['temperature']
        if temp < SEUIL_TEMP_SEMIS_MIN:
            raisons_negatives.append(
                f'La température actuelle ({temp:.0f}°C) est trop basse pour un semis '
                f'(minimum recommandé : {SEUIL_TEMP_SEMIS_MIN}°C).'
            )
        elif temp > SEUIL_TEMP_SEMIS_MAX:
            raisons_negatives.append(
                f'La température actuelle ({temp:.0f}°C) est élevée pour un semis '
                f'(maximum conseillé : {SEUIL_TEMP_SEMIS_MAX}°C).'
            )
        else:
            raisons_positives.append(
                f'La température actuelle ({temp:.0f}°C) est favorable au semis.'
            )

        pluie_proche = forecast[:3]
        forte_pluie = any(
            d['probabilite_pluie'] > SEUIL_PROBA_PLUIE_SEMIS
            or d['pluie_mm'] > SEUIL_PLUIE_SEMIS_MM
            for d in pluie_proche
        )
        if forte_pluie:
            raisons_negatives.append(
                'Des précipitations importantes sont prévues dans les prochains jours, '
                'ce qui peut noyer les graines ou provoquer le pourrissement.'
            )
        else:
            raisons_positives.append(
                'Les précipitations prévues sur les 3 prochains jours sont acceptables.'
            )

        sol = exploitation.type_sol.nom.lower()
        sol_trop_sec = 'sablonneux' in sol and current['humidite'] < 45
        if sol_trop_sec:
            raisons_negatives.append(
                f'Votre sol {exploitation.type_sol.nom} se dessèche vite et '
                f"l'humidité est faible ({current['humidite']}%). "
                'Attendez une période plus humide ou prévoyez un apport d\'eau après le semis.'
            )

        # Règles métier (secours)
        peut_regles = (
            dans_periode
            and SEUIL_TEMP_SEMIS_MIN <= temp <= SEUIL_TEMP_SEMIS_MAX
            and not forte_pluie
            and not sol_trop_sec
        )

        # ML prioritaire si disponible (appris sur mois de semis observés en Afrique)
        if ml_pred is not None:
            peut = bool(ml_pred.get('peut_semer'))
            if peut:
                raisons_positives.append(
                    'Le modèle ML (données terrain Afrique : One Acre Fund / LSMS-ISA) '
                    f'indique que {MOIS_FR[mois]} est un mois favorable au semis '
                    f'pour des conditions proches des vôtres.'
                )
            else:
                raisons_negatives.append(
                    'Le modèle ML (données terrain Afrique : One Acre Fund / LSMS-ISA) '
                    f'n\'associe pas fortement le mois de {MOIS_FR[mois]} à un semis réussi '
                    'dans des contextes similaires.'
                )
        else:
            peut = peut_regles

        explication = ' '.join(raisons_positives + raisons_negatives)
        return {'reponse': peut, 'explication': explication}

    def _evaluer_arrosage(self, exploitation, current, forecast, ml_pred):
        culture = exploitation.culture

        if exploitation.statut == Exploitation.Statut.A_SEMER:
            return {
                'reponse': False,
                'explication': (
                    f'Votre {culture.nom} n\'est pas encore semé. '
                    "L'arrosage n'est pas nécessaire pour le moment."
                ),
            }

        humidite = current['humidite']
        pluie_prevue = forecast[0]['probabilite_pluie'] if forecast else 0
        pluie_mm = forecast[0]['pluie_mm'] if forecast else 0
        temp = current['temperature']

        besoin_regles = (
            humidite < SEUIL_HUMIDITE_ARROSAGE
            and pluie_prevue < SEUIL_PROBA_PLUIE_ARROSAGE
            and pluie_mm < SEUIL_PLUIE_ARROSAGE_MM
        )

        if ml_pred is not None:
            besoin = bool(ml_pred.get('doit_arroser'))
            if besoin:
                explication = (
                    f'Le modèle ML (parcelles irriguées / saisons sèches observées en Afrique) '
                    f'recommande un apport d\'eau pour votre {culture.nom} '
                    f'(humidité {humidite}%, pluie prévue {pluie_prevue}% / {pluie_mm} mm, '
                    f'température {temp:.0f}°C, sol {exploitation.type_sol.nom}).'
                )
            else:
                explication = (
                    f'Selon le modèle ML et la météo actuelle (humidité {humidite}%, '
                    f'pluie {pluie_prevue}% / {pluie_mm} mm), '
                    f'pas besoin d\'arroser votre {culture.nom} aujourd\'hui.'
                )
        else:
            besoin = besoin_regles
            if besoin:
                explication = (
                    f'L\'humidité est de {humidite}% (seuil : {SEUIL_HUMIDITE_ARROSAGE}%) '
                    f'et peu de pluie est prévue ({pluie_prevue}%, {pluie_mm} mm). '
                    f'Avec une température de {temp:.0f}°C, un apport d\'eau est recommandé '
                    f'pour votre {culture.nom} sur sol {exploitation.type_sol.nom}.'
                )
            else:
                explication = (
                    f'L\'humidité actuelle ({humidite}%) et les précipitations prévues '
                    f'({pluie_prevue}%, {pluie_mm} mm) sont suffisantes. '
                    f'Pas besoin d\'arroser votre {culture.nom} aujourd\'hui.'
                )

        return {'reponse': besoin, 'explication': explication}

    def _evaluer_recolte(self, exploitation, forecast, ml_pred):
        culture = exploitation.culture
        duree = culture.duree_recolte_jours

        if cal := get_calendriers_culture(culture).filter(
            growing_period_jours__isnull=False
        ).first():
            if cal.growing_period_jours:
                duree = cal.growing_period_jours

        date_semis = exploitation.date_semis_effective
        if not date_semis:
            return {
                'date_estimee': None,
                'explication': (
                    'Impossible d\'estimer la date de récolte : '
                    'aucune date de semis enregistrée.'
                ),
            }

        date_recolte = date_semis + timedelta(days=duree)
        today = timezone.localdate()

        explication = (
            f'À partir de votre date de semis ({date_semis.strftime("%d/%m/%Y")}) '
            f'et d\'une période de croissance de {duree} jours (données FAO), '
            f'la récolte du {culture.nom} est estimée autour du '
            f'{date_recolte.strftime("%d/%m/%Y")}.'
        )

        # Signal ML : le mois actuel ressemble aux mois de récolte observés
        if ml_pred is not None and ml_pred.get('pret_a_recolter'):
            explication += (
                ' Le modèle ML (mois de récolte observés One Acre Fund / LSMS-ISA) '
                'indique que le mois en cours correspond souvent à une période de récolte '
                'dans des contextes agricoles africains similaires.'
            )
        elif ml_pred is not None and today < date_recolte:
            explication += (
                ' Selon le modèle ML, ce n\'est en général pas encore le mois de récolte '
                'typique pour ce type de situation.'
            )

        pluie_recolte = any(
            d['pluie_mm'] > SEUIL_PLUIE_FORTE_MM for d in forecast[-3:]
        )
        if pluie_recolte:
            explication += (
                ' Attention : de fortes pluies sont prévues à l\'approche de cette période. '
                'Surveillez l\'état de vos plants et anticipez si nécessaire.'
            )

        return {
            'date_estimee': date_recolte.isoformat(),
            'date_estimee_affichage': date_recolte.strftime('%d/%m/%Y'),
            'explication': explication,
            'pret_selon_ml': bool(ml_pred and ml_pred.get('pret_a_recolter')),
        }

    def _evaluer_risques(self, forecast, ml_pred):
        risques = []

        for day in forecast:
            date_fmt = day['date']

            if day['probabilite_pluie'] >= SEUIL_PROBA_PLUIE_FORTE or day['pluie_mm'] >= SEUIL_PLUIE_FORTE_MM:
                risques.append({
                    'type': 'Fortes pluies',
                    'niveau': 'élevé',
                    'description': (
                        f'Le {date_fmt} : pluie prévue à {day["pluie_mm"]} mm '
                        f'(probabilité {day["probabilite_pluie"]}%). '
                        'Risque de noyage des racines ou de maladies fongiques.'
                    ),
                })

            if day['temperature'] >= SEUIL_TEMP_CHALEUR:
                risques.append({
                    'type': 'Chaleur excessive',
                    'niveau': 'modéré',
                    'description': (
                        f'Le {date_fmt} : température maximale de {day["temperature"]:.0f}°C. '
                        'Stress thermique possible pour les jeunes plants.'
                    ),
                })

            if day.get('temperature_min', day['temperature']) < 10:
                risques.append({
                    'type': 'Froid',
                    'niveau': 'modéré',
                    'description': (
                        f'Le {date_fmt} : température minimale basse '
                        f'({day.get("temperature_min", day["temperature"]):.0f}°C).'
                    ),
                })

            if day['vent_kmh'] >= SEUIL_VENT_RISQUE:
                risques.append({
                    'type': 'Vent fort',
                    'niveau': 'modéré',
                    'description': (
                        f'Le {date_fmt} : vents jusqu\'à {day["vent_kmh"]:.0f} km/h. '
                        'Risque de casse ou d\'évaporation accrue.'
                    ),
                })

            if day['humidite'] < SEUIL_HUMIDITE_SECHERESSE and day['pluie_mm'] < 1:
                risques.append({
                    'type': 'Sécheresse',
                    'niveau': 'modéré',
                    'description': (
                        f'Le {date_fmt} : humidité faible ({day["humidite"]}%) '
                        'et peu de pluie. Surveillez l\'hydratation du sol.'
                    ),
                })

        # Risques issus du modèle (chocs observés sur parcelles africaines)
        if ml_pred is not None:
            mapping = [
                ('risque_secheresse', 'Sécheresse (ML)', 'élevé',
                 'Le modèle ML signale un profil proche de parcelles ayant subi une sécheresse.'),
                ('risque_pluie_forte', 'Fortes pluies / inondation (ML)', 'élevé',
                 'Le modèle ML signale un profil proche de parcelles touchées par excès d\'eau ou inondation.'),
                ('risque_ravageurs', 'Ravageurs (ML)', 'modéré',
                 'Le modèle ML signale un profil proche de parcelles touchées par des ravageurs.'),
                ('risque_maladie', 'Maladie / choc cultural (ML)', 'modéré',
                 'Le modèle ML signale un profil proche de parcelles ayant subi un choc cultural / maladie.'),
            ]
            for key, typ, niveau, desc in mapping:
                if ml_pred.get(key):
                    risques.append({
                        'type': typ,
                        'niveau': niveau,
                        'description': desc + ' Source : One Acre Fund / LSMS-ISA.',
                    })

        if not risques:
            risques.append({
                'type': 'Aucun risque majeur',
                'niveau': 'faible',
                'description': (
                    'Les prévisions sur 7 jours ne révèlent pas de risque climatique '
                    'majeur pour votre culture.'
                ),
            })

        return risques[:8]

    def _explication_meilleure_periode(self, culture, forecast, dans_periode):
        periodes = get_periodes_semis_texte(culture)
        base = f'Selon le calendrier FAO pour le {culture.nom} en RDC : {periodes}.'

        jours_favorables = [
            d for d in forecast
            if (
                SEUIL_TEMP_SEMIS_MIN <= d['temperature'] <= SEUIL_TEMP_SEMIS_MAX
                and d['probabilite_pluie'] < SEUIL_PROBA_PLUIE_SEMIS
                and d['pluie_mm'] < SEUIL_PLUIE_SEMIS_MM
            )
        ]
        if jours_favorables:
            dates = ', '.join(d['date'] for d in jours_favorables[:3])
            base += (
                f' Sur les 7 prochains jours, les conditions météo les plus favorables '
                f'au semis semblent être : {dates}.'
            )
        elif dans_periode:
            base += (
                ' Vous êtes dans une période FAO de semis, mais la météo des prochains '
                'jours est mitigée — surveillez les prévisions avant de planter.'
            )
        else:
            base += (
                ' Attendez la prochaine fenêtre de semis FAO pour de meilleurs résultats.'
            )
        return base

    def _generer_resume(self, exploitation, peut_semer, arroser, recolte, risques):
        culture = exploitation.culture
        parties = [f'Analyse pour votre {culture.nom} (sol {exploitation.type_sol.nom}).']

        if exploitation.statut == Exploitation.Statut.A_SEMER:
            if peut_semer['reponse']:
                parties.append('Les conditions semblent favorables pour semer maintenant.')
            else:
                parties.append('Il est préférable d\'attendre avant de semer.')
        else:
            if arroser['reponse']:
                parties.append('Un arrosage est recommandé aujourd\'hui.')
            else:
                parties.append('Pas d\'arrosage nécessaire pour le moment.')

        if recolte.get('date_estimee_affichage'):
            parties.append(
                f'Récolte estimée vers le {recolte["date_estimee_affichage"]}.'
            )

        risques_eleves = [r for r in risques if r['niveau'] == 'élevé']
        if risques_eleves:
            parties.append(
                f'{len(risques_eleves)} risque(s) climatique(s) élevé(s) détecté(s) '
                'sur les 7 prochains jours.'
            )

        return ' '.join(parties)


def analyser_exploitation(exploitation):
    """Raccourci : analyse et retourne le résultat."""
    return DecisionEngine().analyze(exploitation)
