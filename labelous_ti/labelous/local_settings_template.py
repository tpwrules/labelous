# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

STATIC_ROOT = ''

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'labelous',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
    }
}

# where the images are stored
import pathlib
L_IMAGE_PATH = pathlib.Path(
    "").resolve(strict=True)
# path to the mozjpeg jpegtran tool
L_JPEGTRAN_PATH = pathlib.Path(
    "").resolve(strict=True)
# if True, serve images through nginx X-Accel-Redirect
L_IMAGE_ACCEL = not DEBUG

