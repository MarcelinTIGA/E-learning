"""
EFG E-Learning Platform — Administration Django
================================================
Ce fichier configure l'interface /admin/ de Django.

RÔLE :
L'interface /admin/ est un panneau web généré automatiquement par Django.
Elle permet de gérer toutes les données de la plateforme sans écrire de code :
- Créer/modifier/supprimer des formations, utilisateurs, catégories...
- Visualiser les inscriptions, paiements, certificats...
- Très utile pour les tests et la gestion quotidienne

COMMENT Y ACCÉDER :
1. Créer un superuser :   python manage.py createsuperuser
2. Lancer le serveur :    python manage.py runserver
3. Ouvrir dans le navigateur : http://localhost:8000/admin/

ORGANISATION :
Chaque classe ModelAdmin = la configuration d'un modèle dans le panneau admin.
- list_display   → colonnes affichées dans la liste
- list_filter    → filtres dans la barre latérale droite
- search_fields  → champs pris en compte par la barre de recherche
- readonly_fields → champs visibles mais non modifiables (ex: id, dates)
- ordering       → tri par défaut de la liste
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User, Category, Formation, Module, Lesson,
    Quiz, Question, AnswerOption,
    Enrollment, Payment, LessonProgress,
    QuizAttempt, QuizResponse, Certificate,
)


# ================================================================
# 1. UTILISATEUR
# ================================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Configuration de l'affichage des utilisateurs dans /admin/.

    On hérite de BaseUserAdmin (le UserAdmin de Django) pour conserver
    les fonctionnalités de gestion des mots de passe (formulaire de changement,
    bouton "changer le mot de passe"...).

    Personnalisé pour notre modèle sans username (connexion par email).
    """

    # Colonnes affichées dans la liste des utilisateurs
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'created_at']

    # Filtres disponibles dans la barre latérale (clique pour filtrer)
    list_filter = ['role', 'is_active', 'auth_provider', 'created_at']

    # Champs pris en compte par la barre de recherche en haut
    search_fields = ['email', 'first_name', 'last_name']

    # Tri par défaut : les utilisateurs les plus récents en premier
    ordering = ['-created_at']

    # Champs non modifiables (affichés en lecture seule dans le formulaire de détail)
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_login']

    # fieldsets → définit la mise en page du formulaire de détail (groupes de champs)
    # Chaque tuple = (Titre du groupe, {champs})
    fieldsets = (
        (None, {
            'fields': ('id', 'email', 'password')
        }),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'phone', 'bio', 'avatar_url')
        }),
        ('Rôle et statut', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('OAuth (connexion Google/Facebook)', {
            # classes=('collapse',) → ce groupe est réduit par défaut (clique pour développer)
            # Utile pour les champs techniques peu souvent modifiés
            'fields': ('auth_provider', 'auth_provider_id'),
            'classes': ('collapse',),
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'last_login'),
            'classes': ('collapse',),
        }),
    )

    # add_fieldsets → mise en page du formulaire de CRÉATION d'un utilisateur
    # (différent de fieldsets qui est utilisé pour la modification)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),  # 'wide' = formulaire en pleine largeur
            'fields': (
                'email', 'first_name', 'last_name',
                'password1', 'password2',  # password1 et password2 = champs standard de Django pour la création
                'role',
            ),
        }),
    )


# ================================================================
# 2. CATÉGORIE
# ================================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    # prepopulated_fields → Django remplit automatiquement le slug
    # quand on tape le nom dans le formulaire (converti en minuscules avec tirets)
    # Exemple : "Développement Web" → "developpement-web"
    ordering = ['order', 'name']
    readonly_fields = ['id', 'created_at', 'updated_at']


# ================================================================
# 3. FORMATION avec ses modules en ligne
# ================================================================

class ModuleInline(admin.TabularInline):
    """
    Inline → affiche les modules directement dans la page de détail d'une formation.
    TabularInline = affichage en tableau (une ligne par module).
    StackedInline = affichage empilé (chaque module dans sa propre boîte) — plus lisible
    mais prend plus de place.
    """

    model = Module
    # extra=0 → n'affiche pas de lignes vides pour ajouter de nouveaux modules
    # (on les ajoute via le bouton "Ajouter un module" en bas)
    extra = 0
    fields = ['title', 'order', 'is_preview']
    ordering = ['order']


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'formateur', 'category',
        'level', 'status', 'is_published', 'price', 'published_at',
    ]
    list_filter = ['status', 'is_published', 'level', 'category', 'created_at']
    search_fields = ['title', 'description', 'formateur__email']
    ordering = ['-created_at']
    readonly_fields = ['id', 'published_at', 'created_at', 'updated_at']

    # Affiche les modules directement dans la page de la formation
    inlines = [ModuleInline]

    # list_editable → permet de modifier ces champs DIRECTEMENT dans la liste
    # sans avoir à ouvrir le détail de chaque formation
    list_editable = ['is_published', 'status']

    # raw_id_fields → pour les ForeignKey avec beaucoup de valeurs (ex: des milliers de formateurs)
    # Remplace le menu déroulant par un champ texte + bouton de recherche → plus rapide
    raw_id_fields = ['formateur']


# ================================================================
# 4. MODULE avec ses leçons en ligne
# ================================================================

class LessonInline(admin.TabularInline):
    """Leçons affichées directement dans la page d'un module."""

    model = Lesson
    extra = 0
    fields = ['title', 'content_type', 'order', 'duration_min', 'is_preview']
    ordering = ['order']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'formation', 'order', 'is_preview', 'created_at']
    list_filter = ['is_preview', 'formation', 'created_at']
    search_fields = ['title', 'formation__title']
    ordering = ['formation', 'order']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [LessonInline]


# ================================================================
# 5. LEÇON
# ================================================================

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'module', 'content_type',
        'duration_min', 'order', 'is_preview',
    ]
    list_filter = ['content_type', 'is_preview', 'video_source']
    search_fields = ['title', 'module__title', 'module__formation__title']
    ordering = ['module__formation', 'module__order', 'order']
    readonly_fields = ['id', 'created_at', 'updated_at']


# ================================================================
# 6. QUIZ avec ses questions en ligne
# ================================================================

class AnswerOptionInline(admin.TabularInline):
    """Options de réponse affichées dans la page d'une question."""

    model = AnswerOption
    extra = 0
    fields = ['option_text', 'is_correct', 'order']
    ordering = ['order']


class QuestionInline(admin.StackedInline):
    """
    Questions affichées dans la page d'un quiz.
    StackedInline (et non TabularInline) car les questions ont beaucoup de champs.
    """

    model = Question
    extra = 0
    fields = ['question_text', 'question_type', 'points', 'order']
    ordering = ['order']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'passing_score', 'max_attempts', 'created_at']
    list_filter = ['passing_score', 'created_at']
    search_fields = ['title', 'module__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'quiz', 'question_type', 'points', 'order']
    list_filter = ['question_type']
    search_fields = ['question_text', 'quiz__title']
    ordering = ['quiz', 'order']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [AnswerOptionInline]


@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    list_display = ['option_text', 'question', 'is_correct', 'order']
    list_filter = ['is_correct']
    search_fields = ['option_text', 'question__question_text']
    readonly_fields = ['id', 'created_at', 'updated_at']


# ================================================================
# 7. INSCRIPTION
# ================================================================

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'formation', 'status',
        'progress_percent', 'enrolled_at', 'completed_at',
    ]
    list_filter = ['status', 'enrolled_at']
    search_fields = ['user__email', 'formation__title']
    ordering = ['-enrolled_at']

    # Les champs de progression sont calculés automatiquement → lecture seule
    readonly_fields = ['id', 'enrolled_at', 'created_at', 'updated_at']

    # list_display_links → définit sur quels champs on peut cliquer pour ouvrir le détail
    list_display_links = ['user', 'formation']


# ================================================================
# 8. PAIEMENT
# ================================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'formation', 'amount', 'currency',
        'payment_method', 'status', 'paid_at', 'created_at',
    ]
    list_filter = ['status', 'payment_method', 'currency', 'created_at']
    search_fields = ['user__email', 'formation__title', 'transaction_ref']
    ordering = ['-created_at']

    # Un paiement ne doit jamais être modifié manuellement (journal comptable)
    # Tous les champs sont en lecture seule — modifications uniquement via les vues API
    readonly_fields = [
        'id', 'user', 'formation', 'amount', 'currency',
        'payment_method', 'transaction_ref',
        'paid_at', 'created_at', 'updated_at',
    ]


# ================================================================
# 9. PROGRESSION PAR LEÇON
# ================================================================

@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'lesson', 'is_completed',
        'video_position_sec', 'started_at', 'completed_at',
    ]
    list_filter = ['is_completed', 'started_at']
    search_fields = ['user__email', 'lesson__title']
    ordering = ['-started_at']
    readonly_fields = ['id', 'started_at', 'created_at', 'updated_at']


# ================================================================
# 10. TENTATIVES DE QUIZ
# ================================================================

class QuizResponseInline(admin.TabularInline):
    """Réponses d'une tentative affichées directement dans sa page de détail."""

    model = QuizResponse
    extra = 0
    fields = ['question', 'selected_option', 'is_correct']
    # Les réponses ne se modifient pas — elles sont enregistrées lors de la soumission
    readonly_fields = ['question', 'selected_option', 'is_correct']

    # can_delete=False → interdit la suppression d'une réponse depuis l'admin
    # (intégrité des résultats)
    can_delete = False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'quiz', 'score', 'is_passed',
        'attempt_number', 'started_at', 'completed_at',
    ]
    list_filter = ['is_passed', 'started_at']
    search_fields = ['user__email', 'quiz__title']
    ordering = ['-started_at']
    readonly_fields = [
        'id', 'score', 'is_passed', 'attempt_number',
        'started_at', 'completed_at', 'created_at', 'updated_at',
    ]
    inlines = [QuizResponseInline]


@admin.register(QuizResponse)
class QuizResponseAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question', 'selected_option', 'is_correct']
    list_filter = ['is_correct']
    search_fields = ['attempt__user__email', 'question__question_text']
    readonly_fields = ['id', 'is_correct', 'created_at', 'updated_at']


# ================================================================
# 11. CERTIFICAT
# ================================================================

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = [
        'certificate_code', 'user', 'formation', 'issued_at',
    ]
    list_filter = ['issued_at']
    search_fields = ['certificate_code', 'user__email', 'formation__title']
    ordering = ['-issued_at']

    # Le certificat est généré automatiquement — aucun champ ne doit être modifiable
    readonly_fields = [
        'id', 'certificate_code', 'verification_url',
        'issued_at', 'created_at', 'updated_at',
    ]
