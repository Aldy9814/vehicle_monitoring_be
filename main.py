from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid
import io
import pandas as pd

from database import vehicles_ref, trip_logs_ref, employees_ref
from schemas import CheckOutRequest, CheckInRequest, VehicleCreate, EmployeeCreate, VehicleStatusUpdate, UpdateTimeRequest

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vehicle Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DASHBOARD
@app.get("/dashboard/summary")
def get_dashboard_summary():
    vehicles_docs = vehicles_ref.stream()
    available_vehicles = []
    in_use_vehicles = []
    maintenance = []

    for v_doc in vehicles_docs:
        v_data = v_doc.to_dict()
        vehicle_info = {
            "vehicle_id": v_doc.id,
            "name": v_data.get("name", ""),
            "license_plate": v_data.get("license_plate", ""),
            "current_km": v_data.get("current_km", 0)
        }

        if v_data.get("status") == "Available":
            available_vehicles.append(vehicle_info)
        elif v_data.get("status") == "Maintenance":
            maintenance.append(vehicle_info)
        elif v_data.get("status") == "In Use":
            active_log = trip_logs_ref.where("vehicle_id", "==", v_doc.id).where("log_status", "==", "In Progress").limit(1).get()

            if active_log:
                log_data = active_log[0].to_dict()

                passengers_list = log_data.get("passengers", [])
                passenger_names = ", ".join([p.get("name", "") for p in passengers_list]) if passengers_list else "-"

                vehicle_info["trip_details"] = {
                    "log_id": active_log[0].id,
                    "driver_name": log_data.get("driver_name", ""),
                    "destination": log_data.get("destination", ""),
                    "checkout_time": log_data.get("checkout_time", ""),
                    "start_km": log_data.get("start_km", 0),
                    "passengers_str": passenger_names
                }
            in_use_vehicles.append(vehicle_info)

    return {
        "status": "succeess",
        "data": {
            "available": available_vehicles,
            "in_use": in_use_vehicles,
            "maintenance": maintenance
        }
    }


# MASTER
@app.get("/master/employees/search")
def search_employees(query: str = ""):
    """Mencari karyawan berdasarkan Nama atau NIK"""
    docs = employees_ref.stream()
    results = []

    query_lower = query.lower()

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        name = data.get("name", "").lower()
        nik = data.get("nik", "").lower()

        if query == "" or query_lower in name or query_lower in nik:
            results.append({
                "id": data["id"],
                "nik": data.get("nik", ""),
                "name": data.get("name", ""),
                "department": data.get("department", ""),
                "is_driver": data.get("is_driver", False)
            })

    return {"status": "success", "data": results}

@app.get("/master/vehicles/search")
def search_vehicles(query: str = ""):
    """Mencari kendaraan berdasarkan Nama Mobil atau Plat Nomor"""
    docs = vehicles_ref.stream()
    results = []

    query_lower = query.lower()

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        name = data.get("name","").lower()
        license_plate = data.get("license_plate").lower()

        if query == "" or query_lower in name or query_lower in license_plate:
            results.append({
                "id": data["id"],
                "name": data.get("name", ""),
                "license_plate": data.get("license_plate", ""),
                "status": data.get("status", ""),
                "current_km": data.get("current_km", 0)
            })

    return {
        "status": "success", 
        "data": results
    }

def get_next_id(collection_ref, prefix: str) -> str:
    docs = collection_ref.stream()
    max_num = 0
    for doc in docs:
        doc_id = doc.id
        if doc_id.startswith(prefix):
            try:
                num_part = int(doc_id.split("-")[1])
                if num_part > max_num:
                    max_num = num_part
            except (IndexError, ValueError):
                continue
    return f"{prefix}{max_num + 1:03d}"

@app.post("/master/vehicles")
def add_vehicle(req: VehicleCreate):
    """Add vehicle to database"""
    doc_id = get_next_id(vehicles_ref, "V-")
    new_vehicle = {
        "name": req.name,
        "license_plate": req.license_plate.upper(),
        "status": "Available",
        "current_km": req.current_km
    }
    vehicles_ref.document(doc_id).set(new_vehicle)
    return {
        "status": "succcess", 
        "message": "Kendaraan berhasil ditambahkan", 
        "data": {"id": doc_id, **new_vehicle}
    }

@app.post("/master/employees")
def add_employee(req: EmployeeCreate):
    """Add employee to database"""
    existing = employees_ref.where("nik", "==", req.nik).limit(1).get()
    if existing:
        raise HTTPException(status_code=400, detail="NIK sudah terdaftar di sistem")

    doc_id = get_next_id(employees_ref, "E-")
    new_emp = {
        "nik": req.nik,
        "name": req.name,
        "department": req.department,
    }
    employees_ref.document(doc_id).set(new_emp)
    return {
        "status": "success",
        "message": "Karyawan berhasil ditambahkan",
        "date": {"id": doc_id, **new_emp},
    }

@app.patch("/master/vehicles/{vehicle_id}/status")
def update_vehicle_status(vehicle_id: str, req: VehicleStatusUpdate):
    doc_ref = vehicles_ref.document(vehicle_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Kendaraan tidak ditemukan")

    current_status = doc.to_dict().get("status")

    if current_status == "In Use":
        raise HTTPException(status_code=400, detail="Kendaraan sedang digunakan")

    if req.status not in ["Available", "Maintenance"]:
        raise HTTPException(status_code=400, detail="Status tidak valid")

    doc_ref.update({"status": req.status})
    return {
        "status": "success",
        "message": f"Status Berhasil Diupdate menjadi {req.status}"
    }


@app.post("/transactions/checkout")
def process_checkout(req: CheckOutRequest):
    vehicle_doc = vehicles_ref.document(req.vehicle_id).get()

    if not vehicle_doc.exists:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    vehicles_data = vehicle_doc.to_dict()

    if vehicles_data.get("status") != "Available":
        raise HTTPException(status_code=400, detail="Kendaraan sedang dipakai ata di servis")
    if req.start_km < vehicles_data.get("current_km", 0):
        raise HTTPException(status_code=400, detail="Kilometer berangkat tidak boleh lebih sedikit dari Kilometer saat ini")

    co_time = req.checkout_time if req.checkout_time else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_id = str(uuid.uuid4())[:8]
    new_log = {
        "log_id": log_id,
        "vehicle_id": req.vehicle_id,
        "passengers": [{"name": p.name, "nik": p.nik} for p in req.passengers],  
        "driver_name": req.driver_name,      
        "destination": req.destination,
        "checkout_time": co_time,
        "checkin_time": None,
        "start_km": req.start_km,
        "end_km": None,
        "log_status": "In Progress"
    }

    trip_logs_ref.document(log_id).set(new_log)

    vehicles_ref.document(req.vehicle_id).update({
        "status": "In Use"
    })

    return {"status": "success", "message": "Checkout successful", "data": new_log}

@app.post("/transactions/checkin/{log_id}")
def process_checkin(log_id: str, req: CheckInRequest):
    log_doc = trip_logs_ref.document(log_id).get()

    if not log_doc.exists:
        raise HTTPException(status_code=404, detail="Log perjalanan tidak ditemukan")

    log_data = log_doc.to_dict()

    if log_data.get("log_status") == "Completed":
        raise HTTPException(status_code=400, detail="Kendaraan sudah Check In")
    if req.end_km <= log_data.get("start_km", 0):
        raise HTTPException(status_code=400, detail="Kilometer akhir harus lebih besar daripada Kilometer berangkat")

    trip_logs_ref.document(log_id).update({
        "checkin_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "end_km": req.end_km,
        "log_status": "Completed"
    })

    vehicles_ref.document(log_data["vehicle_id"]).update({
        "status": "Available",
        "current_km": req.end_km
    })

    return{"status": "success", "message": "Check-in successful"}



@app.get("/transactions/history")
def get_trip_history(month: str):
    """Mengambil riwayat perjalanan berdasarkan bulan (Format YYY-MM, misal 2026-09)"""

    vehicles_dict = {doc.id: doc.to_dict() for doc in vehicles_ref.stream()}

    logs_docs = trip_logs_ref.stream()
    results = []

    for doc in logs_docs:
        data = doc.to_dict()
        checkout_time = data.get("checkout_time", "")

        if checkout_time.startswith(month):
            v_id = data.get("vehicle_id", "")
            v_info = vehicles_dict.get(v_id, {})

            passengers = data.get("passengers", [])
            passenger_names = ", ".join([f"{p.get('name')} ({p.get('nik')})" for p in passengers])

            results.append({
                "log_id": doc.id,
                "vehicle_name": v_info.get("name", "Unknown"),
                "license_plate": v_info.get("license_plate", "-"),
                "driver_name": data.get("driver_name", "-"),
                "passengers": passenger_names if passenger_names else "-",
                "destination": data.get("destination", "-"),
                "checkout_time": checkout_time,
                "checkin_time": data.get("checkin_time") or "-",
                "start_km": data.get("start_km", 0),
                "end_km": data.get("end_km") or "-",
                "status": data.get("log_status", "")
            })

    results.sort(key=lambda x: x["checkout_time"], reverse=True)
    return {"status": "success", "data": results}

@app.get("/transactions/history/export")
def export_trip_history(month: str):
    """Download trip history Excel"""
    history_response = get_trip_history(month)
    data = history_response["data"]

    if not data:
        df = pd.DataFrame(columns=["Log ID", "Mobil", "Plat Nomor", "Driver", "Penumpang", "Tujuan", "Waktu Keluar", "Waktu Kembali", "KM Awal", "KM Akhir", "Status"])
    else:
        df = pd.DataFrame(data)
        df.rename(columns={
            "log_id": "Log ID", "vehicle_name": "Mobil", "license_plate": "Plat Nomor",
            "driver_name": "Driver", "passengers": "Penumpang", "destination": "Tujuan",
            "checkout_time": "Waktu Keluar", "checkin_time": "Waktu Kembali",
            "start_km": "KM Awal", "end_km": "KM Akhir", "status": "Status"
        }, inplace=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=f"History_{month}")

    output.seek(0)
    headers = {
        'Content-Disposition': f'attachment; filename="Trip_History_{month}.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.put("/master/employees/{emp_id}")
def update_employee(emp_id: str, req: EmployeeCreate):
    """Edit data employee"""
    doc_ref = employees_ref.document(emp_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Data karyawan tidak ditemukan")

    existing = employees_ref.where("nik", "==", req.nik).stream()
    for doc in existing:
        if doc.id != emp_id:
            raise HTTPException(status_code=400, detail="NIK sudah digunakan oleh karyawan lain")

    doc_ref.update({
        "nik": req.nik,
        "name": req.name,
        "department": req.department
    })
    return {
        "status": "success",
        "message": "Data karyawan berhasil diperbarui"
    }

@app.delete("/master/employees/{emp_id}")
def delete_employee(emp_id: str):
    """delete data karyawan"""
    doc_ref = employees_ref.document(emp_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Data karyawan tidak ditemukan")

    doc_ref.delete()
    return{
        "status": "sucess",
        "message": "Data karyawan berhasil dihapus"
    }

@app.delete("/master/vehicles/{vehicle_id}")
def delete_vehicle(vehicle_id: str):
    """delete data kendaraan"""
    doc_ref = vehicles_ref.document(vehicle_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Data kendaraan tidak ditemukan")

    if doc.to_dict().get("status") == "In Use":
        raise HTTPException(status_code=400, detail="Tidak bisa menghapus kendaraan yang sedang beroperasi")

    doc_ref.delete()
    return{
        "status": "success",
        "message": "Data kendaraan berhasil dihapus"
    }

@app.put("/transactions/logs/{log_id}/time")
def update_checkout_time(log_id: str, req: UpdateTimeRequest):
    doc_ref = trip_logs_ref.document(log_id)
    if not  doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="log perjalanan tidak ditemukan")

    doc_ref.update({"checkout_time": req.checkout_time})
    return {"status": "success", "message": "Waktu Check-out berhasil diperbarui"}

@app.delete("/transactions/checkout/{log_id}")
def cancel_checkout(log_id: str):
    log_ref = trip_logs_ref.document(log_id)
    log_doc = log_ref.get()

    if not log_doc.exists:
        raise HTTPException(status_code=404, detail="Log perjalanan tidak ditemukan")

    log_data = log_doc.to_dict()

    if log_data.get("log_status") == "Completed":
        raise HTTPException(status_code=400, detail="pPrjalanan yang sudah selesai tidak bisa dibatalkan")

    vehicle_id = log_data.get("vehicle_id")
    
    if vehicle_id:
        vehicles_ref.document(vehicle_id).update({"status": "Available"})
    
    log_ref.delete()

    return {
        "status": "success",
        "message": "Check-out berhasil dibatalkan dan dihapus"
    }