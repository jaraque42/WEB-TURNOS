import sys
import os

# Añadir la carpeta 'backend' al PYTHONPATH para que las importaciones 'from app...' funcionen
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.append(backend_path)

from app.main import app

