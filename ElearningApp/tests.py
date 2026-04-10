"""
EFG E-Learning Platform — Tests automatiques
=============================================
Ce fichier contient tous les tests automatiques de l'API.

POURQUOI TESTER ?
Les tests vérifient automatiquement que chaque endpoint fonctionne correctement.
Si on modifie du code plus tard et qu'un test échoue → on sait immédiatement
qu'on a cassé quelque chose, sans avoir à tout retester à la main.

COMMENT LANCER LES TESTS :
    # Tous les tests
    python EFGLearning/manage.py test ElearningApp

    # Une seule classe de tests
    python EFGLearning/manage.py test ElearningApp.tests.AuthTests

    # Une seule méthode de test
    python EFGLearning/manage.py test ElearningApp.tests.AuthTests.test_register_success

COMMENT ÇA MARCHE :
1. Django crée une base de données temporaire (vide) juste pour les tests
2. setUp() est appelé AVANT chaque test pour préparer les données
3. Le test s'exécute
4. La base est effacée entre chaque test → tests isolés et indépendants

ORGANISATION :
1. Helpers  → fonctions partagées pour créer des données de test
2. Auth     → inscription, connexion, profil
3. Catalogue→ catégories, formations
4. Leçons   → accès au contenu, progression
5. Quiz     → démarrage, soumission, résultats
6. Certificats et paiements
7. Admin    → permissions et statistiques
"""

from decimal import Decimal

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
# APITestCase → version de TestCase adaptée aux APIs REST
# Elle fournit self.client (APIClient) qui peut envoyer des requêtes HTTP simulées


from .models import (
    User, Category, Formation, Module, Lesson,
    Quiz, Question, AnswerOption,
    Enrollment, Payment, LessonProgress,
    QuizAttempt, QuizResponse, Certificate,
)


# ================================================================
# HELPERS — Fonctions utilitaires partagées par tous les tests
# ================================================================

def create_user(email='apprenant@test.com', password='TestPass123!', role='apprenant', **kwargs):
    """
    Crée un utilisateur de test en une ligne.
    Les valeurs par défaut permettent de créer rapidement un apprenant standard.
    **kwargs → on peut passer des champs supplémentaires (ex: first_name='Jean')
    """
    return User.objects.create_user(
        email=email,
        password=password,
        first_name=kwargs.pop('first_name', 'Test'),
        last_name=kwargs.pop('last_name', 'User'),
        role=role,
        **kwargs,
    )


def create_category(name='Développement', slug='developpement'):
    """Crée une catégorie de test."""
    return Category.objects.create(name=name, slug=slug)


def create_formation(formateur, category=None, price=10000, published=True):
    """
    Crée une formation de test complète et publiée par défaut.
    Si published=True → status='publiee' et is_published=True (visible dans le catalogue).
    """
    return Formation.objects.create(
        formateur=formateur,
        category=category,
        title='Formation Test',
        description='Une formation de test.',
        price=Decimal(str(price)),
        level='debutant',
        status='publiee' if published else 'brouillon',
        is_published=published,
    )


def create_full_formation(formateur, category=None):
    """
    Crée une formation complète avec un module, une leçon et un quiz.
    Utilisée par les tests de progression et de quiz.

    Structure créée :
    Formation
      └── Module (order=0)
            ├── Leçon (order=0)
            └── Quiz
                  └── Question
                        ├── Option A (correcte)
                        └── Option B (incorrecte)
    """
    formation = create_formation(formateur, category)
    module = Module.objects.create(
        formation=formation,
        title='Module 1',
        order=0,
    )
    lesson = Lesson.objects.create(
        module=module,
        title='Leçon 1',
        content_type='text',
        content_text='Contenu de la leçon de test.',
        order=0,
    )
    quiz = Quiz.objects.create(
        module=module,
        title='Quiz Module 1',
        passing_score=50,
        max_attempts=3,
    )
    question = Question.objects.create(
        quiz=quiz,
        question_text='Quelle est la capitale du Sénégal ?',
        question_type='qcm',
        points=1,
        order=0,
    )
    correct_option = AnswerOption.objects.create(
        question=question,
        option_text='Dakar',
        is_correct=True,
        order=0,
    )
    wrong_option = AnswerOption.objects.create(
        question=question,
        option_text='Abidjan',
        is_correct=False,
        order=1,
    )
    # Retourne tous les objets créés pour que les tests puissent les utiliser
    return formation, module, lesson, quiz, question, correct_option, wrong_option


# ================================================================
# 1. TESTS D'AUTHENTIFICATION
# ================================================================

class AuthTests(APITestCase):
    """Tests pour l'inscription, la connexion et le profil."""

    def test_register_success(self):
        """Un nouvel utilisateur peut s'inscrire avec des données valides."""
        url = reverse('elearning:register')
        data = {
            'email': 'nouveau@test.com',
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        }
        response = self.client.post(url, data)

        # 201 Created = l'utilisateur a bien été créé
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Vérifie que l'utilisateur existe bien en base
        self.assertTrue(User.objects.filter(email='nouveau@test.com').exists())

    def test_register_passwords_mismatch(self):
        """L'inscription échoue si les deux mots de passe ne correspondent pas."""
        url = reverse('elearning:register')
        data = {
            'email': 'test@test.com',
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'password': 'SecurePass123!',
            'password_confirm': 'AutreMotDePasse!',  # ← différent
        }
        response = self.client.post(url, data)

        # 400 Bad Request = données invalides
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        """L'inscription échoue si l'email est déjà utilisé."""
        create_user(email='existant@test.com')

        url = reverse('elearning:register')
        data = {
            'email': 'existant@test.com',  # ← email déjà pris
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        """Un utilisateur peut se connecter et recevoir un token JWT."""
        create_user(email='user@test.com', password='TestPass123!')

        url = reverse('elearning:token_obtain')
        response = self.client.post(url, {
            'email': 'user@test.com',
            'password': 'TestPass123!',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Vérifie que la réponse contient bien les deux tokens
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password(self):
        """La connexion échoue avec un mauvais mot de passe."""
        create_user(email='user@test.com', password='TestPass123!')

        url = reverse('elearning:token_obtain')
        response = self.client.post(url, {
            'email': 'user@test.com',
            'password': 'MauvaisMotDePasse!',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get(self):
        """Un utilisateur connecté peut voir son profil."""
        user = create_user()

        # force_authenticate → simule une connexion sans avoir à passer par le flow JWT
        # Équivalent de : "considère cet utilisateur comme connecté pour ce test"
        self.client.force_authenticate(user=user)

        url = reverse('elearning:profile')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], user.email)

    def test_profile_update(self):
        """Un utilisateur peut modifier son prénom et sa bio."""
        user = create_user()
        self.client.force_authenticate(user=user)

        url = reverse('elearning:profile')
        response = self.client.patch(url, {
            'first_name': 'Nouveau Prénom',
            'bio': 'Ma nouvelle bio.',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Nouveau Prénom')

    def test_profile_requires_auth(self):
        """Un visiteur non connecté ne peut pas accéder au profil."""
        url = reverse('elearning:profile')
        response = self.client.get(url)
        # 401 Unauthorized = token absent ou invalide
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ================================================================
# 2. TESTS CATALOGUE
# ================================================================

class CatalogueTests(APITestCase):
    """Tests pour les catégories et le catalogue de formations."""

    def setUp(self):
        """
        setUp() est appelé AVANT chaque test de cette classe.
        Prépare les données de base nécessaires aux tests.
        """
        self.formateur = create_user(email='formateur@test.com', role='formateur')
        self.category = create_category()
        self.formation = create_formation(self.formateur, self.category)

    def test_categories_list(self):
        """La liste des catégories est accessible sans connexion."""
        url = reverse('elearning:category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Au moins une catégorie créée dans setUp
        self.assertGreaterEqual(response.data['count'], 1)

    def test_formations_list_public(self):
        """Le catalogue des formations est accessible sans connexion."""
        url = reverse('elearning:formation-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_formations_list_filter_by_category(self):
        """Le filtre ?category= retourne seulement les formations de cette catégorie."""
        # Crée une 2ème catégorie et formation pour vérifier que le filtre fonctionne
        other_category = create_category(name='Marketing', slug='marketing')
        create_formation(self.formateur, other_category)

        url = reverse('elearning:formation-list')
        response = self.client.get(url, {'category': self.category.slug})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Seule la formation de la catégorie "developpement" doit apparaître
        self.assertEqual(response.data['count'], 1)

    def test_formations_list_search(self):
        """La recherche textuelle filtre les formations par titre."""
        url = reverse('elearning:formation-list')
        response = self.client.get(url, {'search': 'Formation Test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_formation_detail_public(self):
        """Le détail d'une formation est accessible sans connexion."""
        url = reverse('elearning:formation-detail', kwargs={'pk': self.formation.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.formation.title)
        # Un visiteur n'est pas inscrit → is_enrolled doit être False
        self.assertFalse(response.data['is_enrolled'])

    def test_formation_detail_is_enrolled(self):
        """is_enrolled est True pour un apprenant inscrit à la formation."""
        apprenant = create_user()
        Enrollment.objects.create(user=apprenant, formation=self.formation)
        self.client.force_authenticate(user=apprenant)

        url = reverse('elearning:formation-detail', kwargs={'pk': self.formation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_enrolled'])

    def test_unpublished_formation_hidden(self):
        """Une formation non publiée n'apparaît pas dans le catalogue."""
        create_formation(self.formateur, self.category, published=False)

        url = reverse('elearning:formation-list')
        response = self.client.get(url)

        # Seulement la formation publiée (créée dans setUp) doit apparaître
        self.assertEqual(response.data['count'], 1)

    def test_formateur_can_create_formation(self):
        """Un formateur peut créer une formation."""
        self.client.force_authenticate(user=self.formateur)

        url = reverse('elearning:formation-create')
        data = {
            'title': 'Nouvelle Formation',
            'description': 'Description de ma nouvelle formation.',
            'price': '5000.00',
            'level': 'debutant',
            'category': str(self.category.id),
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_apprenant_cannot_create_formation(self):
        """Un apprenant ne peut PAS créer une formation."""
        apprenant = create_user()
        self.client.force_authenticate(user=apprenant)

        url = reverse('elearning:formation-create')
        response = self.client.post(url, {'title': 'Tentative'})
        # 403 Forbidden = connecté mais pas le bon rôle
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ================================================================
# 3. TESTS INSCRIPTIONS ET LEÇONS
# ================================================================

class LessonProgressTests(APITestCase):
    """Tests pour l'accès aux leçons et le suivi de progression."""

    def setUp(self):
        self.formateur = create_user(email='formateur@test.com', role='formateur')
        self.apprenant = create_user(email='apprenant@test.com')
        self.category = create_category()

        # Crée une formation complète (formation + module + leçon + quiz)
        result = create_full_formation(self.formateur, self.category)
        self.formation, self.module, self.lesson = result[0], result[1], result[2]
        self.quiz, self.question = result[3], result[4]
        self.correct_option, self.wrong_option = result[5], result[6]

        # Inscrit l'apprenant à la formation
        self.enrollment = Enrollment.objects.create(
            user=self.apprenant,
            formation=self.formation,
        )

    def test_lesson_access_enrolled_user(self):
        """Un apprenant inscrit peut accéder à une leçon du premier module."""
        self.client.force_authenticate(user=self.apprenant)
        url = reverse('elearning:lesson-detail', kwargs={'pk': self.lesson.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_lesson_access_unenrolled_user(self):
        """Un apprenant NON inscrit ne peut pas accéder à une leçon non-aperçu."""
        autre_apprenant = create_user(email='autre@test.com')
        self.client.force_authenticate(user=autre_apprenant)

        url = reverse('elearning:lesson-detail', kwargs={'pk': self.lesson.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_lesson_creates_progress_on_open(self):
        """L'ouverture d'une leçon crée automatiquement un LessonProgress."""
        self.client.force_authenticate(user=self.apprenant)
        url = reverse('elearning:lesson-detail', kwargs={'pk': self.lesson.id})
        self.client.get(url)

        # Vérifie que le suivi de progression a été créé
        self.assertTrue(
            LessonProgress.objects.filter(
                user=self.apprenant,
                lesson=self.lesson,
            ).exists()
        )

    def test_lesson_complete(self):
        """Marquer une leçon comme terminée met à jour la progression de l'inscription."""
        self.client.force_authenticate(user=self.apprenant)
        url = reverse('elearning:lesson-complete', kwargs={'lesson_id': self.lesson.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_completed'])

        # Recharge l'enrollment depuis la base pour vérifier la progression
        self.enrollment.refresh_from_db()
        # La formation a 1 leçon et elle est terminée → 100%
        # Mais le quiz n'est pas encore réussi → statut reste 'actif' (pas 'complete')
        self.assertEqual(self.enrollment.progress_percent, 100)
        self.assertEqual(self.enrollment.status, 'actif')

    def test_video_position_update(self):
        """Flutter peut mettre à jour la position vidéo d'une leçon."""
        # Crée le suivi de progression d'abord
        LessonProgress.objects.create(user=self.apprenant, lesson=self.lesson)
        self.client.force_authenticate(user=self.apprenant)

        url = reverse('elearning:lesson-progress', kwargs={'lesson_id': self.lesson.id})
        response = self.client.patch(url, {'video_position_sec': 145})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['video_position_sec'], 145)

    def test_enrollment_list(self):
        """L'apprenant voit ses inscriptions dans /api/enrollments/."""
        self.client.force_authenticate(user=self.apprenant)
        url = reverse('elearning:enrollment-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)


# ================================================================
# 4. TESTS QUIZ
# ================================================================

class QuizTests(APITestCase):
    """Tests pour le flux complet d'un quiz : démarrage, soumission, résultat."""

    def setUp(self):
        self.formateur = create_user(email='formateur@test.com', role='formateur')
        self.apprenant = create_user(email='apprenant@test.com')
        self.category = create_category()

        result = create_full_formation(self.formateur, self.category)
        self.formation, self.module, self.lesson = result[0], result[1], result[2]
        self.quiz, self.question = result[3], result[4]
        self.correct_option, self.wrong_option = result[5], result[6]

        # Inscrit l'apprenant
        self.enrollment = Enrollment.objects.create(
            user=self.apprenant,
            formation=self.formation,
        )

    def test_quiz_detail_hides_correct_answers(self):
        """Les bonnes réponses sont cachées dans la réponse envoyée à l'apprenant."""
        self.client.force_authenticate(user=self.apprenant)
        url = reverse('elearning:quiz-detail', kwargs={'pk': self.quiz.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Parcourt les options de réponse dans la réponse JSON
        for question in response.data['questions']:
            for option in question['options']:
                # is_correct ne doit PAS apparaître dans les données envoyées à l'apprenant
                self.assertNotIn('is_correct', option)

    def test_quiz_start(self):
        """Un apprenant peut démarrer une nouvelle tentative de quiz."""
        self.client.force_authenticate(user=self.apprenant)
        url = reverse('elearning:quiz-start', kwargs={'quiz_id': self.quiz.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # La tentative créée doit avoir le numéro 1 (première tentative)
        self.assertEqual(response.data['attempt_number'], 1)

    def test_quiz_submit_correct_answer(self):
        """Soumettre la bonne réponse donne un score de 100% et is_passed=True."""
        self.client.force_authenticate(user=self.apprenant)

        # Étape 1 : démarrer la tentative
        start_url = reverse('elearning:quiz-start', kwargs={'quiz_id': self.quiz.id})
        start_response = self.client.post(start_url)
        attempt_id = start_response.data['id']

        # Étape 2 : soumettre la bonne réponse
        submit_url = reverse('elearning:quiz-submit', kwargs={'attempt_id': attempt_id})
        submit_response = self.client.post(submit_url, {
            'responses': [
                {
                    'question': str(self.question.id),
                    'selected_option': str(self.correct_option.id),
                }
            ]
        }, format='json')
        # format='json' → sérialise les données en JSON (nécessaire pour les listes imbriquées)

        self.assertEqual(submit_response.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_response.data['score'], 100)
        self.assertTrue(submit_response.data['is_passed'])

    def test_quiz_submit_wrong_answer(self):
        """Soumettre une mauvaise réponse donne un score de 0% et is_passed=False."""
        self.client.force_authenticate(user=self.apprenant)

        start_url = reverse('elearning:quiz-start', kwargs={'quiz_id': self.quiz.id})
        attempt_id = self.client.post(start_url).data['id']

        submit_url = reverse('elearning:quiz-submit', kwargs={'attempt_id': attempt_id})
        response = self.client.post(submit_url, {
            'responses': [
                {
                    'question': str(self.question.id),
                    'selected_option': str(self.wrong_option.id),  # ← mauvaise réponse
                }
            ]
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['score'], 0)
        self.assertFalse(response.data['is_passed'])

    def test_quiz_max_attempts_exceeded(self):
        """On ne peut pas démarrer une tentative si le maximum est atteint."""
        self.client.force_authenticate(user=self.apprenant)

        # Crée manuellement 3 tentatives (max_attempts=3 défini dans setUp)
        for i in range(1, 4):
            QuizAttempt.objects.create(
                user=self.apprenant,
                quiz=self.quiz,
                attempt_number=i,
            )

        # Tenter une 4ème tentative doit être refusé
        url = reverse('elearning:quiz-start', kwargs={'quiz_id': self.quiz.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quiz_cannot_submit_twice(self):
        """Une tentative déjà soumise ne peut pas être soumise à nouveau."""
        self.client.force_authenticate(user=self.apprenant)

        start_url = reverse('elearning:quiz-start', kwargs={'quiz_id': self.quiz.id})
        attempt_id = self.client.post(start_url).data['id']

        # Première soumission
        submit_url = reverse('elearning:quiz-submit', kwargs={'attempt_id': attempt_id})
        self.client.post(submit_url, {
            'responses': [
                {
                    'question': str(self.question.id),
                    'selected_option': str(self.correct_option.id),
                }
            ]
        }, format='json')

        # Deuxième soumission → doit être refusée
        response = self.client.post(submit_url, {
            'responses': [
                {
                    'question': str(self.question.id),
                    'selected_option': str(self.correct_option.id),
                }
            ]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_full_completion_generates_certificate_eligible(self):
        """
        Terminer toutes les leçons + réussir tous les quiz
        passe l'enrollment au statut 'complete'.
        """
        self.client.force_authenticate(user=self.apprenant)

        # 1. Marquer la leçon comme terminée
        complete_url = reverse('elearning:lesson-complete', kwargs={'lesson_id': self.lesson.id})
        self.client.post(complete_url)

        # 2. Démarrer et réussir le quiz
        start_url = reverse('elearning:quiz-start', kwargs={'quiz_id': self.quiz.id})
        attempt_id = self.client.post(start_url).data['id']

        submit_url = reverse('elearning:quiz-submit', kwargs={'attempt_id': attempt_id})
        self.client.post(submit_url, {
            'responses': [
                {
                    'question': str(self.question.id),
                    'selected_option': str(self.correct_option.id),
                }
            ]
        }, format='json')

        # Recharge l'enrollment depuis la base de données
        self.enrollment.refresh_from_db()

        # L'enrollment doit être 'complete'
        self.assertEqual(self.enrollment.status, 'complete')
        self.assertIsNotNone(self.enrollment.completed_at)


# ================================================================
# 5. TESTS CERTIFICATS
# ================================================================

class CertificateTests(APITestCase):
    """Tests pour l'obtention et la vérification des certificats."""

    def setUp(self):
        self.apprenant = create_user()
        self.formateur = create_user(email='formateur@test.com', role='formateur')
        self.formation = create_formation(self.formateur)

        # Crée directement un certificat pour les tests
        self.certificate = Certificate.objects.create(
            user=self.apprenant,
            formation=self.formation,
        )

    def test_certificate_list(self):
        """L'apprenant peut voir ses certificats."""
        self.client.force_authenticate(user=self.apprenant)
        url = reverse('elearning:certificate-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_certificate_code_auto_generated(self):
        """Le code du certificat est généré automatiquement au format EFG-XXXXXXXX."""
        self.assertTrue(self.certificate.certificate_code.startswith('EFG-'))
        self.assertEqual(len(self.certificate.certificate_code), 12)  # "EFG-" + 8 chars

    def test_certificate_public_verify(self):
        """N'importe qui peut vérifier un certificat via son code (sans connexion)."""
        url = reverse('elearning:certificate-verify', kwargs={'code': self.certificate.certificate_code})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['certificate_code'], self.certificate.certificate_code)

    def test_certificate_verify_invalid_code(self):
        """La vérification d'un code inexistant retourne 404."""
        url = reverse('elearning:certificate-verify', kwargs={'code': 'EFG-INVALIDE'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_certificate_not_visible_to_other_user(self):
        """Un utilisateur ne voit pas les certificats des autres."""
        autre = create_user(email='autre@test.com')
        self.client.force_authenticate(user=autre)

        url = reverse('elearning:certificate-list')
        response = self.client.get(url)

        # L'autre utilisateur n'a aucun certificat → count = 0
        self.assertEqual(response.data['count'], 0)


# ================================================================
# 6. TESTS PAIEMENTS
# ================================================================

class PaymentTests(APITestCase):
    """Tests pour l'initiation et la confirmation des paiements."""

    def setUp(self):
        self.apprenant = create_user()
        self.admin = create_user(email='admin@test.com', role='admin')
        self.formateur = create_user(email='formateur@test.com', role='formateur')
        self.formation = create_formation(self.formateur)

    def test_create_payment(self):
        """Un apprenant peut initier un paiement pour une formation."""
        self.client.force_authenticate(user=self.apprenant)
        url = reverse('elearning:payment-list')
        response = self.client.post(url, {
            'formation': str(self.formation.id),
            'payment_method': 'mobile_money',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Le paiement est créé avec le statut 'en_attente'
        self.assertEqual(response.data['status'], 'en_attente')
        # Une référence de transaction est générée automatiquement
        self.assertTrue(response.data['transaction_ref'].startswith('EFG-PAY-'))

    def test_cannot_pay_twice_for_same_formation(self):
        """Un apprenant déjà inscrit ne peut pas initier un 2ème paiement."""
        Enrollment.objects.create(user=self.apprenant, formation=self.formation)
        self.client.force_authenticate(user=self.apprenant)

        url = reverse('elearning:payment-list')
        response = self.client.post(url, {
            'formation': str(self.formation.id),
            'payment_method': 'mobile_money',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_confirm_payment(self):
        """Un admin peut confirmer un paiement et créer l'inscription automatiquement."""
        # Crée un paiement en attente manuellement
        import uuid
        payment = Payment.objects.create(
            user=self.apprenant,
            formation=self.formation,
            amount=self.formation.price,
            payment_method='mobile_money',
            transaction_ref=f'EFG-PAY-TEST-{uuid.uuid4().hex[:8]}',
        )

        self.client.force_authenticate(user=self.admin)
        url = reverse('elearning:payment-confirm', kwargs={'payment_id': payment.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Vérifie que l'inscription a bien été créée
        self.assertTrue(
            Enrollment.objects.filter(
                user=self.apprenant,
                formation=self.formation,
            ).exists()
        )

    def test_apprenant_cannot_confirm_payment(self):
        """Un apprenant ne peut pas confirmer un paiement (réservé aux admins)."""
        import uuid
        payment = Payment.objects.create(
            user=self.apprenant,
            formation=self.formation,
            amount=self.formation.price,
            payment_method='mobile_money',
            transaction_ref=f'EFG-PAY-TEST-{uuid.uuid4().hex[:8]}',
        )

        self.client.force_authenticate(user=self.apprenant)
        url = reverse('elearning:payment-confirm', kwargs={'payment_id': payment.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ================================================================
# 7. TESTS ADMINISTRATION
# ================================================================

class AdminTests(APITestCase):
    """Tests pour les endpoints /api/admin/ (réservés aux administrateurs)."""

    def setUp(self):
        self.admin = create_user(email='admin@test.com', role='admin')
        self.apprenant = create_user(email='apprenant@test.com', role='apprenant')
        self.formateur = create_user(email='formateur@test.com', role='formateur')
        self.formation = create_formation(self.formateur)

    def test_admin_stats(self):
        """Un admin peut accéder aux statistiques globales."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('elearning:admin-stats')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Vérifie que tous les champs attendus sont présents
        expected_fields = [
            'total_users', 'total_apprenants', 'total_formateurs',
            'total_formations', 'total_enrollments', 'total_certificates',
            'average_progress', 'completion_rate',
        ]
        for field in expected_fields:
            self.assertIn(field, response.data)

    def test_admin_stats_values(self):
        """Les statistiques reflètent bien les données en base."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('elearning:admin-stats')
        response = self.client.get(url)

        # setUp crée 3 utilisateurs (admin, apprenant, formateur)
        self.assertEqual(response.data['total_users'], 3)
        self.assertEqual(response.data['total_apprenants'], 1)
        self.assertEqual(response.data['total_formateurs'], 1)
        self.assertEqual(response.data['total_formations'], 1)

    def test_apprenant_cannot_access_admin_stats(self):
        """Un apprenant ne peut pas accéder aux statistiques admin."""
        self.client.force_authenticate(user=self.apprenant)
        url = reverse('elearning:admin-stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_list(self):
        """Un admin peut lister tous les utilisateurs."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('elearning:admin-user-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)  # admin + apprenant + formateur

    def test_admin_user_filter_by_role(self):
        """Le filtre ?role= fonctionne sur la liste des utilisateurs."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('elearning:admin-user-list')
        response = self.client.get(url, {'role': 'apprenant'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_admin_formation_list_shows_all(self):
        """Un admin voit TOUTES les formations, y compris les brouillons."""
        # Crée une formation en brouillon (non publiée)
        create_formation(self.formateur, published=False)

        self.client.force_authenticate(user=self.admin)
        url = reverse('elearning:admin-formation-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Doit voir les 2 formations (1 publiée de setUp + 1 brouillon)
        self.assertEqual(response.data['count'], 2)
