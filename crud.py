from sqlalchemy.orm import Session
from models import RegistrationLog, RegistrationHistory

from sqlalchemy import distinct, func

from typing import List, Dict

def create_registration_log(db: Session, registration_data: dict):
    db_registration = RegistrationLog(**registration_data)
    db.add(db_registration)
    db.commit()
    db.refresh(db_registration)
    return db_registration

def get_registration_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(RegistrationLog).offset(skip).limit(limit).all()

def get_registration_history(db: Session, reg_user: str = None, skip: int = 0, limit: int = 100):
    query = db.query(RegistrationHistory)
    if reg_user:
        query = query.filter(RegistrationHistory.reg_user == reg_user)
    return query.order_by(RegistrationHistory.timestamp.desc()).offset(skip).limit(limit).all()

def create_registration_history(db: Session, history_data: dict):
    db_history = RegistrationHistory(**history_data)
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history

def get_unique_registered_users(db: Session) -> List[Dict]:
    """Retorna uma lista de ramais únicos que já se registraram"""
    # Primeiro obtemos os ramais distintos da tabela de logs
    unique_users = db.query(
        distinct(RegistrationLog.reg_user).label("reg_user")
    ).all()
    
    # Agora para cada ramal, obtemos o último registro
    result = []
    for user in unique_users:
        last_registration = db.query(RegistrationLog).filter(
            RegistrationLog.reg_user == user.reg_user
        ).order_by(
            RegistrationLog.created_at.desc()
        ).first()
        
        if last_registration:
            result.append({
                "reg_user": last_registration.reg_user,
                "last_seen": last_registration.created_at,
                "realm": last_registration.realm,
                "hostname": last_registration.hostname,
                "status": "online" if is_user_online(db, last_registration.reg_user) else "offline"
            })
    
    return result

def is_user_online(db: Session, reg_user: str) -> bool:
    """Verifica se um usuário está atualmente online"""
    # Verifica se há um registro recente (últimos 5 minutos) sem um correspondente "offline"
    recent_online = db.query(RegistrationHistory).filter(
        RegistrationHistory.reg_user == reg_user,
        RegistrationHistory.status == "online",
        RegistrationHistory.timestamp > func.datetime('now', '-5 minutes')
    ).first()
    
    if recent_online:
        # Verifica se não há um registro "offline" mais recente
        recent_offline = db.query(RegistrationHistory).filter(
            RegistrationHistory.reg_user == reg_user,
            RegistrationHistory.status == "offline",
            RegistrationHistory.timestamp > recent_online.timestamp
        ).first()
        
        return not recent_offline
    
    return False

def get_user_registration_history(db: Session, reg_user: str, limit: int = 100) -> List[Dict]:
    """Retorna o histórico completo de um ramal específico"""
    history = db.query(RegistrationHistory).filter(
        RegistrationHistory.reg_user == reg_user
    ).order_by(
        RegistrationHistory.timestamp.desc()
    ).limit(limit).all()
    
    return [{
        "timestamp": h.timestamp,
        "status": h.status,
        "duration": h.duration
    } for h in history]