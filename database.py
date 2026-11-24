import os
import json
from firebase_admin import credentials, firestore, initialize_app

firebase_config_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

if not firebase_config_json:
    raise ValueError("Environment variable FIREBASE_CREDENTIALS_JSON belum diatur!")

cred_dict = json.loads(firebase_config_json)
cred = credentials.Certificate(cred_dict)

initialize_app(cred)
db = firestore.client()

employees_ref = db.collection('employees')
vehicles_ref = db.collection('vehicles')
trip_logs_ref = db.collection('trip_logs')