from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance'
    
    def ready(self):
        from ml.classifier import load_classifier
        load_classifier()
