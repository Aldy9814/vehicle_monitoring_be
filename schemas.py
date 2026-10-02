from pydantic import BaseModel
from typing import List, Optional

class Passenger(BaseModel):
    name: str
    nik: str

class CheckOutRequest(BaseModel):
    vehicle_id: str
    passengers: List[Passenger]
    driver_name: str
    destination: str
    start_km: int
    checkout_time: Optional[str] = None

class CheckInRequest(BaseModel):
    end_km: int

class VehicleCreate(BaseModel):
    name: str
    license_plate: str
    current_km: int

class EmployeeCreate(BaseModel):
    nik: str
    name: str
    department: str

class VehicleStatusUpdate(BaseModel):
    status: str

class UpdateTimeRequest(BaseModel):
    checkout_time: str
    