"""
WSGI config for EFGLearning project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sys

# Ajoute la racine du projet (afroLearning/) au PYTHONPATH
# Même logique que manage.py — nécessaire pour que gunicorn trouve ElearningApp
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EFGLearning.settings')

application = get_wsgi_application()
