# quick_firebase_test.py
from firebase_init import init_firebase
import pprint, json

tariffs = init_firebase().reference("/tariffs").get() or {}
print("Ключи тарифов:", list(tariffs))
pprint.pprint(tariffs, width=120)
