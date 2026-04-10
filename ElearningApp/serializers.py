"""
EFG E-Learning Platform — Serializers
=======================================
Un serializer est un "traducteur" entre Python et JSON.

RÔLE PRINCIPAL :
- Côté SORTIE  : convertit un objet Python (issu de la base de données) en JSON
                 pour l'envoyer à Flutter
- Côté ENTRÉE  : reçoit du JSON envoyé par Flutter, le valide,
                 puis crée ou modifie un objet en base de données

ANALOGIE :
Pense au serializer comme un formulaire intelligent :
- Il sait quels champs afficher (read) et lesquels accepter (write)
- Il valide les données avant de les enregistrer (comme un formulaire qui refuse
  un email invalide ou un mot de passe trop court)
- Il peut transformer les données (ex: chiffrer un mot de passe avant de le stocker)

ORGANISATION DE CE FICHIER :
1. Authentification  → inscription, profil utilisateur
2. Catalogue         → catégories, formations (liste et détail), modules, leçons
3. Quiz              → questions, options, quiz complet
4. Progression       → inscriptions, avancement par leçon
5. Quiz interactif   → tentatives, réponses
6. Certificat        → génération et vérification
7. Paiement          → création et suivi
"""

from rest_framework import serializers
# serializers est le module principal de Django REST Framework (DRF)
# Il fournit les classes de base pour créer nos serializers

from django.contrib.auth.password_validation import validate_password
# validate_password → vérifie que le mot de passe respecte les règles définies dans settings.py
# (longueur minimale, pas trop commun, etc.)

from .models import (
    User, Category, Formation, Module, Lesson,
    Quiz, Question, AnswerOption,
    Enrollment, Payment, LessonProgress,
    QuizAttempt, QuizResponse, Certificate,
)
# On importe tous nos modèles depuis models.py (le "." signifie "dans le même dossier")


# ================================================================
# 1. AUTHENTIFICATION
# ================================================================

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'inscription d'un nouvel utilisateur.

    Utilisé par : POST /api/auth/register/

    Ce serializer fait 3 choses spéciales :
    1. Demande le mot de passe EN DOUBLE (password + password_confirm) pour éviter les fautes de frappe
    2. Valide la force du mot de passe (règles de settings.py)
    3. Chiffre le mot de passe avant de le stocker (jamais en clair)
    """

    # write_only=True → ce champ est accepté en entrée mais JAMAIS renvoyé en réponse
    # (on ne veut pas que le mot de passe apparaisse dans la réponse JSON)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],  # Applique les règles de complexité du mot de passe
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        # ModelSerializer lit automatiquement les champs depuis le modèle User
        model = User
        # On liste exactement les champs que Flutter doit envoyer lors de l'inscription
        fields = ['email', 'first_name', 'last_name', 'password', 'password_confirm']

    def validate(self, data):
        """
        validate() est appelé automatiquement par DRF après la validation de chaque champ.
        Ici on vérifie que les deux mots de passe sont identiques.

        data = dictionnaire contenant toutes les valeurs envoyées par Flutter
        """
        if data['password'] != data['password_confirm']:
            # ValidationError interrompt la création et renvoie l'erreur en JSON à Flutter
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return data

    def create(self, validated_data):
        """
        create() est appelé quand les données sont valides, pour créer l'utilisateur en base.
        validated_data = le dictionnaire data après validation (données propres et sûres)
        """
        # On retire password_confirm car ce champ n'existe pas dans le modèle User
        validated_data.pop('password_confirm')

        # create_user() de notre UserManager chiffre automatiquement le mot de passe
        user = User.objects.create_user(**validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer pour afficher et modifier le profil d'un utilisateur connecté.

    Utilisé par :
    - GET  /api/auth/profile/  → affiche le profil
    - PATCH /api/auth/profile/ → modifie le profil (prénom, bio, avatar...)
    """

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'phone', 'bio', 'avatar_url', 'role',
            'created_at',
        ]
        # read_only_fields → ces champs sont visibles mais ne peuvent PAS être modifiés via ce serializer
        # L'email et le rôle ne se changent pas depuis le profil standard
        read_only_fields = ['id', 'email', 'role', 'created_at']


class PublicUserSerializer(serializers.ModelSerializer):
    """
    Version allégée du profil — utilisée pour afficher l'auteur d'une formation.
    Ne révèle que les informations publiques (pas l'email, pas le téléphone).
    """

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'avatar_url', 'bio']


# ================================================================
# 2. CATALOGUE — Catégories et Formations
# ================================================================

class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer pour les catégories de formations.
    Utilisé pour afficher le menu des catégories dans Flutter.
    """

    # SerializerMethodField → champ calculé dynamiquement (pas directement dans le modèle)
    # La valeur est retournée par la méthode get_formations_count() définie plus bas
    formations_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon_url', 'order', 'formations_count']

    def get_formations_count(self, obj):
        """
        Compte les formations publiées dans cette catégorie.
        obj = l'objet Category en cours de sérialisation
        """
        # filter(is_published=True) → on ne compte que les formations visibles
        return obj.formations.filter(is_published=True).count()


class FormationListSerializer(serializers.ModelSerializer):
    """
    Serializer LÉGER pour le catalogue (liste de formations).

    POURQUOI DEUX SERIALIZERS POUR FORMATION ?
    → Le catalogue charge potentiellement des dizaines de formations.
      On ne veut pas renvoyer tous les modules et leçons de chaque formation
      (ce serait lent et inutile pour une liste).
    → Ce serializer ne renvoie que les infos essentielles : titre, image, prix...
    → Le détail complet (avec les modules) est géré par FormationDetailSerializer.
    """

    # Champs imbriqués (nested) : au lieu d'afficher l'id du formateur,
    # on affiche directement son prénom/nom/avatar
    formateur = PublicUserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    # Ces champs n'existent pas directement dans la table formations,
    # mais sont des @property définies dans le modèle Formation
    modules_count = serializers.ReadOnlyField()   # = Formation.modules_count
    total_lessons = serializers.ReadOnlyField()   # = Formation.total_lessons

    class Meta:
        model = Formation
        fields = [
            'id', 'title', 'description', 'image_url',
            'price', 'level', 'status',
            'formateur', 'category',
            'total_duration_min', 'modules_count', 'total_lessons',
            'published_at',
        ]


class LessonSerializer(serializers.ModelSerializer):
    """
    Serializer pour une leçon individuelle.

    Utilisé dans deux contextes :
    - Imbriqué dans ModuleSerializer (affichage du programme)
    - Seul pour accéder au contenu d'une leçon spécifique
    """

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'content_type',
            'content_text', 'video_url', 'video_source', 'pdf_url',
            'duration_min', 'order', 'is_preview',
        ]


class ModuleSerializer(serializers.ModelSerializer):
    """
    Serializer pour un module avec ses leçons imbriquées.
    Utilisé dans le détail d'une formation pour afficher le programme complet.
    """

    # many=True → une liste de leçons (pas une seule)
    # read_only=True → ces leçons sont affichées mais ne peuvent pas être créées via ce serializer
    lessons = LessonSerializer(many=True, read_only=True)

    # Champ calculé : nombre de leçons dans ce module
    lessons_count = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'is_preview', 'lessons_count', 'lessons']

    def get_lessons_count(self, obj):
        return obj.lessons.count()


class FormationDetailSerializer(serializers.ModelSerializer):
    """
    Serializer COMPLET pour le détail d'une formation.
    Inclut les modules et leurs leçons (programme complet).

    Utilisé par : GET /api/formations/{id}/
    """

    formateur = PublicUserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    # Programme complet : modules avec leurs leçons imbriquées
    modules = ModuleSerializer(many=True, read_only=True)

    modules_count = serializers.ReadOnlyField()
    total_lessons = serializers.ReadOnlyField()

    # is_enrolled indique si L'UTILISATEUR CONNECTÉ est inscrit à cette formation
    # Utile pour Flutter : afficher "Continuer" ou "Acheter" selon l'état
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Formation
        fields = [
            'id', 'title', 'description', 'image_url',
            'price', 'level', 'status',
            'formateur', 'category',
            'total_duration_min', 'modules_count', 'total_lessons',
            'published_at', 'is_enrolled', 'modules',
        ]

    def get_is_enrolled(self, obj):
        """
        Vérifie si l'utilisateur actuellement connecté est inscrit à cette formation.

        self.context['request'] → la requête HTTP entrante (contient l'utilisateur connecté)
        """
        request = self.context.get('request')
        # Si pas de requête ou utilisateur non connecté → False
        if not request or not request.user.is_authenticated:
            return False
        return Enrollment.objects.filter(user=request.user, formation=obj).exists()


class FormationWriteSerializer(serializers.ModelSerializer):
    """
    Serializer pour CRÉER ou MODIFIER une formation (usage formateur/admin).
    Séparé de FormationDetailSerializer pour contrôler exactement
    quels champs un formateur peut modifier.

    Utilisé par :
    - POST  /api/formations/        → créer une formation
    - PATCH /api/formations/{id}/   → modifier une formation
    """

    class Meta:
        model = Formation
        fields = [
            'title', 'description', 'image_url',
            'price', 'level', 'status', 'is_published',
            'category', 'total_duration_min',
        ]

    def validate_price(self, value):
        """
        validate_<nom_du_champ>() est appelé automatiquement par DRF
        pour valider un champ spécifique.
        Ici on vérifie que le prix est positif ou nul.
        """
        if value < 0:
            raise serializers.ValidationError("Le prix ne peut pas être négatif.")
        return value


# ================================================================
# 3. QUIZ
# ================================================================

class AnswerOptionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les options de réponse d'une question.

    ATTENTION SÉCURITÉ :
    Le champ is_correct (qui indique la bonne réponse) est géré différemment
    selon le contexte :
    - Pour l'APPRENANT → is_correct est caché (sinon il voit les réponses !)
    - Pour l'ADMIN/FORMATEUR → is_correct est visible pour créer/modifier le quiz

    Cette version est la version PUBLIQUE (sans is_correct).
    La version admin est AnswerOptionAdminSerializer définie plus bas.
    """

    class Meta:
        model = AnswerOption
        # is_correct est intentionnellement ABSENT pour ne pas révéler les réponses
        fields = ['id', 'option_text', 'order']


class AnswerOptionAdminSerializer(serializers.ModelSerializer):
    """
    Version admin/formateur : inclut is_correct pour créer et corriger les quiz.
    Ne jamais exposer cet endpoint aux apprenants.
    """

    class Meta:
        model = AnswerOption
        fields = ['id', 'option_text', 'is_correct', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    """
    Serializer pour afficher une question avec ses options de réponse.
    Utilisé côté APPRENANT (les bonnes réponses sont cachées).
    """

    # Affiche les options sans révéler is_correct
    options = AnswerOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'order', 'points', 'options']


class QuestionAdminSerializer(serializers.ModelSerializer):
    """
    Version admin/formateur : affiche les options avec les bonnes réponses.
    """

    options = AnswerOptionAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'order', 'points', 'options']


class QuizSerializer(serializers.ModelSerializer):
    """
    Serializer pour afficher un quiz avec ses questions (côté apprenant).
    Les bonnes réponses sont cachées.
    """

    questions = QuestionSerializer(many=True, read_only=True)
    questions_count = serializers.ReadOnlyField()

    class Meta:
        model = Quiz
        # passing_score et max_attempts sont visibles (l'apprenant doit savoir à quoi s'attendre)
        fields = ['id', 'title', 'passing_score', 'max_attempts', 'questions_count', 'questions']


class QuizAdminSerializer(serializers.ModelSerializer):
    """
    Version admin/formateur : inclut les bonnes réponses pour créer/modifier le quiz.
    """

    questions = QuestionAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'title', 'passing_score', 'max_attempts', 'questions']


# ================================================================
# 4. PROGRESSION — Inscriptions et avancement
# ================================================================

class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer pour les inscriptions d'un apprenant.

    Utilisé par :
    - GET /api/enrollments/           → liste des formations suivies par l'apprenant
    - GET /api/enrollments/{id}/      → détail d'une inscription avec progression
    """

    # Affiche les informations de la formation (titre, image...) au lieu de juste son id
    formation = FormationListSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id', 'formation', 'enrolled_at',
            'status', 'progress_percent', 'completed_at',
        ]
        # Ces champs sont calculés automatiquement — l'apprenant ne peut pas les forcer
        read_only_fields = ['enrolled_at', 'status', 'progress_percent', 'completed_at']


class LessonProgressSerializer(serializers.ModelSerializer):
    """
    Serializer pour suivre la progression sur une leçon spécifique.

    Utilisé par :
    - GET   /api/lessons/{id}/progress/    → récupère la position de lecture et l'état
    - PATCH /api/lessons/{id}/progress/    → met à jour la position vidéo (toutes les 10s)
    - POST  /api/lessons/{id}/complete/    → marque la leçon comme terminée
    """

    class Meta:
        model = LessonProgress
        fields = [
            'id', 'lesson', 'is_completed',
            'video_position_sec', 'started_at', 'completed_at',
        ]
        # Ces champs sont gérés automatiquement côté serveur
        read_only_fields = ['lesson', 'is_completed', 'started_at', 'completed_at']
        # Seul video_position_sec est modifiable par Flutter (reprise automatique)


# ================================================================
# 5. QUIZ INTERACTIF — Tentatives et réponses
# ================================================================

class QuizResponseSerializer(serializers.ModelSerializer):
    """
    Serializer pour soumettre une réponse à une question lors d'une tentative.

    Flux :
    Flutter envoie → { "question": "uuid...", "selected_option": "uuid..." }
    Le serveur calcule automatiquement is_correct (voir QuizResponse.save() dans models.py)
    """

    class Meta:
        model = QuizResponse
        fields = ['id', 'question', 'selected_option', 'is_correct']
        # is_correct est calculé par le serveur dans QuizResponse.save()
        # Flutter ne doit pas pouvoir l'envoyer lui-même (sécurité anti-triche)
        read_only_fields = ['is_correct']

    def validate(self, data):
        """
        Vérifie que l'option de réponse appartient bien à la question posée.
        Sans cette vérification, un utilisateur pourrait envoyer l'id d'une option
        d'une autre question → résultat incohérent en base.
        """
        question = data.get('question')
        selected_option = data.get('selected_option')

        if selected_option.question_id != question.id:
            raise serializers.ValidationError(
                "L'option sélectionnée n'appartient pas à cette question."
            )
        return data


class QuizAttemptSerializer(serializers.ModelSerializer):
    """
    Serializer pour afficher le résultat d'une tentative de quiz.

    Utilisé par :
    - GET  /api/attempts/{id}/         → résultat d'une tentative (score, réponses)
    - POST /api/quiz/{id}/start/       → démarrer une nouvelle tentative
    - POST /api/attempts/{id}/submit/  → soumettre et calculer le score
    """

    # Affiche les réponses soumises avec leur correction
    responses = QuizResponseSerializer(many=True, read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'quiz', 'score', 'is_passed',
            'attempt_number', 'started_at', 'completed_at',
            'responses',
        ]
        # score, is_passed et completed_at sont calculés par calculate_score()
        # L'apprenant ne peut pas les définir manuellement
        read_only_fields = ['score', 'is_passed', 'attempt_number', 'started_at', 'completed_at']

    def validate(self, data):
        """
        Vérifie que l'apprenant n'a pas dépassé le nombre maximum de tentatives autorisées.

        self.context['request'].user → l'apprenant connecté
        data['quiz'] → le quiz visé
        """
        request = self.context.get('request')
        quiz = data.get('quiz')

        if request and quiz:
            # Compte les tentatives déjà effectuées par cet apprenant sur ce quiz
            attempts_count = QuizAttempt.objects.filter(
                user=request.user,
                quiz=quiz,
            ).count()

            # quiz.max_attempts == 0 signifie tentatives illimitées (on ne bloque pas)
            if quiz.max_attempts > 0 and attempts_count >= quiz.max_attempts:
                raise serializers.ValidationError(
                    f"Nombre maximum de tentatives atteint ({quiz.max_attempts})."
                )
        return data


# ================================================================
# 6. CERTIFICAT
# ================================================================

class CertificateSerializer(serializers.ModelSerializer):
    """
    Serializer pour afficher un certificat obtenu.

    Utilisé par :
    - GET /api/certificates/              → liste des certificats de l'apprenant
    - GET /api/certificates/{id}/         → détail d'un certificat
    - GET /api/verify/{code}/             → vérification publique (sans connexion)
    """

    # Affiche le nom complet de l'apprenant et le titre de la formation
    # au lieu de leurs ids (plus lisible pour Flutter et pour le PDF du certificat)
    user = PublicUserSerializer(read_only=True)
    formation_title = serializers.CharField(source='formation.title', read_only=True)
    # source='formation.title' → Django va chercher l'attribut title de la formation liée

    class Meta:
        model = Certificate
        fields = [
            'id', 'user', 'formation_title',
            'certificate_code', 'verification_url', 'issued_at',
        ]
        # Tous les champs sont en lecture seule : un certificat ne se modifie pas
        read_only_fields = ['certificate_code', 'verification_url', 'issued_at']


# ================================================================
# 7. PAIEMENT
# ================================================================

class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer et consulter un paiement.

    Flux de paiement :
    1. Flutter envoie : POST /api/payments/ avec { formation, payment_method }
    2. Le serveur crée un Payment (status=en_attente) et génère un transaction_ref
    3. Flutter redirige vers la passerelle de paiement (Mobile Money, Stripe...)
    4. La passerelle envoie une confirmation au serveur (webhook)
    5. Le serveur met à jour status=validé et crée l'Enrollment
    """

    # Affiche le titre de la formation au lieu de son id
    formation_title = serializers.CharField(source='formation.title', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'formation', 'formation_title',
            'amount', 'currency', 'payment_method',
            'status', 'transaction_ref', 'paid_at', 'created_at',
        ]
        # Ces champs sont gérés par le serveur, pas par Flutter
        # amount → toujours copié depuis formation.price dans perform_create() (sécurité : Flutter ne peut pas manipuler le prix)
        read_only_fields = [
            'amount', 'status', 'transaction_ref', 'paid_at', 'created_at', 'formation_title'
        ]

    def validate(self, data):
        """
        Vérifie que l'apprenant n'est pas déjà inscrit à cette formation.
        (On ne veut pas qu'il paye deux fois pour la même formation.)
        """
        request = self.context.get('request')
        formation = data.get('formation')

        if request and formation:
            already_enrolled = Enrollment.objects.filter(
                user=request.user,
                formation=formation,
            ).exists()

            if already_enrolled:
                raise serializers.ValidationError(
                    "Vous êtes déjà inscrit à cette formation."
                )
        return data


# ================================================================
# 8. DASHBOARD ADMINISTRATEUR
# ================================================================

class AdminFormationSerializer(serializers.ModelSerializer):
    """
    Serializer pour la gestion des formations côté administrateur.
    Permet de voir et modifier tous les champs, y compris le statut de publication.
    """

    formateur = PublicUserSerializer(read_only=True)
    # formateur_id → champ d'écriture séparé pour assigner un formateur par son id
    # write_only=True → accepté en entrée mais non renvoyé dans la réponse (on renvoie formateur à la place)
    formateur_id = serializers.UUIDField(write_only=True, required=False)

    modules_count = serializers.ReadOnlyField()
    total_lessons = serializers.ReadOnlyField()
    enrollments_count = serializers.SerializerMethodField()

    class Meta:
        model = Formation
        fields = [
            'id', 'title', 'description', 'image_url',
            'price', 'level', 'status', 'is_published',
            'formateur', 'formateur_id', 'category',
            'total_duration_min', 'modules_count', 'total_lessons',
            'enrollments_count', 'published_at', 'created_at',
        ]
        read_only_fields = ['published_at', 'created_at']

    def get_enrollments_count(self, obj):
        """Nombre total d'apprenants inscrits à cette formation."""
        return obj.enrollments.count()

    def update(self, instance, validated_data):
        """
        update() est appelé lors d'un PATCH ou PUT pour modifier une formation existante.
        instance = l'objet Formation existant en base
        validated_data = les nouvelles valeurs après validation
        """
        # Si formateur_id est fourni, on récupère l'objet User correspondant
        formateur_id = validated_data.pop('formateur_id', None)
        if formateur_id:
            try:
                formateur = User.objects.get(id=formateur_id, role__in=['formateur', 'admin'])
                instance.formateur = formateur
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"formateur_id": "Formateur introuvable ou rôle invalide."}
                )

        # Met à jour tous les autres champs avec les nouvelles valeurs
        # setattr(obj, 'champ', valeur) = equivalent de obj.champ = valeur
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Serializer pour la gestion des utilisateurs côté administrateur.
    Permet de voir tous les champs et de modifier le rôle d'un utilisateur.
    """

    enrollments_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'phone', 'role', 'is_active',
            'auth_provider', 'created_at',
            'enrollments_count',
        ]
        read_only_fields = ['email', 'auth_provider', 'created_at']

    def get_enrollments_count(self, obj):
        """Nombre de formations suivies par cet utilisateur."""
        return obj.enrollments.count()


class AdminStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques du dashboard administrateur.

    Ce serializer est différent des autres : il n'est pas lié à un modèle (pas de ModelSerializer).
    Il sert uniquement à structurer des données calculées manuellement dans la vue.

    Utilisé par : GET /api/admin/stats/
    """

    # Ces champs sont en lecture seule (calculés côté serveur)
    total_users = serializers.IntegerField(read_only=True)
    total_apprenants = serializers.IntegerField(read_only=True)
    total_formateurs = serializers.IntegerField(read_only=True)
    total_formations = serializers.IntegerField(read_only=True)
    total_enrollments = serializers.IntegerField(read_only=True)
    total_certificates = serializers.IntegerField(read_only=True)
    average_progress = serializers.FloatField(read_only=True)
    # Taux de réussite global = (inscriptions complétées / total inscriptions) × 100
    completion_rate = serializers.FloatField(read_only=True)
