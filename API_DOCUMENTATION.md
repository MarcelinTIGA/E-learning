# EFG Learning — Documentation API

**Base URL :** `http://localhost:8000/api/`  
**Authentification :** `Authorization: Bearer <access_token>` (sauf endpoints marqués Public)

---

## Table des matières

1. [Authentification](#1-authentification)
2. [Catalogue](#2-catalogue)
3. [Leçons et progression](#3-leçons-et-progression)
4. [Inscriptions](#4-inscriptions)
5. [Quiz](#5-quiz)
6. [Certificats](#6-certificats)
7. [Paiements](#7-paiements)
8. [Administration](#8-administration)

---

## 1. Authentification

### POST `/api/auth/register/` — Inscription
**Accès :** Public

**Corps de la requête :**
```json
{
  "email": "jean@example.com",
  "first_name": "Jean",
  "last_name": "Dupont",
  "password": "MonMotDePasse123",
  "password_confirm": "MonMotDePasse123"
}
```

**Réponse 201 :**
```json
{
  "email": "jean@example.com",
  "first_name": "Jean",
  "last_name": "Dupont"
}
```

**Erreurs :**
- `400` — email déjà utilisé, mots de passe différents, mot de passe trop faible

---

### POST `/api/auth/token/` — Connexion (obtenir les tokens)
**Accès :** Public

**Corps :**
```json
{
  "email": "jean@example.com",
  "password": "MonMotDePasse123"
}
```

**Réponse 200 :**
```json
{
  "access": "eyJhbGci...",
  "refresh": "eyJhbGci..."
}
```

> `access` expire après **2 heures**. `refresh` expire après **30 jours**.

---

### POST `/api/auth/token/refresh/` — Renouveler le token d'accès
**Accès :** Public

**Corps :**
```json
{
  "refresh": "eyJhbGci..."
}
```

**Réponse 200 :**
```json
{
  "access": "eyJhbGci..."
}
```

---

### GET `/api/auth/profile/` — Voir son profil
**Accès :** Authentifié

**Réponse 200 :**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "jean@example.com",
  "first_name": "Jean",
  "last_name": "Dupont",
  "phone": "+22507000000",
  "bio": "Développeur passionné",
  "avatar_url": "https://...",
  "role": "apprenant",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Valeurs de `role` :** `apprenant` | `formateur` | `admin`

---

### PATCH `/api/auth/profile/` — Modifier son profil
**Accès :** Authentifié

**Corps (champs optionnels) :**
```json
{
  "first_name": "Jean-Pierre",
  "phone": "+22507111111",
  "bio": "Nouvelle bio",
  "avatar_url": "https://..."
}
```

> `email` et `role` ne sont **pas** modifiables depuis cet endpoint.

**Réponse 200 :** profil complet mis à jour (même format que GET)

---

## 2. Catalogue

### GET `/api/categories/` — Liste des catégories
**Accès :** Public

**Réponse 200 :**
```json
{
  "count": 5,
  "results": [
    {
      "id": "uuid...",
      "name": "Développement Web",
      "slug": "developpement-web",
      "description": "...",
      "icon_url": "https://...",
      "order": 1,
      "formations_count": 12
    }
  ]
}
```

---

### GET `/api/formations/` — Catalogue des formations
**Accès :** Public

**Paramètres de filtre (optionnels) :**
| Paramètre | Exemple | Description |
|---|---|---|
| `category` | `?category=developpement-web` | Filtrer par slug de catégorie |
| `level` | `?level=debutant` | `debutant` / `intermediaire` / `avance` |
| `search` | `?search=python` | Recherche dans titre et description |

**Réponse 200 :**
```json
{
  "count": 42,
  "next": "http://localhost:8000/api/formations/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid...",
      "title": "Python pour débutants",
      "description": "...",
      "image_url": "https://...",
      "price": "15000.00",
      "level": "debutant",
      "status": "publiee",
      "formateur": {
        "id": "uuid...",
        "first_name": "Alice",
        "last_name": "Martin",
        "avatar_url": "https://...",
        "bio": "..."
      },
      "category": {
        "id": "uuid...",
        "name": "Développement",
        "slug": "developpement",
        "description": "...",
        "icon_url": "https://...",
        "order": 1,
        "formations_count": 5
      },
      "total_duration_min": 480,
      "modules_count": 6,
      "total_lessons": 24,
      "published_at": "2025-01-10T08:00:00Z"
    }
  ]
}
```

---

### GET `/api/formations/{id}/` — Détail d'une formation
**Accès :** Public (mais `is_enrolled` nécessite un token)

**Réponse 200 :**
```json
{
  "id": "uuid...",
  "title": "Python pour débutants",
  "description": "...",
  "image_url": "https://...",
  "price": "15000.00",
  "level": "debutant",
  "status": "publiee",
  "formateur": { "...": "..." },
  "category": { "...": "..." },
  "total_duration_min": 480,
  "modules_count": 2,
  "total_lessons": 8,
  "published_at": "2025-01-10T08:00:00Z",
  "is_enrolled": true,
  "modules": [
    {
      "id": "uuid...",
      "title": "Module 1 — Introduction",
      "description": "...",
      "order": 0,
      "is_preview": true,
      "lessons_count": 4,
      "lessons": [
        {
          "id": "uuid...",
          "title": "Leçon 1 — Installation",
          "content_type": "video",
          "content_text": null,
          "video_url": "https://...",
          "video_source": "youtube",
          "pdf_url": null,
          "duration_min": 15,
          "order": 0,
          "is_preview": true
        }
      ]
    }
  ]
}
```

**Valeurs de `content_type` :** `video` | `texte` | `pdf`  
**Valeurs de `video_source` :** `youtube` | `vimeo` | `hebergement_propre`

---

### POST `/api/formations/create/` — Créer une formation
**Accès :** Formateur ou Admin

**Corps :**
```json
{
  "title": "Ma formation",
  "description": "Description complète...",
  "image_url": "https://...",
  "price": "5000.00",
  "level": "debutant",
  "status": "brouillon",
  "is_published": false,
  "category": "uuid-de-la-categorie",
  "total_duration_min": 120
}
```

**Valeurs de `status` :** `brouillon` | `en_revue` | `publiee` | `archivee`  
**Réponse 201 :** les champs envoyés en retour

---

### PATCH `/api/formations/{id}/edit/` — Modifier une formation
**Accès :** Formateur (ses formations uniquement) ou Admin (toutes)

**Corps :** mêmes champs que la création (tous optionnels)  
**Réponse 200 :** formation mise à jour

---

## 3. Leçons et progression

### GET `/api/lessons/{id}/` — Contenu d'une leçon
**Accès :** Authentifié

> Crée automatiquement un suivi de progression à la première ouverture.

**Réponse 200 :**
```json
{
  "id": "uuid...",
  "title": "Leçon 1 — Installation",
  "content_type": "video",
  "content_text": null,
  "video_url": "https://youtube.com/...",
  "video_source": "youtube",
  "pdf_url": null,
  "duration_min": 15,
  "order": 0,
  "is_preview": true
}
```

**Erreur 403 :** module non encore débloqué (quiz précédent non réussi)

---

### GET `/api/lessons/{lesson_id}/progress/` — Voir sa progression sur une leçon
**Accès :** Authentifié

**Réponse 200 :**
```json
{
  "id": "uuid...",
  "lesson": "uuid-de-la-lecon",
  "is_completed": false,
  "video_position_sec": 145,
  "started_at": "2025-01-15T10:00:00Z",
  "completed_at": null
}
```

---

### PATCH `/api/lessons/{lesson_id}/progress/` — Sauvegarder la position vidéo
**Accès :** Authentifié

> Appeler toutes les 10 secondes pendant la lecture vidéo.

**Corps :**
```json
{
  "video_position_sec": 145
}
```

**Réponse 200 :** progression mise à jour (même format que GET)

---

### POST `/api/lessons/{lesson_id}/complete/` — Marquer une leçon comme terminée
**Accès :** Authentifié

**Corps :** aucun (requête POST vide)

**Réponse 200 :**
```json
{
  "detail": "Leçon marquée comme terminée.",
  "is_completed": true
}
```

> Déclenche automatiquement le recalcul de la progression globale de l'inscription.  
> Si 100% des leçons terminées + tous les quiz réussis → l'inscription passe en `complete` et un certificat est généré.

---

## 4. Inscriptions

### GET `/api/enrollments/` — Mes formations en cours
**Accès :** Authentifié

**Réponse 200 :**
```json
{
  "count": 3,
  "results": [
    {
      "id": "uuid...",
      "formation": { "...formation complète..." },
      "enrolled_at": "2025-01-10T08:00:00Z",
      "status": "en_cours",
      "progress_percent": "45.00",
      "completed_at": null
    }
  ]
}
```

**Valeurs de `status` :** `en_cours` | `complete` | `abandonne`

---

### GET `/api/enrollments/{id}/` — Détail d'une inscription
**Accès :** Authentifié (ses inscriptions uniquement)

**Réponse 200 :** même format que la liste (un seul objet)

---

## 5. Quiz

### GET `/api/quiz/{id}/` — Afficher un quiz
**Accès :** Authentifié

> Les bonnes réponses (`is_correct`) ne sont **jamais** envoyées à l'apprenant.

**Réponse 200 :**
```json
{
  "id": "uuid...",
  "title": "Quiz Module 1",
  "passing_score": 70,
  "max_attempts": 3,
  "questions_count": 5,
  "questions": [
    {
      "id": "uuid...",
      "question_text": "Quel mot-clé définit une variable en Python ?",
      "question_type": "choix_unique",
      "order": 0,
      "points": 2,
      "options": [
        { "id": "uuid-A", "option_text": "var", "order": 0 },
        { "id": "uuid-B", "option_text": "let", "order": 1 },
        { "id": "uuid-C", "option_text": "Il n'y en a pas", "order": 2 }
      ]
    }
  ]
}
```

**Valeurs de `question_type` :** `choix_unique` | `choix_multiple` | `vrai_faux`  
**`max_attempts = 0`** → tentatives illimitées

---

### POST `/api/quiz/{quiz_id}/start/` — Démarrer une tentative
**Accès :** Authentifié

**Corps :** aucun

**Réponse 201 :**
```json
{
  "id": "uuid-de-la-tentative",
  "quiz": "uuid-du-quiz",
  "score": null,
  "is_passed": false,
  "attempt_number": 1,
  "started_at": "2025-01-15T14:00:00Z",
  "completed_at": null,
  "responses": []
}
```

> Conserver l'`id` de la tentative — il est nécessaire pour soumettre les réponses.

**Erreur 400 :** nombre maximum de tentatives atteint

---

### POST `/api/attempts/{attempt_id}/submit/` — Soumettre les réponses
**Accès :** Authentifié

**Corps :**
```json
{
  "responses": [
    {
      "question": "uuid-question-1",
      "selected_option": "uuid-option-choisie"
    },
    {
      "question": "uuid-question-2",
      "selected_option": "uuid-option-choisie"
    }
  ]
}
```

**Réponse 200 :**
```json
{
  "id": "uuid-de-la-tentative",
  "quiz": "uuid-du-quiz",
  "score": 80.0,
  "is_passed": true,
  "attempt_number": 1,
  "started_at": "2025-01-15T14:00:00Z",
  "completed_at": "2025-01-15T14:12:00Z",
  "responses": [
    {
      "id": "uuid...",
      "question": "uuid-question-1",
      "selected_option": "uuid-option-choisie",
      "is_correct": true
    }
  ]
}
```

> `is_correct` est calculé côté serveur — Flutter ne peut pas l'envoyer.

**Erreurs :**
- `400` — tentative déjà soumise
- `400` — aucune réponse fournie
- `400` — option n'appartenant pas à la question

---

### GET `/api/attempts/{id}/` — Résultat détaillé d'une tentative
**Accès :** Authentifié (ses tentatives uniquement)

**Réponse 200 :** même format que la soumission

---

## 6. Certificats

### GET `/api/certificates/` — Mes certificats
**Accès :** Authentifié

**Réponse 200 :**
```json
{
  "count": 2,
  "results": [
    {
      "id": "uuid...",
      "user": {
        "id": "uuid...",
        "first_name": "Jean",
        "last_name": "Dupont",
        "avatar_url": "https://...",
        "bio": "..."
      },
      "formation_title": "Python pour débutants",
      "certificate_code": "EFG-A1B2C3D4",
      "verification_url": "https://efg.com/verify/EFG-A1B2C3D4",
      "issued_at": "2025-01-20T09:00:00Z"
    }
  ]
}
```

---

### GET `/api/certificates/{id}/` — Détail d'un certificat
**Accès :** Authentifié (ses certificats uniquement)

**Réponse 200 :** même format que la liste (un seul objet)

---

### GET `/api/verify/{code}/` — Vérifier un certificat
**Accès :** Public (pour les employeurs)

Exemple : `GET /api/verify/EFG-A1B2C3D4/`

**Réponse 200 :** certificat complet (même format que la liste)  
**Erreur 404 :** code invalide ou certificat inexistant

---

## 7. Paiements

### GET `/api/payments/` — Mes paiements
**Accès :** Authentifié

**Réponse 200 :**
```json
{
  "count": 1,
  "results": [
    {
      "id": "uuid...",
      "formation": "uuid-de-la-formation",
      "formation_title": "Python pour débutants",
      "amount": "15000.00",
      "currency": "XOF",
      "payment_method": "mobile_money",
      "status": "en_attente",
      "transaction_ref": "EFG-PAY-A1B2C3D4E5F6G7H8",
      "paid_at": null,
      "created_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

**Valeurs de `status` :** `en_attente` | `valide` | `echoue` | `rembourse`  
**Valeurs de `payment_method` :** `mobile_money` | `carte_bancaire` | `virement`

---

### POST `/api/payments/` — Initier un paiement
**Accès :** Authentifié

**Corps :**
```json
{
  "formation": "uuid-de-la-formation",
  "payment_method": "mobile_money"
}
```

> `amount` est automatiquement copié depuis le prix de la formation — Flutter ne peut pas le modifier.

**Réponse 201 :** paiement créé avec `status=en_attente` et `transaction_ref` généré

**Flux après la réponse 201 :**
1. Flutter reçoit le `transaction_ref`
2. Flutter redirige vers la passerelle de paiement (MTN MoMo, Orange Money...)
3. L'apprenant effectue le paiement
4. La passerelle confirme → `POST /api/payments/{id}/confirm/` (webhook)
5. L'inscription est créée → accès au contenu débloqué

**Erreurs :**
- `400` — déjà inscrit à cette formation

---

### POST `/api/payments/{payment_id}/confirm/` — Confirmer un paiement
**Accès :** Admin uniquement

**Corps :** aucun

**Réponse 200 :**
```json
{
  "detail": "Paiement confirmé. Inscription créée.",
  "enrollment_id": "uuid...",
  "created": true
}
```

**Erreur 400 :** paiement déjà confirmé ou non en attente

---

## 8. Administration

> Tous les endpoints `/api/admin/` nécessitent le rôle **admin**.

### GET `/api/admin/stats/` — Statistiques globales
**Accès :** Admin

**Réponse 200 :**
```json
{
  "total_users": 150,
  "total_apprenants": 130,
  "total_formateurs": 18,
  "total_formations": 45,
  "total_enrollments": 320,
  "total_certificates": 87,
  "average_progress": 62.5,
  "completion_rate": 27.2
}
```

---

### GET `/api/admin/users/` — Liste de tous les utilisateurs
**Accès :** Admin

**Paramètres optionnels :**
- `?role=apprenant` | `formateur` | `admin`

**Réponse 200 :**
```json
{
  "count": 150,
  "results": [
    {
      "id": "uuid...",
      "email": "jean@example.com",
      "first_name": "Jean",
      "last_name": "Dupont",
      "phone": "+22507000000",
      "role": "apprenant",
      "is_active": true,
      "auth_provider": "email",
      "created_at": "2025-01-01T00:00:00Z",
      "enrollments_count": 3
    }
  ]
}
```

---

### GET `/api/admin/users/{id}/` — Détail d'un utilisateur
**Accès :** Admin

**Réponse 200 :** même format que la liste (un seul objet)

---

### PATCH `/api/admin/users/{id}/` — Modifier un utilisateur
**Accès :** Admin

**Corps (champs modifiables) :**
```json
{
  "role": "formateur",
  "is_active": false,
  "first_name": "Jean",
  "last_name": "Dupont",
  "phone": "+22507000000"
}
```

> `email` et `auth_provider` sont en lecture seule.

---

### GET `/api/admin/formations/` — Toutes les formations
**Accès :** Admin

> Inclut les brouillons et formations non publiées (contrairement au catalogue public).

**Paramètres optionnels :**
- `?status=brouillon` | `en_revue` | `publiee` | `archivee`

**Réponse 200 :**
```json
{
  "count": 60,
  "results": [
    {
      "id": "uuid...",
      "title": "Python pour débutants",
      "description": "...",
      "image_url": "https://...",
      "price": "15000.00",
      "level": "debutant",
      "status": "brouillon",
      "is_published": false,
      "formateur": { "...": "..." },
      "formateur_id": null,
      "category": "uuid...",
      "total_duration_min": 480,
      "modules_count": 6,
      "total_lessons": 24,
      "enrollments_count": 0,
      "published_at": null,
      "created_at": "2025-01-05T09:00:00Z"
    }
  ]
}
```

---

### GET `/api/admin/formations/{id}/` — Détail d'une formation (admin)
**Accès :** Admin

**Réponse 200 :** même format que la liste (un seul objet)

---

### PATCH `/api/admin/formations/{id}/` — Modifier n'importe quelle formation
**Accès :** Admin

**Corps (tous optionnels) :**
```json
{
  "status": "publiee",
  "is_published": true,
  "formateur_id": "uuid-du-nouveau-formateur"
}
```

> `formateur_id` (UUID en écriture) permet de réassigner le formateur.  
> La réponse renvoie `formateur` (objet complet) mais pas `formateur_id`.

---

## Codes d'erreur courants

| Code | Signification |
|---|---|
| `400` | Données invalides (voir le corps de l'erreur) |
| `401` | Token manquant ou expiré |
| `403` | Permission insuffisante (mauvais rôle ou contenu verrouillé) |
| `404` | Ressource introuvable |

**Format d'erreur standard :**
```json
{
  "detail": "Message d'erreur explicite."
}
```

**Format d'erreur de validation :**
```json
{
  "email": ["Un utilisateur avec cet email existe déjà."],
  "password": ["Les mots de passe ne correspondent pas."]
}
```

---

## Pagination

Tous les endpoints de liste sont paginés. Format de réponse :
```json
{
  "count": 42,
  "next": "http://localhost:8000/api/formations/?page=2",
  "previous": null,
  "results": [ "..." ]
}
```

Taille de page : **20 éléments** par défaut. Naviguer avec `?page=2`, `?page=3`...
