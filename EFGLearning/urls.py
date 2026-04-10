"""
EFG E-Learning — URLs principales (fichier chargé par manage.py)

NOTE ARCHITECTURE :
Ce fichier est le ROOT_URLCONF utilisé quand manage.py est lancé
depuis la racine du projet. Son contenu est identique au fichier
EFGLearning/EFGLearning/urls.py.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Panneau d'administration Django
    path('admin/', admin.site.urls),

    # Toutes les routes de l'API EFG Learning sous /api/
    # app_name = 'elearning' est défini dans ElearningApp/urls.py
    path('api/', include('ElearningApp.urls')),
]
