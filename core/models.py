from django.conf import settings
from django.db import models


class Culture(models.Model):
    """Culture agricole de référence (maïs, riz, haricot…)."""

    nom = models.CharField('nom', max_length=150)
    fao_crop_id = models.CharField(
        'identifiant FAO',
        max_length=10,
        blank=True,
        unique=True,
        null=True,
        help_text='Identifiant de la culture dans l\'API FAO Crop Calendar.',
    )
    duree_recolte_jours = models.PositiveIntegerField(
        'durée moyenne avant récolte (jours)',
        default=90,
        help_text='Nombre de jours entre le semis et la récolte.',
    )

    class Meta:
        verbose_name = 'culture'
        verbose_name_plural = 'cultures'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class TypeSol(models.Model):
    """Type de sol de référence."""

    nom = models.CharField('nom', max_length=100, unique=True)

    class Meta:
        verbose_name = 'type de sol'
        verbose_name_plural = 'types de sol'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Exploitation(models.Model):
    """Parcelle / culture enregistrée par un agriculteur."""

    class Statut(models.TextChoices):
        A_SEMER = 'A_SEMER', 'Je vais semer'
        DEJA_SEME = 'DEJA_SEME', "J'ai déjà semé"

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exploitations',
        verbose_name='utilisateur',
    )
    culture = models.ForeignKey(
        Culture,
        on_delete=models.PROTECT,
        related_name='exploitations',
        verbose_name='culture',
    )
    type_sol = models.ForeignKey(
        TypeSol,
        on_delete=models.PROTECT,
        related_name='exploitations',
        verbose_name='type de sol',
    )
    latitude = models.DecimalField(
        'latitude',
        max_digits=9,
        decimal_places=6,
    )
    longitude = models.DecimalField(
        'longitude',
        max_digits=9,
        decimal_places=6,
    )
    statut = models.CharField(
        'statut',
        max_length=20,
        choices=Statut.choices,
    )
    date_prevue_semis = models.DateField(
        'date prévue de semis',
        null=True,
        blank=True,
    )
    date_reelle_semis = models.DateField(
        'date réelle de semis',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField('créé le', auto_now_add=True)
    updated_at = models.DateTimeField('modifié le', auto_now=True)

    class Meta:
        verbose_name = 'exploitation'
        verbose_name_plural = 'exploitations'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.culture.nom} — {self.utilisateur.username}'

    @property
    def date_semis_effective(self):
        """Date de semis utilisée pour les calculs (réelle ou prévue)."""
        if self.statut == self.Statut.DEJA_SEME:
            return self.date_reelle_semis
        return self.date_prevue_semis


class Analyse(models.Model):
    """Historique des recommandations agricoles pour une exploitation."""

    exploitation = models.ForeignKey(
        Exploitation,
        on_delete=models.CASCADE,
        related_name='analyses',
        verbose_name='exploitation',
    )
    resultat = models.JSONField(
        'résultat',
        help_text='Recommandations structurées produites par le moteur de décision.',
    )
    date_analyse = models.DateTimeField('date d\'analyse', auto_now_add=True)

    class Meta:
        verbose_name = 'analyse'
        verbose_name_plural = 'analyses'
        ordering = ['-date_analyse']

    def __str__(self):
        return f'Analyse {self.exploitation.culture.nom} — {self.date_analyse:%d/%m/%Y %H:%M}'


class FaoCalendrier(models.Model):
    """Périodes de semis et récolte issues du calendrier agricole FAO."""

    culture = models.ForeignKey(
        Culture,
        on_delete=models.CASCADE,
        related_name='calendriers_fao',
        verbose_name='culture',
    )
    pays_code = models.CharField(
        'code pays ISO',
        max_length=3,
        default='CD',
        help_text='Code pays FAO (CD = République Démocratique du Congo).',
    )
    zone_aez = models.CharField(
        'zone agro-écologique',
        max_length=150,
        default='Inconnue',
        help_text='Zone agro-écologique FAO (ex. Sud Ouest).',
    )
    zone_id = models.CharField(
        'identifiant zone FAO',
        max_length=10,
        blank=True,
    )
    session_info = models.CharField(
        'saison / session',
        max_length=100,
        blank=True,
        help_text='Ex. Saison A, Saison B.',
    )
    mois_semis_debut = models.PositiveSmallIntegerField(
        'mois début semis',
        help_text='Mois (1-12) du début de la période de semis.',
    )
    mois_semis_fin = models.PositiveSmallIntegerField(
        'mois fin semis',
        help_text='Mois (1-12) de fin de la période de semis.',
    )
    mois_recolte_debut = models.PositiveSmallIntegerField(
        'mois début récolte',
        help_text='Mois (1-12) du début de la période de récolte.',
    )
    mois_recolte_fin = models.PositiveSmallIntegerField(
        'mois fin récolte',
        help_text='Mois (1-12) de fin de la période de récolte.',
    )
    growing_period_jours = models.PositiveIntegerField(
        'période de croissance (jours)',
        null=True,
        blank=True,
    )
    fao_last_updated = models.CharField(
        'dernière mise à jour FAO',
        max_length=20,
        blank=True,
    )

    class Meta:
        verbose_name = 'calendrier FAO'
        verbose_name_plural = 'calendriers FAO'
        ordering = ['culture__nom', 'zone_aez', 'session_info']
        constraints = [
            models.UniqueConstraint(
                fields=['culture', 'pays_code', 'zone_aez', 'session_info'],
                name='uniq_fao_calendrier_session',
            ),
        ]

    def __str__(self):
        label = f'{self.culture.nom} — {self.zone_aez}'
        if self.session_info:
            label += f' ({self.session_info})'
        return label
