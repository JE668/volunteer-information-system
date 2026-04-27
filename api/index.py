# Vercel wrapper for Flask app
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from app import app
app.config['DATABASE'] = os.path.join(_ROOT, 'data', 'zs_scores.db')

# Export as 'app' for Vercel Python runtime
app = app