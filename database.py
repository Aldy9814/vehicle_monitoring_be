import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

employees_ref = db.collection('employees')
vehicles_ref = db.collection('vehicles')
trip_logs_ref = db.collection('trip_logs')

