import uuid
import json
import structlog
from typing import Dict
from app.domain.appointment import Appointment
from app.voice.connection_manager import manager

logger = structlog.get_logger(__name__)

# In-memory mock database for appointments
db_appointments: Dict[str, Appointment] = {}

async def _notify_frontend(session_id: str, appointment: Appointment):
    """Sends the UI state to the frontend."""
    # Convert to dict and handle datetime
    data = appointment.model_dump()
    data["created_at"] = data["created_at"].isoformat()
    
    payload = {
        "event_type": "appointment_state",
        "data": data
    }
    await manager.send_personal_message(json.dumps(payload), session_id)

async def book_appointment(
    session_id: str,
    patient_name: str,
    date: str,
    time: str,
    patient_age: int = None,
    patient_phone: str = None,
    symptoms: str = None
) -> str:
    """
    Books a new medical appointment.
    """
    appt_id = f"appt_{uuid.uuid4().hex[:8]}"
    appt = Appointment(
        id=appt_id,
        session_id=session_id,
        patient_name=patient_name,
        patient_age=patient_age,
        patient_phone=patient_phone,
        symptoms=symptoms,
        date=date,
        time=time,
        status="booked"
    )
    
    db_appointments[appt_id] = appt
    logger.info("Appointment booked", appt_id=appt_id)
    
    await _notify_frontend(session_id, appt)
    return f"Successfully booked appointment for {patient_name} on {date} at {time}. Appointment ID: {appt_id}"

async def cancel_appointment(session_id: str, appointment_id: str) -> str:
    """
    Cancels an existing appointment.
    """
    if appointment_id not in db_appointments:
        return f"Error: Appointment {appointment_id} not found."
    
    appt = db_appointments[appointment_id]
    appt.status = "canceled"
    logger.info("Appointment canceled", appt_id=appointment_id)
    
    await _notify_frontend(session_id, appt)
    return f"Successfully canceled appointment {appointment_id}."

async def reschedule_appointment(session_id: str, appointment_id: str, new_date: str, new_time: str) -> str:
    """
    Reschedules an existing appointment to a new date and time.
    """
    if appointment_id not in db_appointments:
        return f"Error: Appointment {appointment_id} not found."
        
    appt = db_appointments[appointment_id]
    appt.date = new_date
    appt.time = new_time
    appt.status = "rescheduled"
    logger.info("Appointment rescheduled", appt_id=appointment_id)
    
    await _notify_frontend(session_id, appt)
    return f"Successfully rescheduled appointment {appointment_id} to {new_date} at {new_time}."
