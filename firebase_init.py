import os
import json
import firebase_admin
from firebase_admin import credentials, db

def init_firebase():
    """Однократная инициализация Firebase Admin SDK."""
    if firebase_admin._apps:
        return db

    cred_json = os.environ.get("FIREBASE_CREDENTIALS")
    db_url = os.environ.get("FIREBASE_DB_URL")

    if not cred_json or not db_url:
        raise RuntimeError("Заполните FIREBASE_CREDENTIALS и FIREBASE_DB_URL в Environment")

    # Чтение JSON из строки
    cred = credentials.Certificate(json.loads(cred_json))
    firebase_admin.initialize_app(cred, {'databaseURL': db_url})
    return db
