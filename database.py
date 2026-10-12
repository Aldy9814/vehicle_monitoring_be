import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app

firebase_config_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

if firebase_config_json:
    cred_dict = json.loads(firebase_config_json)
    cred = credentials.Certificate(cred_dict)
else:
    cred = credentials.Certificate("serviceAccountKey.json")

initialize_app(cred)
db = firestore.client()

employees_ref = db.collection('employees')
vehicles_ref = db.collection('vehicles')
trip_logs_ref = db.collection('trip_logs')

