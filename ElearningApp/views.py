"""
EFG E-Learning Platform — Views
================================
Une vue (view) est le "gestionnaire" d'une requête HTTP.

RÔLE PRINCIPAL :
1. Reçoit la requête HTTP (GET, POST, PATCH...) envoyée par Flutter
2. Vérifie les permissions (est-ce que tu as le droit ?)
3. Récupère ou modifie les données en base de données
4. Sérialise les données via les serializers (Python → JSON)
5. Renvoie la réponse JSON à Flutter

ANALOGIE :
Pense à une vue comme à un guichet de banque :
- Le guichet vérifie d'abord ton identité (permission)
- Il récupère tes informations dans le système (base de données)
- Il te les présente dans un format lisible (JSON)

ORGANISATION DE CE FICHIER :
1. Permissions personnalisées   → qui peut faire quoi
2. Authentification             → inscription, profil
3. Catalogue                    → catégories, formations
4. Leçons et progression        → contenu, avancement
5. Inscriptions                 → formations suivies
6. Quiz                         → questions, tentatives, résultats
7. Certificats                  → obtention, vérification publique
8. Paiements                    → initiation, confirmation
9. Administration               → stats et gestion (admin uniquement)
"""

import uuid

from django.db.models import Q, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    User, Category, Formation, Module, Lesson,
    Quiz, Enrollment, LessonProgress,
    QuizAttempt, QuizResponse, Certificate, Payment,
)
from .serializers import (
    RegisterSerializer, UserProfileSerializer,
    CategorySerializer,
    FormationListSerializer, FormationDetailSerializer, FormationWriteSerializer,
    LessonSerializer,
    LessonProgressSerializer,
    EnrollmentSerializer,
    QuizSerializer, QuizAttemptSerializer, QuizResponseSerializer,
    CertificateSerializer,
    PaymentSerializer,
    AdminFormationSerializer, AdminUserSerializer, AdminStatsSerializer,
)


# ================================================================
# 1. PERMISSIONS PERSONNALISÉES
# ================================================================

class IsFormateur(BasePermission):
    """
    Permission réservée aux formateurs et aux admins.

    Pourquoi les deux ?
    → Selon la vision produit, un admin peut aussi créer des formations.
    → user.is_formateur retourne True pour role='formateur' ET role='admin'.

    Utilisée sur : création et modification de formations.
    """

    def has_permission(self, request, view):
        # has_permission est appelé AVANT de traiter la requête
        # On vérifie 3 conditions enchaînées :
        # 1. L'utilisateur existe (pas une requête anonyme)
        # 2. L'utilisateur est connecté (a un token valide)
        # 3. L'utilisateur a le bon rôle
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_formateur
        )


class IsAdmin(BasePermission):
    """
    Permission réservée aux administrateurs uniquement.
    Utilisée sur tous les endpoints /api/admin/...
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_admin
        )


# ================================================================
# 2. FONCTION UTILITAIRE — Déverrouillage progressif des modules
# ================================================================

def _can_access_module(user, module):
    """
    Vérifie si un utilisateur connecté peut accéder à un module donné.

    RÈGLES DE DÉVERROUILLAGE PROGRESSIF (vision produit) :
    - Aperçu (is_preview=True)   → accessible à tous, même sans compte
    - Premier module (order=0)   → accessible si inscrit à la formation
    - Autres modules             → accessible seulement si le quiz du
                                   module précédent a été RÉUSSI

    EXEMPLE :
    Formation avec 3 modules (A, B, C) :
    - Module A (order=0) → accessible immédiatement après inscription
    - Module B (order=1) → accessible si quiz du module A réussi
    - Module C (order=2) → accessible si quiz du module B réussi

    Arguments :
    - user   : l'objet User connecté
    - module : l'objet Module dont on vérifie l'accès

    Retourne : True si accessible, False sinon
    """

    # Un module d'aperçu est accessible sans restriction (vitrine de la formation)
    if module.is_preview:
        return True

    # Vérifie que l'utilisateur est inscrit à la formation parente
    enrollment = Enrollment.objects.filter(
        user=user,
        formation=module.formation,
    ).first()  # .first() retourne None si aucun résultat (évite une exception)

    if not enrollment:
        return False  # Pas inscrit → pas d'accès

    # Le module d'ordre 0 est toujours accessible si l'utilisateur est inscrit
    if module.order == 0:
        return True

    # Pour les modules suivants : cherche le module précédent
    # __lt = "less than" (strictement inférieur en SQL : WHERE order < module.order)
    # .order_by('-order') = tri décroissant → .first() donne le plus grand order inférieur
    prev_module = Module.objects.filter(
        formation=module.formation,
        order__lt=module.order,
    ).order_by('-order').first()

    if prev_module is None:
        return True  # Pas de module précédent → accessible

    # Vérifie si le module précédent a un quiz associé
    # hasattr(prev_module, 'quiz') → vérifie si la relation OneToOne existe
    if hasattr(prev_module, 'quiz'):
        # Le module précédent a un quiz : il faut l'avoir réussi
        return QuizAttempt.objects.filter(
            user=user,
            quiz=prev_module.quiz,
            is_passed=True,  # is_passed=True → score >= passing_score
        ).exists()

    # Le module précédent n'a pas de quiz → accessible directement
    return True


# ================================================================
# 3. AUTHENTIFICATION
# ================================================================

class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Crée un nouveau compte utilisateur (inscription).

    Données attendues (JSON) :
    {
        "email": "jean@example.com",
        "first_name": "Jean",
        "last_name": "Dupont",
        "password": "monMotDePasse123",
        "password_confirm": "monMotDePasse123"
    }

    Permission : AllowAny → tout le monde peut s'inscrire sans être connecté.
    """

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/auth/profile/ → affiche le profil de l'utilisateur connecté
    PATCH /api/auth/profile/ → modifie le profil (prénom, bio, avatar...)

    Pas de PUT (remplacement total) : on préfère PATCH (modification partielle).
    C'est plus sûr : Flutter envoie seulement les champs modifiés.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    # http_method_names → liste les méthodes HTTP acceptées par cette vue
    # On exclut 'put' pour forcer l'usage de 'patch' (modification partielle)
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        # Retourne l'utilisateur extrait du token JWT (pas un id dans l'URL)
        # self.request.user est rempli automatiquement par JWTAuthentication
        return self.request.user


# ================================================================
# 4. CATALOGUE
# ================================================================

class CategoryListView(generics.ListAPIView):
    """
    GET /api/categories/
    Retourne toutes les catégories avec le nombre de formations publiées.
    Accessible sans connexion (affichage pour les visiteurs).
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class FormationListView(generics.ListAPIView):
    """
    GET /api/formations/
    Catalogue des formations publiées et visibles.

    Filtres optionnels (paramètres d'URL) :
    - ?category=<slug>   → ex: ?category=developpement-web
    - ?level=<niveau>    → debutant | intermediaire | avance
    - ?search=<texte>    → recherche dans le titre et la description
    """

    serializer_class = FormationListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        get_queryset() est appelé par DRF pour obtenir la liste des objets à afficher.
        On le surcharge pour appliquer les filtres optionnels.
        """
        # Base : formations publiées et visibles dans le catalogue
        queryset = Formation.objects.filter(
            is_published=True,
            status='publiee',
        ).select_related('formateur', 'category')
        # select_related → Django charge le formateur et la catégorie en UNE SEULE requête SQL
        # Sans ça : N+1 requêtes (une par formation pour charger le formateur) → lent

        # Filtrage par catégorie (slug = identifiant texte de la catégorie)
        category_slug = self.request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Filtrage par niveau
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)

        # Recherche textuelle dans titre ET description
        search = self.request.query_params.get('search')
        if search:
            # Q() permet de combiner des conditions avec OR (|) ou AND (&)
            # icontains = insensible à la casse (majuscules/minuscules)
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        return queryset


class FormationDetailView(generics.RetrieveAPIView):
    """
    GET /api/formations/{id}/
    Détail complet d'une formation (avec modules, leçons et is_enrolled).

    Accessible sans connexion.
    is_enrolled sera False pour un visiteur, True pour un apprenant inscrit.
    """

    queryset = Formation.objects.filter(is_published=True)
    serializer_class = FormationDetailSerializer
    permission_classes = [AllowAny]
    # Pas besoin de surcharger get_serializer_context() :
    # DRF passe automatiquement {'request': request, 'view': self, 'format': format}


class FormationCreateView(generics.CreateAPIView):
    """
    POST /api/formations/
    Crée une nouvelle formation.

    Permission : formateur ou admin uniquement.
    Le formateur est automatiquement assigné à partir du token (pas envoyé par Flutter).
    """

    serializer_class = FormationWriteSerializer
    permission_classes = [IsFormateur]

    def perform_create(self, serializer):
        """
        perform_create() est appelé après validation du serializer, juste avant la sauvegarde.
        On y ajoute automatiquement le formateur = l'utilisateur connecté.
        """
        serializer.save(formateur=self.request.user)


class FormationUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/formations/{id}/
    Modifie une formation existante.

    Règle de sécurité :
    - Un formateur ne peut modifier QUE ses propres formations
    - Un admin peut modifier TOUTES les formations
    """

    serializer_class = FormationWriteSerializer
    permission_classes = [IsFormateur]
    http_method_names = ['patch', 'head', 'options']

    def get_queryset(self):
        # Un admin voit toutes les formations
        if self.request.user.is_admin:
            return Formation.objects.all()
        # Un formateur ne voit que ses formations (filtre sur formateur=moi)
        return Formation.objects.filter(formateur=self.request.user)


# ================================================================
# 5. LEÇONS ET PROGRESSION
# ================================================================

class LessonDetailView(generics.RetrieveAPIView):
    """
    GET /api/lessons/{id}/
    Retourne le contenu d'une leçon.

    Contrôle d'accès :
    - Leçon/module d'aperçu → accessible à tous les utilisateurs connectés
    - Autres leçons → inscription requise ET module débloqué

    Effet de bord : crée automatiquement un LessonProgress
    (enregistrement de début de leçon) à la première ouverture.
    """

    queryset = Lesson.objects.select_related('module__formation')
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        """
        retrieve() est la méthode appelée sur GET.
        On la surcharge pour ajouter notre logique d'accès personnalisée.
        """
        lesson = self.get_object()  # Récupère la leçon (ou renvoie 404 si introuvable)

        # Leçon ou module en aperçu → accessible sans vérification supplémentaire
        if lesson.is_preview or lesson.module.is_preview:
            serializer = self.get_serializer(lesson)
            return Response(serializer.data)

        # Vérifie que le module est débloqué pour cet utilisateur
        if not _can_access_module(request.user, lesson.module):
            return Response(
                {"detail": "Ce module n'est pas encore accessible. Complétez le quiz précédent."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Crée automatiquement le suivi de progression à la première ouverture
        # get_or_create → si déjà existant : récupère | si nouveau : crée
        # Le "_" (underscore) ignore la valeur de retour "created" (True/False)
        LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
        )

        serializer = self.get_serializer(lesson)
        return Response(serializer.data)


class LessonProgressView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/lessons/{lesson_id}/progress/
        → récupère la progression (position vidéo, état de complétion)

    PATCH /api/lessons/{lesson_id}/progress/
        → met à jour la position dans la vidéo (appelé par Flutter toutes les 10 secondes)
        Données attendues : { "video_position_sec": 145 }
    """

    serializer_class = LessonProgressSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        """
        Récupère (ou crée) la progression de l'utilisateur connecté pour la leçon donnée.
        lesson_id est passé dans l'URL : /api/lessons/{lesson_id}/progress/
        """
        lesson_id = self.kwargs['lesson_id']  # self.kwargs = paramètres extraits de l'URL
        lesson = get_object_or_404(Lesson, id=lesson_id)

        # get_or_create : si l'apprenant n'a jamais ouvert cette leçon → crée le suivi
        progress, _ = LessonProgress.objects.get_or_create(
            user=self.request.user,
            lesson=lesson,
        )
        return progress


class LessonCompleteView(APIView):
    """
    POST /api/lessons/{lesson_id}/complete/
    Marque une leçon comme terminée.

    Déclenche une cascade automatique (définie dans models.py) :
    1. LessonProgress.is_completed → True
    2. Enrollment.progress_percent → recalculé
    3. Si 100% ET tous quiz réussis → Enrollment.status → 'complete'
    4. Un certificat peut alors être généré
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id)

        # Récupère ou crée le suivi de progression
        progress, _ = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
        )

        # Si la leçon est déjà terminée, on répond sans refaire les calculs
        if progress.is_completed:
            return Response(
                {"detail": "Cette leçon est déjà terminée.", "is_completed": True},
                status=status.HTTP_200_OK,
            )

        # Marque comme terminée et déclenche la mise à jour de la progression globale
        progress.mark_completed()

        return Response(
            {"detail": "Leçon marquée comme terminée.", "is_completed": True},
            status=status.HTTP_200_OK,
        )


# ================================================================
# 6. INSCRIPTIONS
# ================================================================

class EnrollmentListView(generics.ListAPIView):
    """
    GET /api/enrollments/
    Liste toutes les formations auxquelles l'apprenant connecté est inscrit.
    """

    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Ne retourne QUE les inscriptions de l'utilisateur connecté
        return Enrollment.objects.filter(
            user=self.request.user,
        ).select_related('formation', 'formation__formateur', 'formation__category').order_by('-enrolled_at')


class EnrollmentDetailView(generics.RetrieveAPIView):
    """
    GET /api/enrollments/{id}/
    Détail d'une inscription spécifique (progression, statut, formation).
    """

    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Sécurité : l'utilisateur ne peut voir QUE ses propres inscriptions
        return Enrollment.objects.filter(user=self.request.user)


# ================================================================
# 7. QUIZ
# ================================================================

class QuizDetailView(generics.RetrieveAPIView):
    """
    GET /api/quiz/{id}/
    Affiche un quiz avec ses questions (SANS les bonnes réponses → sécurité).

    Accessible uniquement si le module est débloqué pour l'utilisateur.
    """

    queryset = Quiz.objects.select_related('module__formation')
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        quiz = self.get_object()

        # Vérifie que le module du quiz est accessible
        if not _can_access_module(request.user, quiz.module):
            return Response(
                {"detail": "Ce quiz n'est pas encore accessible."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(quiz)
        return Response(serializer.data)


class QuizStartView(APIView):
    """
    POST /api/quiz/{quiz_id}/start/
    Démarre une nouvelle tentative de quiz.

    Vérifie que le nombre maximum de tentatives n'est pas atteint.
    Retourne l'id de la tentative créée → Flutter l'utilise pour soumettre les réponses.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)

        # Vérifie l'accès au module
        if not _can_access_module(request.user, quiz.module):
            return Response(
                {"detail": "Ce quiz n'est pas encore accessible."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Compte les tentatives déjà effectuées par cet utilisateur sur ce quiz
        attempts_count = QuizAttempt.objects.filter(
            user=request.user,
            quiz=quiz,
        ).count()

        # quiz.max_attempts == 0 signifie "illimité" → on ne bloque pas
        if quiz.max_attempts > 0 and attempts_count >= quiz.max_attempts:
            return Response(
                {
                    "detail": (
                        f"Nombre maximum de tentatives atteint ({quiz.max_attempts})."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Crée la nouvelle tentative avec le bon numéro de séquence
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            attempt_number=attempts_count + 1,
        )

        serializer = QuizAttemptSerializer(attempt, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuizSubmitView(APIView):
    """
    POST /api/attempts/{attempt_id}/submit/
    Soumet les réponses et calcule le score final.

    Flutter envoie les réponses dans le corps de la requête :
    {
        "responses": [
            {"question": "uuid-de-la-question-1", "selected_option": "uuid-de-l-option"},
            {"question": "uuid-de-la-question-2", "selected_option": "uuid-de-l-option"},
            ...
        ]
    }

    Le serveur :
    1. Enregistre chaque réponse (QuizResponse.save() calcule is_correct automatiquement)
    2. Calcule le score final (QuizAttempt.calculate_score())
    3. Retourne le résultat complet avec score et is_passed
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, attempt_id):
        # Récupère la tentative — vérifie aussi que c'est bien la tentative de CET utilisateur
        attempt = get_object_or_404(
            QuizAttempt,
            id=attempt_id,
            user=request.user,  # Sécurité : un utilisateur ne peut soumettre que ses propres tentatives
        )

        # Une tentative déjà soumise a completed_at rempli (défini dans calculate_score())
        if attempt.completed_at:
            return Response(
                {"detail": "Cette tentative a déjà été soumise."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Récupère la liste des réponses envoyées par Flutter
        responses_data = request.data.get('responses', [])
        if not responses_data:
            return Response(
                {"detail": "Aucune réponse fournie."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Enregistre chaque réponse individuellement
        errors = []
        for item in responses_data:
            serializer = QuizResponseSerializer(
                data=item,
                context={'request': request},
            )
            if serializer.is_valid():
                # attempt est passé à save() pour lier la réponse à cette tentative
                # Ce champ n'est pas dans les fields du serializer mais est requis par le modèle
                serializer.save(attempt=attempt)
            else:
                errors.append(serializer.errors)

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        # Calcule le score final et met à jour la progression si le quiz est réussi
        attempt.calculate_score()

        # Retourne le résultat complet de la tentative
        result_serializer = QuizAttemptSerializer(attempt, context={'request': request})
        return Response(result_serializer.data)


class QuizAttemptDetailView(generics.RetrieveAPIView):
    """
    GET /api/attempts/{id}/
    Résultat détaillé d'une tentative (score, réponses, corrections).
    Utile pour que Flutter affiche le corrigé après soumission.
    """

    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Sécurité : seulement les tentatives de l'utilisateur connecté
        return QuizAttempt.objects.filter(user=self.request.user)


# ================================================================
# 8. CERTIFICATS
# ================================================================

class CertificateListView(generics.ListAPIView):
    """
    GET /api/certificates/
    Liste tous les certificats obtenus par l'utilisateur connecté.
    """

    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user).order_by('-issued_at')


class CertificateDetailView(generics.RetrieveAPIView):
    """
    GET /api/certificates/{id}/
    Détail d'un certificat obtenu.
    """

    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user)


class CertificateVerifyView(APIView):
    """
    GET /api/verify/{code}/
    Vérifie l'authenticité d'un certificat via son code unique (ex: EFG-A1B2C3D4).

    Permission : AllowAny → un employeur peut vérifier sans avoir de compte EFG.
    C'est l'endpoint public de vérification.
    """

    permission_classes = [AllowAny]

    def get(self, request, code):
        # Cherche le certificat par son code — renvoie 404 si introuvable (code invalide)
        certificate = get_object_or_404(Certificate, certificate_code=code)
        serializer = CertificateSerializer(certificate)
        return Response(serializer.data)


# ================================================================
# 9. PAIEMENTS
# ================================================================

class PaymentListView(generics.ListCreateAPIView):
    """
    GET  /api/payments/  → liste des paiements de l'utilisateur connecté
    POST /api/payments/  → initie un nouveau paiement

    Flux après un POST réussi :
    1. Le serveur crée un Payment (status='en_attente')
    2. Flutter reçoit la transaction_ref et redirige vers la passerelle de paiement
    3. L'apprenant paie sur la passerelle (Mobile Money, carte...)
    4. La passerelle confirme au serveur → PaymentConfirmView est appelée
    5. L'Enrollment est créé → accès complet débloqué
    """

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        perform_create() est appelé après validation du serializer.
        On ajoute les champs calculés côté serveur :
        - user            → l'utilisateur connecté
        - amount          → copie du prix de la formation à l'instant du paiement
        - transaction_ref → référence unique générée par nos soins
        """
        formation = serializer.validated_data['formation']

        # Génère une référence de transaction unique au format : EFG-PAY-XXXXXXXXXXXXXXXX
        # uuid4().hex → 32 caractères hexadécimaux aléatoires
        # [:16]        → on garde 16 caractères (suffisant pour l'unicité)
        transaction_ref = f"EFG-PAY-{uuid.uuid4().hex[:16].upper()}"

        serializer.save(
            user=self.request.user,
            amount=formation.price,   # Capture le prix actuel (ne change pas si le prix monte)
            transaction_ref=transaction_ref,
        )


class PaymentConfirmView(APIView):
    """
    POST /api/payments/{payment_id}/confirm/
    Confirme un paiement et crée l'inscription correspondante.

    EN PRODUCTION : cet endpoint sera appelé par le webhook de la passerelle de paiement
    (MTN MoMo, Orange Money, Stripe...) avec une signature sécurisée.

    POUR L'INSTANT : réservé aux admins pour les tests et la gestion manuelle.

    Actions effectuées :
    1. Payment.status → 'valide'
    2. Payment.paid_at → date/heure actuelle
    3. Enrollment créé → l'apprenant a accès au contenu complet
    """

    permission_classes = [IsAdmin]

    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)

        # On ne peut confirmer qu'un paiement qui est en attente
        if payment.status != 'en_attente':
            return Response(
                {
                    "detail": (
                        f"Ce paiement ne peut pas être confirmé "
                        f"(statut actuel : {payment.get_status_display()})."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Met à jour le statut et enregistre la date de paiement
        payment.status = 'valide'
        payment.paid_at = timezone.now()
        payment.save()

        # Crée l'inscription — get_or_create évite les doublons en cas de double appel
        enrollment, created = Enrollment.objects.get_or_create(
            user=payment.user,
            formation=payment.formation,
        )

        # Lie le paiement à l'inscription (relation OneToOne dans le modèle)
        payment.enrollment = enrollment
        payment.save()

        return Response(
            {
                "detail": "Paiement confirmé. Inscription créée.",
                "enrollment_id": str(enrollment.id),
                "created": created,  # True si nouvelle inscription, False si existait déjà
            },
            status=status.HTTP_200_OK,
        )


# ================================================================
# 10. ADMINISTRATION
# ================================================================

class AdminStatsView(APIView):
    """
    GET /api/admin/stats/
    Statistiques globales pour le tableau de bord administrateur.

    Retourne des chiffres calculés sur l'ensemble de la plateforme :
    - Nombre d'utilisateurs par rôle
    - Nombre de formations, inscriptions, certificats
    - Taux de progression moyen
    - Taux de complétion global
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        total_enrollments = Enrollment.objects.count()
        completed_enrollments = Enrollment.objects.filter(status='complete').count()

        stats = {
            'total_users': User.objects.count(),
            'total_apprenants': User.objects.filter(role='apprenant').count(),
            'total_formateurs': User.objects.filter(role='formateur').count(),
            'total_formations': Formation.objects.count(),
            'total_enrollments': total_enrollments,
            'total_certificates': Certificate.objects.count(),

            # aggregate(avg=Avg(...)) calcule la moyenne directement en SQL (rapide)
            # Le "or 0.0" gère le cas où il n'y a aucune inscription (Avg retourne None)
            'average_progress': float(
                Enrollment.objects.aggregate(avg=Avg('progress_percent'))['avg'] or 0.0
            ),

            # Taux de complétion = inscriptions terminées / total inscriptions × 100
            # round(..., 1) = arrondit à 1 décimale (ex: 66.7%)
            'completion_rate': (
                round((completed_enrollments / total_enrollments) * 100, 1)
                if total_enrollments > 0
                else 0.0
            ),
        }

        serializer = AdminStatsSerializer(stats)
        return Response(serializer.data)


class AdminUserListView(generics.ListAPIView):
    """
    GET /api/admin/users/
    Liste tous les utilisateurs de la plateforme.
    Filtrage optionnel par rôle : ?role=apprenant | formateur | admin
    """

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')

        # Filtrage optionnel par rôle (ex: ?role=formateur)
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        return queryset


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/admin/users/{id}/ → détail d'un utilisateur
    PATCH /api/admin/users/{id}/ → modifier (rôle, is_active, etc.)
    """

    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    http_method_names = ['get', 'patch', 'head', 'options']


class AdminFormationListView(generics.ListAPIView):
    """
    GET /api/admin/formations/
    Liste TOUTES les formations (y compris brouillons et non publiées).
    Filtrage par statut : ?status=brouillon | en_revue | publiee | archivee
    """

    serializer_class = AdminFormationSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = Formation.objects.all().select_related('formateur', 'category')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset


class AdminFormationDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/admin/formations/{id}/ → détail complet (avec nb d'inscrits)
    PATCH /api/admin/formations/{id}/ → modifier n'importe quel champ
                                        (statut, formateur, publication...)
    """

    queryset = Formation.objects.all()
    serializer_class = AdminFormationSerializer
    permission_classes = [IsAdmin]
    http_method_names = ['get', 'patch', 'head', 'options']
