# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Aperçu du projet

**afroLearning** (EFG Learning) est une plateforme e-learning de style Udemy, développée avec Django (backend REST API) et Flutter (application mobile). Le backend est **entièrement fonctionnel** avec 45 tests automatiques qui passent.

Stack technique :
- Python 3.13 + Django 6.0.4
- Django REST Framework + djangorestframework-simplejwt (JWT)
- Base de données : SQLite en développement, PostgreSQL en production
- Frontend : Flutter (consomme l'API via HTTP/JSON)

## Commandes courantes

Toutes les commandes s'exécutent depuis la racine du projet. Activer l'environnement virtuel d'abord :

```bash
source env/bin/activate
```

```bash
# Lancer le serveur de développement
python EFGLearning/manage.py runserver

# Appliquer les migrations
python EFGLearning/manage.py migrate

# Créer de nouvelles migrations après modification des modèles
python EFGLearning/manage.py makemigrations

# Créer un superuser pour accéder à /admin/
python EFGLearning/manage.py createsuperuser

# Lancer tous les tests
python EFGLearning/manage.py test ElearningApp

# Lancer une seule classe ou méthode de test
python EFGLearning/manage.py test ElearningApp.tests.AuthTests
python EFGLearning/manage.py test ElearningApp.tests.AuthTests.test_login_success

# Shell Django (pour tester des requêtes en base)
python EFGLearning/manage.py shell
```

## Architecture et structure

Le projet a une structure imbriquée — attention à ne pas confondre les deux niveaux :

```
afroLearning/                    ← racine du dépôt git
  env/                           ← environnement virtuel Python (ne pas modifier)
  requirements.txt               ← dépendances Python
  EFGLearning/                   ← répertoire de travail Django (contient manage.py)
    manage.py                    ← point d'entrée des commandes Django
    .env                         ← variables d'environnement (SECRET_KEY, DATABASE_URL...)
    db.sqlite3                   ← base de données SQLite (développement)
    settings.py                  ← settings actif (chargé par manage.py via sys.path)
    urls.py                      ← URLs racine actives (chargées par manage.py)
    EFGLearning/                 ← paquet Python Django (settings, urls, wsgi, asgi)
      settings.py                ← copie des settings (même contenu que EFGLearning/settings.py)
      urls.py                    ← copie des URLs racine
  ElearningApp/                  ← application Django principale
    models.py                    ← 14 modèles (User, Formation, Module, Lesson, Quiz...)
    serializers.py               ← 15+ serializers DRF
    views.py                     ← 20 vues API
    urls.py                      ← 22 routes (préfixe /api/)
    admin.py                     ← configuration du panneau /admin/
    tests.py                     ← 45 tests automatiques
    migrations/                  ← migrations Django (0001_initial.py)
```

**Points architecturaux critiques :**

- **Double settings.py** : `manage.py` ajoute la racine au `sys.path`, donc Python charge `EFGLearning/settings.py` (le fichier externe). Les deux fichiers `settings.py` doivent rester identiques en contenu. Toujours modifier les deux si on change la config.
- **Double urls.py** : même principe — `EFGLearning/urls.py` et `EFGLearning/EFGLearning/urls.py` doivent rester synchronisés.
- **AUTH_USER_MODEL** : `ElearningApp.User` — modèle utilisateur personnalisé avec connexion par email (pas username). Jamais utiliser `auth.User` directement.
- **Namespace URLs** : `app_name = 'elearning'` dans `ElearningApp/urls.py`. Utiliser `reverse('elearning:register')` dans les tests. Ne pas passer `namespace=` dans `include()` du urls.py racine (conflit).
- **sys.path** dans `manage.py` : `sys.path.insert(0, ...)` ajouté manuellement pour que Django trouve `ElearningApp` depuis le sous-répertoire `EFGLearning/`.

## Modèles de données (14 tables)

Hiérarchie pédagogique : `Formation → Module → Lesson → Quiz → Question → AnswerOption`

Suivi de progression : `Enrollment → LessonProgress`, `QuizAttempt → QuizResponse → Certificate`

Flux de paiement : `Payment → (confirmation) → Enrollment`

Logique métier importante dans les modèles :
- `Enrollment.update_progress()` — recalcule le % de progression, passe en `COMPLETE` si 100% leçons + tous quiz réussis
- `LessonProgress.mark_completed()` — marque une leçon terminée et déclenche `update_progress()`
- `QuizAttempt.calculate_score()` — calcule le score, met à jour `is_passed`, déclenche `update_progress()`
- `QuizResponse.save()` — correction automatique côté serveur (anti-triche : recalcule `is_correct` depuis `selected_option.is_correct`)
- `Certificate.save()` — génère automatiquement le code `EFG-XXXXXXXX` et l'URL de vérification

## API — Endpoints principaux

Tous les endpoints sont préfixés par `/api/`. Authentification via header `Authorization: Bearer <token>`.

| Groupe | Endpoints clés |
|---|---|
| Auth | `POST /api/auth/register/`, `POST /api/auth/token/`, `GET/PATCH /api/auth/profile/` |
| Catalogue | `GET /api/categories/`, `GET /api/formations/`, `GET /api/formations/{id}/` |
| Leçons | `GET /api/lessons/{id}/`, `PATCH /api/lessons/{id}/progress/`, `POST /api/lessons/{id}/complete/` |
| Inscriptions | `GET /api/enrollments/`, `GET /api/enrollments/{id}/` |
| Quiz | `GET /api/quiz/{id}/`, `POST /api/quiz/{id}/start/`, `POST /api/attempts/{id}/submit/` |
| Certificats | `GET /api/certificates/`, `GET /api/verify/{code}/` (public) |
| Paiements | `GET/POST /api/payments/`, `POST /api/payments/{id}/confirm/` |
| Admin | `GET /api/admin/stats/`, `GET /api/admin/users/`, `GET /api/admin/formations/` |

Permissions :
- `AllowAny` : register, token, catalogue, vérification certificat
- `IsAuthenticated` : tout le reste
- `IsFormateur` : créer/modifier formations
- `IsAdmin` : endpoints `/api/admin/`, confirmation paiements

## Sécurité — Points importants

- Les bonnes réponses des quiz (`is_correct`) ne sont jamais envoyées aux apprenants (deux serializers séparés : `AnswerOptionSerializer` vs `AnswerOptionAdminSerializer`)
- La correction des quiz se fait côté serveur (`QuizResponse.save()`), Flutter ne peut pas envoyer `is_correct=True`
- `amount` du paiement est toujours copié depuis `formation.price` côté serveur — Flutter ne peut pas manipuler le prix
- Déverrouillage progressif des modules vérifié dans `views.py` via `_can_access_module(user, module)`

## Fichier .env (EFGLearning/.env)

```
SECRET_KEY=...
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```
