"""
Django settings for APbackend project.
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['apbackend.herokuapp.com']

# Application definition

INSTALLED_APPS = [
    'social_django',
    'channels',
    'myapp',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'APbackend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'APbackend.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfile')

# APbackend/settings.py
# Channels
ASGI_APPLICATION = 'APbackend.routing.application'

redis_host = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379')
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [redis_host],
        },
    },
}

# for auth0.com authentication
SOCIAL_AUTH_TRAILING_SLASH = False  # Remove trailing slash from routes
SOCIAL_AUTH_AUTH0_DOMAIN = os.environ.get('SOCIAL_AUTH_AUTH0_DOMAIN')
SOCIAL_AUTH_AUTH0_KEY = os.environ.get('SOCIAL_AUTH_AUTH0_KEY')
SOCIAL_AUTH_AUTH0_SECRET = os.environ.get('SOCIAL_AUTH_AUTH0_SECRET')

# auth scope, if I need more scope, add them here.
SOCIAL_AUTH_AUTH0_SCOPE = [
    'openid',
    'profile',
    'email'
]

AUTHENTICATION_BACKENDS = {
    'myapp.auth0backend.Auth0',
    'django.contrib.auth.backends.ModelBackend'
}

LOGIN_URL = '/login/auth0'
LOGIN_REDIRECT_URL = '/dashboard' # sent outside, then outside uses this URL, but any url that doesnt exist
# gets redirected to /dashboard anyway, instead of broken page

SITE_ID = 1