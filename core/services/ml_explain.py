"""
Explications pédagogiques des prédictions ML AgriDec.

Ces textes relient chaque réponse (Oui/Non) à la façon dont le modèle
a été entraîné (One Acre Fund + LSMS-ISA), pour la page « Tester le ML ».
"""

# Noms affichés pour chaque cible du modèle
TARGET_LABELS = {
    'peut_semer': 'Puis-je semer ?',
    'doit_arroser': 'Dois-je arroser ?',
    'pret_a_recolter': 'Est-ce un mois de récolte ?',
    'risque_secheresse': 'Risque sécheresse ?',
    'risque_pluie_forte': 'Risque fortes pluies / inondation ?',
    'risque_ravageurs': 'Risque ravageurs ?',
    'risque_maladie': 'Risque maladie / choc cultural ?',
}

# Cause liée aux données d'entraînement (toujours vraie pour ce modèle)
CAUSE_DONNEES = (
    'Oui — cette réponse vient surtout de la façon dont on a labellisé '
    'One Acre Fund + LSMS-ISA, pas d’un agronome qui regarde ta parcelle aujourd’hui.'
)


def explain_prediction(target: str, value: int, *, mois: int, culture: str) -> dict:
    """
    Retourne un dict {titre, reponse, explication, cause_donnees, detail_entrainement}
    pour une cible du modèle.
    """
    oui = bool(value)
    culture = culture or 'cette culture'

    if target == 'peut_semer':
        if oui:
            explication = (
                f'Le modèle associe le mois {mois} à un mois où des agriculteurs '
                f'ont réellement semé des cultures proches de « {culture} » '
                f'dans les enquêtes Afrique (dates/mois de semis observés).'
            )
            detail = (
                'Entraînement : pour chaque parcelle, on a mis peut_semer=1 '
                'uniquement sur le mois_de_semis_observé, sinon 0 (12 lignes / parcelle).'
            )
        else:
            explication = (
                f'Le mois {mois} ne correspond pas (assez souvent) aux mois de semis '
                f'observés pour des profils proches de « {culture} » dans One Acre Fund / LSMS. '
                f'Ce n’est pas un jugement météo du jour.'
            )
            detail = (
                'Cause données : très peu de mois positifs (environ 1 mois sur 12 par parcelle), '
                'donc le modèle dit souvent Non hors des fenêtres de semis apprises.'
            )

    elif target == 'doit_arroser':
        if oui:
            explication = (
                f'Le modèle rapproche votre situation de parcelles marquées « irriguées » (LSMS) '
                f'ou de saisons peu pluvieuses (One Acre Fund) pendant la saison de culture.'
            )
            detail = (
                'Attention : le label n’était pas « arroser aujourd’hui car humidité basse », '
                'mais plutôt « cette parcelle était irriguée / saison sèche ».'
            )
        else:
            explication = (
                f'Le modèle dit Non surtout parce que, dans les données d’entraînement, '
                f'la majorité des parcelles sont pluviales (non irriguées). '
                f'Environ 90 % des exemples ont doit_arroser=0. '
                f'Il ignore largement « 0 mm de pluie aujourd’hui ».'
            )
            detail = (
                'Cause données : LSMS.irrigated est rare (=1) ; One Acre Fund n’a pas de décision '
                'd’arrosage journalière. D’où des Non fréquents même en saison sèche réelle.'
            )

    elif target == 'pret_a_recolter':
        if oui:
            explication = (
                f'Le mois {mois} ressemble aux mois de récolte observés '
                f'(harvest_date / harvest_end_month) pour des cultures proches.'
            )
            detail = (
                'Entraînement : pret_a_recolter=1 seulement si mois == mois_de_recolte_observé.'
            )
        else:
            explication = (
                f'Le mois {mois} n’est pas typiquement un mois de récolte '
                f'dans les historiques Afrique utilisés pour « {culture} ».'
            )
            detail = (
                'Cause données : comme pour le semis, un seul mois positif sur 12 par parcelle '
                '→ beaucoup de Non.'
            )

    elif target == 'risque_secheresse':
        if oui:
            explication = (
                'Profil proche de parcelles ayant déclaré un choc sécheresse (LSMS) '
                'ou une saison très peu pluvieuse (One Acre Fund).'
            )
            detail = 'Label issu de drought_shock / pluie saisonnière faible — pas de capteur humidité du jour.'
        else:
            explication = (
                'Le modèle ne rapproche pas assez votre entrée des parcelles '
                'ayant subi une sécheresse déclarée dans les enquêtes.'
            )
            detail = 'Cause données : chocs déclaratifs (oui/non) au niveau saison/parcelle, pas alerte météo 7 jours.'

    elif target == 'risque_pluie_forte':
        if oui:
            explication = (
                'Profil proche de parcelles avec excès d’eau (One Acre Fund water_excess) '
                'ou chocs pluie/inondation (LSMS rain_shock / flood_shock).'
            )
            detail = 'Labels d’adversités terrain saisonnières, pas prévision Open-Meteo du jour.'
        else:
            explication = (
                'Peu de similarité avec les parcelles marquées excès d’eau / inondation '
                'dans les datasets d’entraînement.'
            )
            detail = 'Cause données : événements rares et déclaratifs → souvent Non.'

    elif target == 'risque_ravageurs':
        if oui:
            explication = (
                'Profil proche de parcelles avec ravageurs / Striga (One Acre Fund) '
                'ou pests_shock (LSMS).'
            )
            detail = 'Présence/absence déclarée sur la parcelle, pas observation terrain RDC du jour.'
        else:
            explication = (
                'Le modèle ne détecte pas un profil typique des parcelles '
                'ayant déclaré des ravageurs dans l’entraînement.'
            )
            detail = 'Cause données : label binaire d’enquête, fortement lié au contexte local des pays LSMS/OAF.'

    elif target == 'risque_maladie':
        if oui:
            explication = (
                'Profil proche de parcelles avec maladie (One Acre Fund disease) '
                'ou choc cultural (LSMS crop_shock).'
            )
            detail = 'Encore une fois : déclaration d’enquête, pas diagnostic phytosanitaire temps réel.'
        else:
            explication = (
                'Peu de similarité avec les parcelles ayant déclaré maladie / choc cultural.'
            )
            detail = 'Cause données : labels d’enquête (souvent déséquilibrés).'

    else:
        explication = 'Cible inconnue.'
        detail = ''

    return {
        'cle': target,
        'titre': TARGET_LABELS.get(target, target),
        'valeur': int(oui),
        'reponse': 'Oui' if oui else 'Non',
        'explication': explication,
        'cause_donnees': CAUSE_DONNEES,
        'detail_entrainement': detail,
    }


def explain_all(predictions: dict, *, mois: int, culture: str) -> list[dict]:
    """Liste ordonnée d’explications pour toutes les cibles prédites."""
    order = [
        'peut_semer',
        'doit_arroser',
        'pret_a_recolter',
        'risque_secheresse',
        'risque_pluie_forte',
        'risque_ravageurs',
        'risque_maladie',
    ]
    results = []
    for key in order:
        if key in predictions:
            results.append(
                explain_prediction(key, predictions[key], mois=mois, culture=culture)
            )
    # cibles éventuelles non listées
    for key, val in predictions.items():
        if key not in order:
            results.append(explain_prediction(key, val, mois=mois, culture=culture))
    return results
