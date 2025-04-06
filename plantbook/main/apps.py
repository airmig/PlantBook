from django.apps import AppConfig
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        logger.info("Initializing MainConfig")
        try:
            logger.info(f"Default storage backend: {default_storage.__class__.__name__}")
            logger.info(f"Storage backend configuration: {default_storage.__dict__}")
        except Exception as e:
            logger.error(f"Error initializing storage backend: {str(e)}")
