import os
from dotenv import load_dotenv

load_dotenv()                         # читаем .env

import firebase_admin
from firebase_admin import credentials, db

def init_firebase():
    """Однократная инициализация Firebase Admin SDK."""
    if firebase_admin._apps:
        return db                     # уже инициализировано

    cred_path = os.getenv("FIREBASE_CREDENTIALS")
    db_url   = os.getenv("FIREBASE_DB_URL")
    

    if not cred_path or not db_url:
        raise RuntimeError("Заполните FIREBASE_CREDENTIALS и FIREBASE_DB_URL в .env")

    cred = credentials.Certificate(cred_path)
    
    firebase_admin.initialize_app(cred, {"databaseURL": db_url})
    return db
