# trong file settings.py của bạn

import os
import dj_database_url
from pathlib import Path

# ... (các phần khác)

# Lấy SECRET_KEY từ biến môi trường
SECRET_KEY = os.environ.get('SECRET_KEY')

# Tắt DEBUG trên production
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Thêm tên miền Heroku của bạn vào đây sau khi tạo app
# Ví dụ: ALLOWED_HOSTS = ['ten-app-cua-ban.herokuapp.com', '127.0.0.1']
ALLOWED_HOSTS = []


# Application definition
# ...

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Thêm WhiteNoiseMiddleware ngay sau SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ...

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
# Nơi Django sẽ thu thập tất cả các file tĩnh để whitenoise phục vụ
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ...

# Cấu hình Database
# Mặc định vẫn dùng SQLite cho local
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Nếu có biến DATABASE_URL (do Heroku cung cấp), hãy sử dụng nó
db_from_env = dj_database_url.config(conn_max_age=600, ssl_require=True)
if db_from_env:
    DATABASES['default'].update(db_from_env)

