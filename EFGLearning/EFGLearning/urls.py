"""
URL configuration for EFGLearning project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Panneau d'administration Django (interface web de gestion des données)
    path('admin/', admin.site.urls),

    # Toutes les routes de l'API EFG Learning sont accessibles sous /api/
    # include() délègue la suite de l'URL au fichier ElearningApp/urls.py
    # namespace='elearning' permet d'utiliser : reverse('elearning:register')
    # app_name = 'elearning' est déjà défini dans ElearningApp/urls.py
    # → pas besoin de répéter namespace= ici (Django l'utilise automatiquement)
    path('api/', include('ElearningApp.urls')),
]
