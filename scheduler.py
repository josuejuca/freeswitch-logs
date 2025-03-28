from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from services import get_current_registrations
from crud import create_registration_log, create_registration_history
from database import SessionLocal
from datetime import datetime
import time

def monitor_registrations():
    """Coleta e armazena os registros atuais"""
    db = SessionLocal()
    try:
        current_registrations = get_current_registrations("json")
        current_users = {reg["reg_user"] for reg in current_registrations}
        
        # Registrar logs completos
        for registration in current_registrations:
            create_registration_log(db, registration)
            
        # Obter últimos registros conhecidos do cache/bd
        last_known_users = set(
            user.reg_user for user in 
            db.query(RegistrationHistory.reg_user)
            .filter(RegistrationHistory.status == "online")
            .distinct()
            .all()
        )
        
        # Registrar mudanças de status
        for user in current_users - last_known_users:
            # Novo usuário online
            create_registration_history(db, {
                "reg_user": user,
                "status": "online",
                "timestamp": datetime.now()
            })
            
        for user in last_known_users - current_users:
            # Usuário ficou offline
            # Primeiro encontramos o último registro online
            last_online = db.query(RegistrationHistory).filter(
                RegistrationHistory.reg_user == user,
                RegistrationHistory.status == "online"
            ).order_by(
                RegistrationHistory.timestamp.desc()
            ).first()
            
            if last_online:
                duration = (datetime.now() - last_online.timestamp).total_seconds()
                create_registration_history(db, {
                    "reg_user": user,
                    "status": "offline",
                    "timestamp": datetime.now(),
                    "duration": duration
                })
            
    except Exception as e:
        print(f"Error in monitoring: {str(e)}")
    finally:
        db.close()

def start_scheduler():
    """Inicia o agendador para coletar dados a cada 5 segundos"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        monitor_registrations,
        trigger=IntervalTrigger(seconds=5),
        id='monitor_registrations',
        name='Monitor FreeSwitch registrations every 5 seconds',
        replace_existing=True
    )
    scheduler.start()
    print("Scheduler started")