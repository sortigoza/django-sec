from django.conf import settings

DATA_DIR = settings.PYSEC_DATA_DIR = getattr(
    settings,
    'PYSEC_DATA_DIR',
    '/tmp/pysec')