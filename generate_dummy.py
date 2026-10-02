from database import employees_ref, vehicles_ref

def generate_data():
 
    employees = [
        {"id": "E-001", "nik": "27001", "name": "Aldyansyah Priyo Utomo", "department": "IT", "is_driver": False},
        {"id": "E-002", "nik": "27002", "name": "Rina Wijaya", "department": "Marketing", "is_driver": False},
        {"id": "E-003", "nik": "27003", "name": "Pak Anton", "department": "Operations", "is_driver": True}
    ]

    vehicles = [
        {"id": "V-001", "name": "Toyota Avanza", "license_plate": "N 1234 AB", "status": "Available", "current_km": 15000},
        {"id": "V-002", "name": "Toyota Innova", "license_plate": "L 9988 XYZ", "status": "Available", "current_km": 32000},
        {"id": "V-003", "name": "Daihatsu GranMax", "license_plate": "N 5555 CD", "status": "In Maintenance", "current_km": 80000}
    ]

    print("Creating employee data...")
    for emp in employees:
        doc_id = emp.pop("id")
        employees_ref.document(doc_id).set(emp)
        print(f"  -> Employee {emp['name']} successfully added.")

    print("\nCreating vehivle data...")
    for veh in vehicles:
        doc_id = veh.pop("id")
        vehicles_ref.document(doc_id).set(veh)
        print(f"  -> Vehicle {veh['name']} successfully added.")

    print("\nAll dummy data has been generated in the Firestore")

if __name__ == "__main__":
    generate_data()