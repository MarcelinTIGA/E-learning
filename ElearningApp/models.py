"""
EFG E-Learning Platform — Django Models
========================================
Ce fichier définit toutes les tables de la base de données.
En Django, chaque classe Python ici = une table dans la base de données.
Chaque attribut de classe = une colonne dans cette table.

14 tables au total, correspondant à la vision du produit EFG.
"""

import uuid  # Pour générer des identifiants uniques (ex: "550e8400-e29b-...")
from django.db import models  # La boîte à outils de Django pour créer des tables
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
# AbstractBaseUser  → classe vide pour créer un système de connexion personnalisé
# BaseUserManager  → classe pour gérer la création des utilisateurs (create_user, create_superuser)
# PermissionsMixin → ajoute les champs is_superuser, groups, user_permissions (nécessaires pour /admin/)
from django.core.validators import MinValueValidator, MaxValueValidator
# Ces validateurs vérifient les valeurs AVANT de les enregistrer en base
# Ex: MinValueValidator(0) sur un prix → interdit les prix négatifs
from django.utils import timezone  # Pour obtenir la date/heure actuelle (compatible avec les fuseaux horaires)


# ============================================================
# MODÈLE DE BASE (partagé par toutes les tables sauf User)
# ============================================================

class BaseModel(models.Model):
    """
    Ce modèle abstrait est le "parent" de presque toutes nos tables.
    "Abstrait" = Django ne crée PAS de table "basemodel" en base.
    Il copie simplement ces 3 champs dans chaque table enfant.

    Résultat : toutes nos tables auront automatiquement :
    - un identifiant unique (id)
    - une date de création (created_at)
    - une date de dernière modification (updated_at)
    """

    id = models.UUIDField(
        primary_key=True,    # Ce champ est la clé primaire (identifiant unique de chaque ligne)
        default=uuid.uuid4,  # Génère automatiquement un UUID à la création (ex: "550e8400-e29b-...")
        editable=False       # On ne peut pas modifier l'id manuellement — c'est voulu
    )
    # auto_now_add=True → la date est écrite UNE SEULE FOIS à la création, jamais modifiée ensuite
    created_at = models.DateTimeField(auto_now_add=True)
    # auto_now=True → la date est mise à jour AUTOMATIQUEMENT à chaque modification (.save())
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True  # IMPORTANT : sans ça, Django essaierait de créer une table "basemodel"


# ============================================================
# 1. USER — Utilisateur personnalisé
# ============================================================

class UserManager(BaseUserManager):
    """
    Le "manager" est l'outil qui permet de créer des utilisateurs.
    On le personnalise parce qu'on utilise l'EMAIL pour se connecter
    (au lieu du "username" habituel de Django).

    Il sera appelé ainsi dans le code :
        User.objects.create_user(email="...", password="...")
        User.objects.create_superuser(email="...", password="...")
    """

    def create_user(self, email, password=None, **extra_fields):
        # **extra_fields capture tous les autres arguments passés (first_name, last_name, role, etc.)
        if not email:
            raise ValueError("L'adresse email est obligatoire.")

        # normalize_email() met le domaine en minuscules pour éviter les doublons
        # Exemple : "User@GMAIL.COM" devient "User@gmail.com"
        email = self.normalize_email(email)

        # Crée l'objet User en mémoire (pas encore enregistré en base)
        user = self.model(email=email, **extra_fields)

        # set_password() chiffre le mot de passe avant de le stocker
        # JAMAIS stocker un mot de passe en clair dans la base
        # Si password=None (connexion Google/Facebook), le compte n'aura pas de mot de passe
        user.set_password(password)

        # using=self._db → support multi-base de données (bonne pratique Django)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # Un superuser est un administrateur avec accès total
        # setdefault() → applique la valeur seulement si le champ n'est pas déjà défini
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('is_staff', True)       # Accès au panneau /admin/ de Django
        extra_fields.setdefault('is_superuser', True)   # Toutes les permissions Django
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Notre modèle utilisateur personnalisé.
    Remplace complètement le User par défaut de Django.

    IMPORTANT : AUTH_USER_MODEL = 'ElearningApp.User' dans settings.py
    indique à Django d'utiliser CE modèle au lieu du sien.

    Un utilisateur peut avoir 3 rôles :
    - apprenant  → suit des formations
    - formateur  → crée des formations
    - admin      → gère tout (a aussi les droits du formateur)
    """

    # TextChoices crée une liste de valeurs autorisées pour un champ
    # Format : CONSTANTE = 'valeur_en_base', 'Libellé affiché'
    class Role(models.TextChoices):
        APPRENANT = 'apprenant', 'Apprenant'
        FORMATEUR = 'formateur', 'Formateur'
        ADMIN = 'admin', 'Administrateur'

    class AuthProvider(models.TextChoices):
        # Indique comment l'utilisateur s'est inscrit
        EMAIL = 'email', 'Email'
        GOOGLE = 'google', 'Google'
        FACEBOOK = 'facebook', 'Facebook'

    # On redéfinit l'id ici (pas hérité de BaseModel car User a une structure spéciale)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # unique=True → impossible d'avoir deux comptes avec le même email
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    # blank=True → ce champ n'est pas obligatoire dans les formulaires
    # default='' → la valeur par défaut est une chaîne vide (pas NULL)
    phone = models.CharField(max_length=20, blank=True, default='')
    bio = models.TextField(blank=True, default='')
    avatar_url = models.URLField(blank=True, default='')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,   # Restreint les valeurs acceptées à celles définies dans Role
        default=Role.APPRENANT, # Tout nouvel utilisateur est apprenant par défaut
    )

    # auth_provider : méthode d'inscription (email classique, Google ou Facebook)
    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        default=AuthProvider.EMAIL,
    )
    # auth_provider_id : l'identifiant unique renvoyé par Google ou Facebook
    # Exemple Google : "110248495921238986420"
    # Utilisé pour reconnaître l'utilisateur lors de ses prochaines connexions OAuth
    auth_provider_id = models.CharField(max_length=255, blank=True, default='')

    # Ces deux champs sont redéfinis pour éviter un conflit avec auth.User de Django
    # (les deux modèles ne peuvent pas avoir le même "related_name" vers Group et Permission)
    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name='efg_users',       # Nom unique pour l'accès inverse : group.efg_users.all()
        related_query_name='efg_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='efg_users',
        related_query_name='efg_user',
    )

    is_active = models.BooleanField(default=True)   # False = compte désactivé (ne peut plus se connecter)
    is_staff = models.BooleanField(default=False)    # True = accès au panneau /admin/ de Django

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Lie ce modèle au UserManager défini plus haut
    objects = UserManager()

    # Indique à Django que l'identifiant de connexion est l'email (et non le username)
    USERNAME_FIELD = 'email'

    # Champs demandés en plus de l'email lors de "python manage.py createsuperuser"
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'          # Nom exact de la table en base de données
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        # Définit ce qu'on voit dans le panneau admin et dans les logs
        # Exemple : "Jean Dupont (jean@example.com)"
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def is_formateur(self):
        # @property = on l'appelle comme un attribut : user.is_formateur (sans parenthèses)
        # Retourne True pour les formateurs ET les admins
        # (un admin peut aussi créer des formations selon la vision du produit)
        return self.role in (self.Role.FORMATEUR, self.Role.ADMIN)

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN


# ============================================================
# 2. CATEGORY — Catégorie de formations
# ============================================================

class Category(BaseModel):
    """
    Catégorie pour classer les formations (ex: Développement Web, Marketing...).
    Une formation appartient à une catégorie.
    """
    name = models.CharField(max_length=100, unique=True)

    # Le slug est une version "URL-friendly" du nom
    # Exemple : "Développement Web" → "developpement-web"
    # Utilisé dans les URLs : /api/categories/developpement-web/
    slug = models.SlugField(max_length=120, unique=True)

    description = models.TextField(blank=True, default='')
    icon_url = models.URLField(blank=True, default='')

    # Contrôle l'ordre d'affichage dans l'app Flutter
    # order=0 apparaît en premier, order=1 en deuxième, etc.
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'categories'
        ordering = ['order', 'name']  # Trie d'abord par order, puis alphabétiquement si égalité
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'

    def __str__(self):
        return self.name


# ============================================================
# 3. FORMATION — Cours complet
# ============================================================

class Formation(BaseModel):
    """
    Une formation est le produit principal de la plateforme.
    Elle contient des modules, qui contiennent des leçons et des quiz.
    Structure : Formation → Modules → Leçons → Quiz
    """

    class Level(models.TextChoices):
        DEBUTANT = 'debutant', 'Débutant'
        INTERMEDIAIRE = 'intermediaire', 'Intermédiaire'
        AVANCE = 'avance', 'Avancé'

    class Status(models.TextChoices):
        # Workflow de publication d'une formation
        BROUILLON = 'brouillon', 'Brouillon'    # En cours de création
        EN_REVUE = 'en_revue', 'En revue'       # Soumise pour validation
        PUBLIEE = 'publiee', 'Publiée'          # Visible dans le catalogue
        ARCHIVEE = 'archivee', 'Archivée'       # Retirée du catalogue

    # ForeignKey = relation "plusieurs-à-un" : plusieurs formations peuvent avoir le même formateur
    # on_delete=CASCADE → si le formateur est supprimé, toutes ses formations le sont aussi
    # related_name → permet d'accéder aux formations depuis un user : user.formations_creees.all()
    formateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='formations_creees',
        # limit_choices_to → dans /admin/, le menu déroulant "formateur" ne montrera
        # que les utilisateurs ayant le rôle formateur ou admin (pas les apprenants)
        limit_choices_to={'role__in': ['formateur', 'admin']},
    )

    # on_delete=SET_NULL → si la catégorie est supprimée, la formation reste mais sans catégorie
    # null=True est obligatoire quand on utilise SET_NULL (sinon Django refuse)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='formations',
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    image_url = models.URLField(blank=True, default='')

    # DecimalField pour l'argent (jamais FloatField qui cause des erreurs d'arrondi)
    # Exemple d'erreur float : 0.1 + 0.2 = 0.30000000000000004 → catastrophique pour un prix
    price = models.DecimalField(
        max_digits=10,      # 10 chiffres au total → prix max possible : 99 999 999.99
        decimal_places=2,   # 2 décimales (centimes)
        validators=[MinValueValidator(0)],  # Interdit les prix négatifs
    )
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.DEBUTANT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BROUILLON)

    # is_published permet de "dépublier" rapidement une formation sans changer son status
    # Exemple : status='publiee' mais is_published=False → cachée du catalogue
    is_published = models.BooleanField(default=False)

    # Durée totale calculée (somme des durées de toutes les leçons)
    # Ce champ est mis à jour à chaque ajout/modification de leçon
    # Stocké ici pour éviter de recalculer à chaque requête du catalogue
    total_duration_min = models.PositiveIntegerField(default=0)

    # null=True → ce champ peut être vide (avant la publication, il n'y a pas de date)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'formations'
        ordering = ['-published_at']  # '-' devant le champ = ordre décroissant (plus récent en premier)
        verbose_name = 'Formation'
        verbose_name_plural = 'Formations'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Override de save() : on intercepte la sauvegarde pour ajouter notre logique
        # Quand is_published passe à True pour la première fois,
        # on enregistre automatiquement la date de publication
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        # super().save() appelle le save() original de Django pour vraiment enregistrer en base
        super().save(*args, **kwargs)

    @property
    def modules_count(self):
        # self.modules → accès inverse via related_name='modules' défini dans Module
        return self.modules.count()

    @property
    def total_lessons(self):
        # __ (double underscore) = traversée de relation en Django
        # module__formation=self → "les leçons dont le module appartient à cette formation"
        return Lesson.objects.filter(module__formation=self).count()


# ============================================================
# 4. MODULE
# ============================================================

class Module(BaseModel):
    """
    Un module est un chapitre d'une formation.
    Les modules sont débloqués progressivement :
    → le module N est accessible seulement si le quiz du module N-1 est validé.
    La vérification de ce déverrouillage est faite dans les vues API, pas ici.
    """

    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')

    # order détermine l'ordre d'affichage ET la logique de déverrouillage progressif
    # Module order=0 → toujours accessible (premier module)
    # Module order=1 → accessible seulement si quiz du module order=0 réussi
    order = models.PositiveIntegerField(default=0)

    # Si True, ce module est visible AVANT l'achat de la formation (aperçu gratuit)
    is_preview = models.BooleanField(default=False)

    class Meta:
        db_table = 'modules'
        ordering = ['order']
        # unique_together → impossible d'avoir deux modules avec le même numéro d'ordre
        # dans la même formation. Garantit un ordre sans ambiguïté.
        unique_together = ['formation', 'order']
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'

    def __str__(self):
        return f"{self.formation.title} → {self.title}"


# ============================================================
# 5. LESSON — Leçon
# ============================================================

class Lesson(BaseModel):
    """
    Une leçon est l'unité de contenu d'un module.
    Elle peut être une vidéo, un PDF ou du texte.

    Pour chaque type, un seul champ est rempli :
    - type 'video' → video_url est rempli, les autres sont vides
    - type 'pdf'   → pdf_url est rempli, les autres sont vides
    - type 'text'  → content_text est rempli, les autres sont vides
    """

    class ContentType(models.TextChoices):
        VIDEO = 'video', 'Vidéo'
        PDF = 'pdf', 'PDF'
        TEXT = 'text', 'Texte'

    class VideoSource(models.TextChoices):
        # Flutter a besoin de savoir d'où vient la vidéo pour choisir le bon lecteur :
        # - internal → lecteur vidéo natif Flutter
        # - youtube  → widget youtube_player_flutter
        # - vimeo    → webview ou lecteur Vimeo
        INTERNAL = 'internal', 'Upload interne'
        YOUTUBE = 'youtube', 'YouTube'
        VIMEO = 'vimeo', 'Vimeo'

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)

    # Rempli uniquement si content_type = 'text'
    content_text = models.TextField(blank=True, default='')

    content_type = models.CharField(max_length=10, choices=ContentType.choices, default=ContentType.VIDEO)

    # Rempli uniquement si content_type = 'video'
    video_url = models.URLField(blank=True, default='')
    video_source = models.CharField(max_length=10, choices=VideoSource.choices, blank=True, default='')

    # Rempli uniquement si content_type = 'pdf'
    pdf_url = models.URLField(blank=True, default='')

    # Durée estimée en minutes (pour les vidéos = durée réelle, pour PDF/texte = temps de lecture estimé)
    duration_min = models.PositiveIntegerField(default=0)

    order = models.PositiveIntegerField(default=0)

    # Si True, cette leçon est accessible sans avoir acheté la formation
    is_preview = models.BooleanField(default=False)

    class Meta:
        db_table = 'lessons'
        ordering = ['order']
        unique_together = ['module', 'order']  # Pas deux leçons au même rang dans un module
        verbose_name = 'Leçon'
        verbose_name_plural = 'Leçons'

    def __str__(self):
        return f"{self.module.title} → {self.title}"


# ============================================================
# 6. QUIZ
# ============================================================

class Quiz(BaseModel):
    """
    Quiz associé à un module. Obligatoire pour passer au module suivant.

    Relation OneToOne (1:1) avec Module → un module a exactement UN quiz.
    Différence avec ForeignKey (1:N) : ForeignKey permettrait plusieurs quiz par module.
    """

    # OneToOneField → relation 1:1 stricte (un module = un quiz, un quiz = un module)
    # Accès : module.quiz → le quiz du module | quiz.module → le module du quiz
    module = models.OneToOneField(Module, on_delete=models.CASCADE, related_name='quiz')
    title = models.CharField(max_length=255)

    # Score minimum (en %) pour valider le quiz et débloquer le module suivant
    # Exemple : passing_score=70 → l'apprenant doit avoir au moins 70%
    passing_score = models.PositiveIntegerField(
        default=70,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )

    # Nombre de tentatives autorisées. 0 = illimité.
    # La vue API vérifie cette limite avant de créer une nouvelle tentative.
    max_attempts = models.PositiveIntegerField(default=3)

    class Meta:
        db_table = 'quizzes'
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quiz'

    def __str__(self):
        return f"Quiz: {self.title}"

    @property
    def questions_count(self):
        return self.questions.count()

    @property
    def total_points(self):
        # aggregate() calcule directement en SQL (plus rapide que de charger toutes les questions en Python)
        # Sum('points') → additionne les valeurs du champ 'points' de toutes les questions
        # Le "or 0" gère le cas où il n'y a aucune question (Sum retourne None, pas 0)
        return self.questions.aggregate(total=models.Sum('points'))['total'] or 0


# ============================================================
# 7. QUESTION
# ============================================================

class Question(BaseModel):
    """
    Question d'un quiz. Deux types : QCM ou Vrai/Faux.
    Chaque question a un "poids" en points (champ points).
    """

    class QuestionType(models.TextChoices):
        QCM = 'qcm', 'QCM'           # Plusieurs choix, une seule bonne réponse
        VRAI_FAUX = 'vrai_faux', 'Vrai / Faux'

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QuestionType.choices, default=QuestionType.QCM)
    order = models.PositiveIntegerField(default=0)

    # Une question peut valoir plus qu'une autre (ex: question difficile = 3 points)
    points = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        db_table = 'questions'
        ordering = ['order']
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

    def __str__(self):
        # [:60] → affiche seulement les 60 premiers caractères du texte (évite les affichages trop longs)
        return f"Q{self.order}: {self.question_text[:60]}"


# ============================================================
# 8. ANSWER_OPTION — Option de réponse
# ============================================================

class AnswerOption(BaseModel):
    """
    Une option de réponse pour une question.
    Exemple pour "Quelle est la capitale du Sénégal ?" :
    - Option A : "Dakar"      is_correct=True
    - Option B : "Abidjan"    is_correct=False
    - Option C : "Douala"     is_correct=False
    """

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.TextField()
    # is_correct=True → c'est la bonne réponse
    # Le correcteur automatique (dans QuizResponse.save()) se base sur ce champ
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'answer_options'
        ordering = ['order']
        verbose_name = "Option de réponse"
        verbose_name_plural = "Options de réponse"

    def __str__(self):
        marker = "✓" if self.is_correct else "✗"
        return f"{marker} {self.option_text[:50]}"


# ============================================================
# 9. ENROLLMENT — Inscription à une formation
# ============================================================

class Enrollment(BaseModel):
    """
    Table pivot entre User et Formation.
    Créée automatiquement après un paiement validé.

    C'est la table centrale du suivi de progression :
    - Elle lie un apprenant à une formation
    - Elle stocke le pourcentage de progression global
    - Elle détermine si l'apprenant a accès au contenu complet

    Flux de création :
    1. L'apprenant clique "Acheter"
    2. Un Payment est créé (status=en_attente)
    3. Le système de paiement confirme → Payment.status = validé
    4. L'Enrollment est créé → accès complet débloqué
    """

    class Status(models.TextChoices):
        ACTIF = 'actif', 'Actif'            # En cours de suivi
        COMPLETE = 'complete', 'Complété'   # Tout terminé → certificat disponible
        ABANDONNE = 'abandonne', 'Abandonné'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIF)

    # Progression de 0 à 100 (%). Recalculé automatiquement via update_progress()
    progress_percent = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)])
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'enrollments'
        # unique_together → un apprenant ne peut s'inscrire qu'UNE SEULE FOIS à une formation
        unique_together = ['user', 'formation']
        verbose_name = 'Inscription'
        verbose_name_plural = 'Inscriptions'

    def __str__(self):
        return f"{self.user.email} → {self.formation.title} ({self.progress_percent}%)"

    def update_progress(self):
        """
        Recalcule le pourcentage de progression de l'apprenant dans cette formation.

        Appelée automatiquement quand :
        - Une leçon est marquée comme terminée (via LessonProgress.mark_completed())
        - Un quiz est réussi (via QuizAttempt.calculate_score())

        Logique :
        progress = (leçons terminées / total leçons) × 100
        Si 100% ET tous les quiz validés → statut = COMPLETE
        """
        # Compte le total des leçons de cette formation
        total_lessons = Lesson.objects.filter(module__formation=self.formation).count()

        # Cas où la formation n'a pas encore de leçons (évite une division par zéro)
        if total_lessons == 0:
            return

        # Compte les leçons que CET apprenant a terminées dans CETTE formation
        completed_lessons = LessonProgress.objects.filter(
            user=self.user,
            lesson__module__formation=self.formation,  # Traversée : leçon → module → formation
            is_completed=True,
        ).count()

        # int() arrondit à l'entier inférieur (ex: 66.6% → 66%)
        self.progress_percent = int((completed_lessons / total_lessons) * 100)

        if self.progress_percent == 100:
            # 100% des leçons ne suffit pas pour obtenir le certificat.
            # Il faut AUSSI que tous les quiz soient réussis (règle métier critique).
            all_quizzes = Quiz.objects.filter(module__formation=self.formation)

            # all() retourne True seulement si CHAQUE élément du générateur est True
            # Si un seul quiz n'est pas validé → all_passed = False
            all_passed = all(
                QuizAttempt.objects.filter(user=self.user, quiz=quiz, is_passed=True).exists()
                for quiz in all_quizzes
            )

            if all_passed:
                self.status = self.Status.COMPLETE
                self.completed_at = timezone.now()

        self.save()


# ============================================================
# 10. PAYMENT — Paiement
# ============================================================

class Payment(BaseModel):
    """
    Enregistrement de chaque tentative de paiement.
    Un paiement validé déclenche la création de l'Enrollment.

    IMPORTANT : ne jamais supprimer un paiement, même échoué.
    C'est un journal comptable (audit trail) qui peut servir
    en cas de litige avec un apprenant.

    Pourquoi séparer Payment et Enrollment ?
    → Un paiement peut échouer (pas d'enrollment créé)
    → Un remboursement peut désactiver l'enrollment sans supprimer la trace du paiement
    """

    class PaymentMethod(models.TextChoices):
        MOBILE_MONEY = 'mobile_money', 'Mobile Money'  # MTN MoMo, Orange Money, etc.
        CARTE = 'carte', 'Carte bancaire'
        STRIPE = 'stripe', 'Stripe'
        PAYPAL = 'paypal', 'PayPal'

    class Status(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'  # Paiement initié, pas encore confirmé
        VALIDE = 'valide', 'Validé'              # Paiement confirmé → enrollment créé
        ECHOUE = 'echoue', 'Échoué'             # Paiement refusé
        REMBOURSE = 'rembourse', 'Remboursé'    # Remboursement effectué

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='payments')

    # SET_NULL → si l'enrollment est supprimé, le paiement reste (preuve de transaction conservée)
    # null=True car le Payment est créé AVANT l'Enrollment (on crée d'abord le paiement en attente)
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment',
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Code ISO 4217 sur 3 caractères : 'XAF' = Franc CFA (CEMAC), 'EUR' = Euro, 'USD' = Dollar
    currency = models.CharField(max_length=3, default='XAF')

    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EN_ATTENTE)

    # Référence unique fournie par la plateforme de paiement (Stripe, MTN MoMo, etc.)
    # unique=True → impossible d'enregistrer deux fois la même transaction (protection anti-doublon)
    # Sert aussi à vérifier un paiement auprès de la plateforme en cas de litige
    transaction_ref = models.CharField(max_length=255, unique=True)

    # paid_at ≠ created_at :
    # created_at = quand le Payment est créé en base (statut = en_attente)
    # paid_at    = quand la confirmation de paiement arrive (statut = validé)
    # L'écart peut être de quelques secondes à plusieurs minutes
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'

    def __str__(self):
        return f"{self.user.email} → {self.amount} {self.currency} ({self.status})"


# ============================================================
# 11. LESSON_PROGRESS — Progression par leçon
# ============================================================

class LessonProgress(BaseModel):
    """
    Suit la progression d'un apprenant sur chaque leçon.
    Une ligne est créée la première fois que l'apprenant ouvre une leçon.

    Fonctionnalité "reprise automatique des vidéos" :
    → Flutter envoie la position de lecture toutes les 10 secondes
    → Quand l'apprenant revient, Flutter lit video_position_sec et reprend à cet endroit
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')

    is_completed = models.BooleanField(default=False)

    # Position en secondes dans la vidéo (ignoré pour les leçons PDF ou texte)
    video_position_sec = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lesson_progress'
        # unique_together → une seule ligne par couple (apprenant, leçon)
        # Si l'apprenant revient sur une leçon, on MET À JOUR cette ligne (pas de doublon)
        unique_together = ['user', 'lesson']
        verbose_name = 'Progression leçon'
        verbose_name_plural = 'Progressions leçons'

    def __str__(self):
        status = "✓" if self.is_completed else "…"
        return f"{status} {self.user.email} → {self.lesson.title}"

    def mark_completed(self):
        """
        Marque cette leçon comme terminée et déclenche une cascade de mises à jour :

        1. Cette leçon → is_completed = True
        2. L'enrollment parent → progress_percent recalculé
        3. Si 100% + tous quiz validés → enrollment.status = COMPLETE → certificat disponible

        Appelée quand l'apprenant clique "Leçon terminée" dans Flutter.
        Flutter envoie : POST /api/lessons/{id}/complete/
        La vue appelle cette méthode.
        """
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()

        # Remonte vers l'enrollment pour recalculer la progression globale
        # self.lesson.module.formation → traverse 3 niveaux : leçon → module → formation
        enrollment = Enrollment.objects.filter(
            user=self.user,
            formation=self.lesson.module.formation,
        ).first()  # .first() retourne None si pas trouvé (évite une exception)

        if enrollment:
            enrollment.update_progress()


# ============================================================
# 12. QUIZ_ATTEMPT — Tentative de quiz
# ============================================================

class QuizAttempt(BaseModel):
    """
    Enregistre chaque tentative d'un apprenant sur un quiz.

    Flux complet d'un quiz :
    1. Apprenant ouvre le quiz     → Flutter crée un QuizAttempt (POST /api/quiz/{id}/start/)
    2. Apprenant répond            → Flutter crée des QuizResponse pour chaque réponse
    3. Apprenant valide            → Flutter soumet (POST /api/attempts/{id}/submit/)
    4. calculate_score() est appelé → score calculé, is_passed déterminé
    5. Si réussi                   → progression mise à jour, module suivant débloqué
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')

    # Score de 0 à 100 (%). Calculé par calculate_score() à la soumission.
    score = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)])

    # True si score >= quiz.passing_score
    is_passed = models.BooleanField(default=False)

    # Numéro de la tentative (1ère, 2ème, 3ème...). Vérifié contre quiz.max_attempts.
    attempt_number = models.PositiveIntegerField(default=1)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'quiz_attempts'
        ordering = ['-started_at']
        verbose_name = 'Tentative de quiz'
        verbose_name_plural = 'Tentatives de quiz'

    def __str__(self):
        status = "✓" if self.is_passed else "✗"
        return f"{status} {self.user.email} → {self.quiz.title} ({self.score}%)"

    def calculate_score(self):
        """
        Calcule le score de cette tentative après soumission.

        Logique de calcul :
        score = (points obtenus / total points du quiz) × 100

        Exemple :
        - Quiz avec Q1 (2pts), Q2 (3pts), Q3 (5pts) = 10 pts au total
        - Apprenant réussit Q1 et Q3 → 2 + 5 = 7 pts
        - Score = (7/10) × 100 = 70%
        - Si passing_score=70 → is_passed = True
        """
        total_points = self.quiz.total_points

        # Cas où le quiz n'a pas encore de questions
        if total_points == 0:
            return

        # self.responses → toutes les réponses de cette tentative (via related_name='responses')
        # filter(is_correct=True) → garde seulement les bonnes réponses
        # Générateur Python : calcule la somme des points des questions bien répondues
        earned_points = sum(
            response.question.points
            for response in self.responses.filter(is_correct=True)
        )

        self.score = int((earned_points / total_points) * 100)
        self.is_passed = self.score >= self.quiz.passing_score
        self.completed_at = timezone.now()
        self.save()

        # Si réussi → recalcule la progression de l'enrollment
        # (permet au module suivant de se débloquer)
        if self.is_passed:
            enrollment = Enrollment.objects.filter(
                user=self.user,
                formation=self.quiz.module.formation,
            ).first()
            if enrollment:
                enrollment.update_progress()


# ============================================================
# 13. QUIZ_RESPONSE — Réponse individuelle à une question
# ============================================================

class QuizResponse(BaseModel):
    """
    Enregistre la réponse d'un apprenant à UNE question lors d'UNE tentative.
    La correction est automatique et faite côté serveur (pas côté Flutter).

    unique_together ['attempt', 'question'] → impossible de répondre deux fois
    à la même question dans la même tentative (protection contre les double-clics).
    """

    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    selected_option = models.ForeignKey(AnswerOption, on_delete=models.CASCADE, related_name='selections')

    # is_correct est calculé AUTOMATIQUEMENT dans save() — ne pas le définir manuellement
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = 'quiz_responses'
        unique_together = ['attempt', 'question']
        verbose_name = 'Réponse quiz'
        verbose_name_plural = 'Réponses quiz'

    def __str__(self):
        marker = "✓" if self.is_correct else "✗"
        return f"{marker} Q{self.question.order}"

    def save(self, *args, **kwargs):
        # CORRECTION AUTOMATIQUE côté serveur :
        # On recalcule is_correct à partir de selected_option.is_correct
        # Cela empêche un utilisateur malveillant d'envoyer is_correct=True via l'API
        # pour se donner artificiellement une bonne réponse.
        self.is_correct = self.selected_option.is_correct
        super().save(*args, **kwargs)


# ============================================================
# 14. CERTIFICATE — Certificat de fin de formation
# ============================================================

class Certificate(BaseModel):
    """
    Certificat délivré quand l'apprenant a :
    - Terminé toutes les leçons (progress_percent = 100%)
    - Validé tous les quiz (is_passed = True pour chaque quiz)

    Le certificat est vérifiable publiquement (sans connexion) via :
    - Son code unique : EFG-A1B2C3D4
    - Son lien public : /verify/EFG-A1B2C3D4/

    Cela permet aux employeurs de vérifier l'authenticité d'un certificat
    présenté par un candidat.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='certificates')

    # Code unique au format "EFG-XXXXXXXX". Généré automatiquement dans save() si vide.
    # unique=True → un code = un certificat précis dans toute la base
    certificate_code = models.CharField(max_length=50, unique=True)

    # URL publique de vérification. Générée automatiquement dans save() si vide.
    verification_url = models.URLField(blank=True, default='')

    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'certificates'
        # Un apprenant ne peut obtenir qu'UN SEUL certificat par formation
        unique_together = ['user', 'formation']
        verbose_name = 'Certificat'
        verbose_name_plural = 'Certificats'

    def __str__(self):
        return f"Certificat {self.certificate_code} → {self.user.email}"

    def save(self, *args, **kwargs):
        # Génère le code et l'URL automatiquement à la première création
        if not self.certificate_code:
            # uuid4().hex → 32 caractères hexadécimaux aléatoires (ex: "a1b2c3d4e5f6...")
            # [:8] → on garde seulement les 8 premiers
            # .upper() → majuscules pour la lisibilité (ex: "A1B2C3D4")
            # Résultat final : "EFG-A1B2C3D4"
            self.certificate_code = f"EFG-{uuid.uuid4().hex[:8].upper()}"
        if not self.verification_url:
            self.verification_url = f"/verify/{self.certificate_code}/"
        super().save(*args, **kwargs)
