"""
EFG E-Learning Platform — URLs de l'application
=================================================
Ce fichier définit les "routes" de l'API ElearningApp.

RÔLE :
Chaque ligne fait le lien entre une URL et une vue (view).
Quand Flutter envoie une requête vers /api/formations/,
Django lit ce fichier pour savoir quelle vue doit répondre.

CONVENTION DES PRÉFIXES :
- /api/auth/...          → Authentification (inscription, connexion, profil)
- /api/categories/       → Catégories de formations
- /api/formations/       → Catalogue des formations
- /api/lessons/          → Contenu des leçons et progression
- /api/enrollments/      → Inscriptions de l'apprenant connecté
- /api/quiz/             → Quiz et tentatives
- /api/attempts/         → Résultats de tentatives
- /api/certificates/     → Certificats obtenus
- /api/verify/           → Vérification publique des certificats
- /api/payments/         → Paiements
- /api/admin/            → Administration (réservé aux admins)

RAPPEL : Le préfixe /api/ est défini dans EFGLearning/urls.py (fichier principal).
         Ce fichier ne gère que ce qui vient APRÈS /api/.
"""

from django.urls import path

# TokenObtainPairView → génère access_token + refresh_token à partir de l'email/mot de passe
# TokenRefreshView   → génère un nouveau access_token à partir du refresh_token
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

# app_name → espace de noms pour éviter les conflits de noms entre applications
# Ex: reverse('elearning:register') au lieu de reverse('register')
app_name = 'elearning'

urlpatterns = [

    # ── AUTHENTIFICATION ──────────────────────────────────────────────────────
    # POST → inscription (email, first_name, last_name, password, password_confirm)
    path('auth/register/', views.RegisterView.as_view(), name='register'),

    # POST → connexion : renvoie { "access": "...", "refresh": "..." }
    # Géré directement par django-simplejwt (pas besoin de vue custom)
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),

    # POST → renouvellement du access_token expiré via le refresh_token
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # GET  → afficher le profil de l'utilisateur connecté
    # PATCH → modifier le profil (prénom, bio, avatar...)
    path('auth/profile/', views.ProfileView.as_view(), name='profile'),


    # ── CATALOGUE ─────────────────────────────────────────────────────────────
    # GET → liste toutes les catégories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),

    # GET  → catalogue des formations publiées (avec filtres ?category, ?level, ?search)
    path('formations/', views.FormationListView.as_view(), name='formation-list'),

    # POST → créer une nouvelle formation (formateur/admin seulement)
    path('formations/create/', views.FormationCreateView.as_view(), name='formation-create'),

    # GET  → détail complet d'une formation (modules, leçons, is_enrolled)
    # <uuid:pk> → capture l'identifiant UUID dans l'URL (ex: /formations/550e8400-e29b-.../)
    path('formations/<uuid:pk>/', views.FormationDetailView.as_view(), name='formation-detail'),

    # PATCH → modifier une formation existante (formateur/admin seulement)
    path('formations/<uuid:pk>/edit/', views.FormationUpdateView.as_view(), name='formation-update'),


    # ── LEÇONS ────────────────────────────────────────────────────────────────
    # GET → contenu d'une leçon (vérifie aussi l'accès et crée un LessonProgress)
    path('lessons/<uuid:pk>/', views.LessonDetailView.as_view(), name='lesson-detail'),

    # GET   → position vidéo et état de complétion
    # PATCH → mettre à jour la position vidéo (toutes les 10 secondes depuis Flutter)
    path(
        'lessons/<uuid:lesson_id>/progress/',
        views.LessonProgressView.as_view(),
        name='lesson-progress',
    ),

    # POST → marquer une leçon comme terminée (déclenche la mise à jour de la progression)
    path(
        'lessons/<uuid:lesson_id>/complete/',
        views.LessonCompleteView.as_view(),
        name='lesson-complete',
    ),


    # ── INSCRIPTIONS ──────────────────────────────────────────────────────────
    # GET → liste des formations suivies par l'apprenant connecté
    path('enrollments/', views.EnrollmentListView.as_view(), name='enrollment-list'),

    # GET → détail d'une inscription (progression, statut)
    path('enrollments/<uuid:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment-detail'),


    # ── QUIZ ──────────────────────────────────────────────────────────────────
    # GET → affiche le quiz avec ses questions (SANS les bonnes réponses)
    path('quiz/<uuid:pk>/', views.QuizDetailView.as_view(), name='quiz-detail'),

    # POST → démarre une nouvelle tentative (renvoie l'id de la tentative créée)
    path('quiz/<uuid:quiz_id>/start/', views.QuizStartView.as_view(), name='quiz-start'),

    # POST → soumet les réponses et calcule le score final
    path(
        'attempts/<uuid:attempt_id>/submit/',
        views.QuizSubmitView.as_view(),
        name='quiz-submit',
    ),

    # GET → résultat détaillé d'une tentative (score, réponses, corrections)
    path('attempts/<uuid:pk>/', views.QuizAttemptDetailView.as_view(), name='attempt-detail'),


    # ── CERTIFICATS ───────────────────────────────────────────────────────────
    # GET → liste des certificats obtenus par l'apprenant connecté
    path('certificates/', views.CertificateListView.as_view(), name='certificate-list'),

    # GET → détail d'un certificat (avec code et URL de vérification)
    path('certificates/<uuid:pk>/', views.CertificateDetailView.as_view(), name='certificate-detail'),

    # GET → vérification publique d'un certificat via son code (ex: EFG-A1B2C3D4)
    # AllowAny → accessible sans compte, pour les employeurs
    # <str:code> → capture la chaîne de caractères (ex: "EFG-A1B2C3D4")
    path('verify/<str:code>/', views.CertificateVerifyView.as_view(), name='certificate-verify'),


    # ── PAIEMENTS ─────────────────────────────────────────────────────────────
    # GET  → liste des paiements de l'utilisateur connecté
    # POST → initie un nouveau paiement (renvoie transaction_ref pour la passerelle)
    path('payments/', views.PaymentListView.as_view(), name='payment-list'),

    # POST → confirme un paiement et crée l'inscription (admin ou webhook de la passerelle)
    path(
        'payments/<uuid:payment_id>/confirm/',
        views.PaymentConfirmView.as_view(),
        name='payment-confirm',
    ),


    # ── ADMINISTRATION ────────────────────────────────────────────────────────
    # GET → statistiques globales : nb utilisateurs, formations, taux de complétion...
    path('admin/stats/', views.AdminStatsView.as_view(), name='admin-stats'),

    # GET → liste tous les utilisateurs (filtrable par ?role=apprenant|formateur|admin)
    path('admin/users/', views.AdminUserListView.as_view(), name='admin-user-list'),

    # GET/PATCH → voir et modifier un utilisateur spécifique
    path('admin/users/<uuid:pk>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),

    # GET → liste TOUTES les formations (même brouillons, filtrable par ?status=...)
    path('admin/formations/', views.AdminFormationListView.as_view(), name='admin-formation-list'),

    # GET/PATCH → voir et modifier n'importe quelle formation (publication, changement de formateur...)
    path(
        'admin/formations/<uuid:pk>/',
        views.AdminFormationDetailView.as_view(),
        name='admin-formation-detail',
    ),
]
