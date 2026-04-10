# Configuration Gunicorn pour la production EFG Learning
#
# Lancement depuis la racine du projet (afroLearning/) :
#   gunicorn --config gunicorn.conf.py EFGLearning.wsgi:application
#
# Ou sans ce fichier (valeurs par défaut) :
#   gunicorn EFGLearning.wsgi:application --bind 0.0.0.0:8000 --workers 3

# Adresse et port d'écoute
bind = "0.0.0.0:8000"

# Nombre de processus workers
# Règle habituelle : 2 × nb_cœurs + 1
# Ex: serveur 2 cœurs → 5 workers
workers = 3

# Type de worker : "sync" (défaut) convient pour une API Django standard
# Utiliser "gthread" si les vues font des appels réseau lents (I/O bound)
worker_class = "sync"

# Délai maximum d'une requête avant d'être considérée comme bloquée
timeout = 120

# Journalisation dans la sortie standard (capturée par systemd/Docker/Render)
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Rechargement automatique en cas de changement de code (développement uniquement)
# reload = True
