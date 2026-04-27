# Vercel wrapper - exports the Flask app as 'application'
import os
import sys

# Ensure correct path for data directory
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app import app as application
application.config['DATABASE'] = os.path.join(_ROOT, 'data', 'zs_scores.db')