from .auth import auth_bp
from .diagnosis import diagnosis_bp
from .files import files_bp
from .models import models_bp

__all__ = ['auth_bp', 'diagnosis_bp', 'files_bp', 'models_bp']