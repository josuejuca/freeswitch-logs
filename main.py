from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import models
import crud
import services
import database
from pydantic import BaseModel

# Criar tabelas
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="FusionPBX Registration Monitor",
             description="API para monitoramento de registros de ramais no FusionPBX",
             version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependência para obter a sessão do banco de dados
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelos Pydantic
class RegistrationLog(BaseModel):
    reg_user: str
    realm: str
    token: str
    url: str
    expires: int
    network_ip: str
    network_port: int
    network_proto: str
    hostname: str
    metadata: str = None
    created_at: datetime = None

    class Config:
        orm_mode = True

class RegistrationHistory(BaseModel):
    reg_user: str
    status: str
    timestamp: datetime
    duration: int = None

    class Config:
        orm_mode = True

class ActiveUsersCount(BaseModel):
    count: int
    timestamp: datetime

# Rotas da API
@app.get("/registrations/", response_model=List[RegistrationLog])
def read_registrations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_registration_logs(db, skip=skip, limit=limit)

@app.get("/history/", response_model=List[RegistrationHistory])
def read_history(reg_user: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_registration_history(db, reg_user=reg_user, skip=skip, limit=limit)

@app.get("/active/", response_model=ActiveUsersCount)
def get_active_users():
    count = services.get_active_users_count()
    return {"count": count, "timestamp": datetime.now()}

@app.get("/current/")
def get_current_registrations():
    return services.get_current_registrations("json")

# Iniciar o agendador quando a aplicação iniciar
@app.on_event("startup")
def startup_event():
    from scheduler import start_scheduler
    start_scheduler()
    
# PT 2
# Adicione estes modelos Pydantic
class UniqueUser(BaseModel):
    reg_user: str
    last_seen: datetime
    realm: str
    hostname: str
    status: str

class UserHistory(BaseModel):
    timestamp: datetime
    status: str
    duration: int = None

# Adicione estas novas rotas
@app.get("/users/unique/", response_model=List[UniqueUser])
def get_unique_registered_users(db: Session = Depends(get_db)):
    """Retorna todos os ramais únicos que já se registraram, com status atual"""
    return crud.get_unique_registered_users(db)

@app.get("/users/{reg_user}/history/", response_model=List[UserHistory])
def get_user_history(reg_user: str, db: Session = Depends(get_db)):
    """Retorna o histórico completo de um ramal específico"""
    return crud.get_user_registration_history(db, reg_user)

@app.get("/users/online/", response_model=List[UniqueUser])
def get_currently_online_users(db: Session = Depends(get_db)):
    """Retorna apenas os ramais que estão online no momento"""
    all_users = crud.get_unique_registered_users(db)
    return [user for user in all_users if user["status"] == "online"]

@app.get("/users/offline/", response_model=List[UniqueUser])
def get_currently_offline_users(db: Session = Depends(get_db)):
    """Retorna apenas os ramais que estão offline no momento"""
    all_users = crud.get_unique_registered_users(db)
    return [user for user in all_users if user["status"] == "offline"]

# PT 3 

@app.get("/users/count/")
def get_users_count(db: Session = Depends(get_db)):
    """Retorna contagens de usuários"""
    total_users = db.query(func.count(distinct(RegistrationLog.reg_user))).scalar()
    online_users = len([u for u in crud.get_unique_registered_users(db) if u["status"] == "online"])
    
    return {
        "total_unique_users": total_users,
        "currently_online": online_users,
        "currently_offline": total_users - online_users,
        "timestamp": datetime.now()
    }

@app.get("/users/{reg_user}/details/")
def get_user_details(reg_user: str, db: Session = Depends(get_db)):
    """Retorna detalhes completos sobre um ramal específico"""
    # Último registro completo
    last_registration = db.query(RegistrationLog).filter(
        RegistrationLog.reg_user == reg_user
    ).order_by(
        RegistrationLog.created_at.desc()
    ).first()
    
    if not last_registration:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Histórico resumido
    history = crud.get_user_registration_history(db, reg_user, limit=10)
    
    # Estatísticas
    total_registrations = db.query(RegistrationLog).filter(
        RegistrationLog.reg_user == reg_user
    ).count()
    
    avg_session_duration = db.query(
        func.avg(RegistrationHistory.duration)
    ).filter(
        RegistrationHistory.reg_user == reg_user,
        RegistrationHistory.duration.isnot(None)
    ).scalar()
    
    return {
        "user": reg_user,
        "last_seen": last_registration.created_at,
        "status": "online" if crud.is_user_online(db, reg_user) else "offline",
        "realm": last_registration.realm,
        "hostname": last_registration.hostname,
        "total_registrations": total_registrations,
        "average_session_duration": avg_session_duration,
        "recent_history": history,
        "last_registration": {
            "network_ip": last_registration.network_ip,
            "network_port": last_registration.network_port,
            "network_proto": last_registration.network_proto,
            "expires": last_registration.expires
        }
    }