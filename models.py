from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class RegistrationLog(Base):
    __tablename__ = "registration_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    reg_user = Column(String(50), index=True)
    realm = Column(String(100))
    token = Column(String(100))
    url = Column(Text)
    expires = Column(Integer)
    network_ip = Column(String(50))
    network_port = Column(Integer)
    network_proto = Column(String(10))
    hostname = Column(String(100))
    log_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class RegistrationHistory(Base):
    __tablename__ = "registration_history"
    
    id = Column(Integer, primary_key=True, index=True)
    reg_user = Column(String(50), index=True)
    status = Column(String(20))  # 'online' or 'offline'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    duration = Column(Integer, nullable=True)  # Duração em segundos, se disponível