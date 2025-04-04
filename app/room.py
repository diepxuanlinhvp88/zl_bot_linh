from sqlalchemy import (
    create_engine, Column, Integer, String, BigInteger, Text, Boolean,
    TIMESTAMP, ForeignKey, func
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, DOUBLE_PRECISION
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Khởi tạo declarative base
Base = declarative_base()

# Model cho bảng rooms
class Room(Base):
    __tablename__ = 'rooms'
    
    id = Column(Integer, primary_key=True)  # SERIAL PRIMARY KEY
    msg_id = Column(Text, nullable=False)  # NOT NULL
    cli_msg_id = Column(Text)
    msg_type = Column(Text)
    uid_from = Column(Text)
    id_to = Column(Text)
    d_name = Column(Text)
    ts = Column(BigInteger)
    status = Column(Text)
    content = Column(Text)
    address = Column(Text)
    price = Column(Integer)
    room_type = Column(Text)
    floor = Column(Text)
    elevator = Column(Boolean)
    area = Column(Text)
    furniture = Column(ARRAY(Text))
    services = Column(JSONB)
    contract = Column(JSONB)
    notes = Column(ARRAY(Text))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    lat = Column(DOUBLE_PRECISION)
    lon = Column(DOUBLE_PRECISION)
    
    # Thiết lập mối quan hệ với bảng room_media
    media = relationship("RoomMedia", back_populates="room", cascade="all, delete-orphan")

# Model cho bảng room_media
class RoomMedia(Base):
    __tablename__ = 'room_media'
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # SERIAL PRIMARY KEY
    room_id = Column(Integer, ForeignKey('rooms.id',ondelete="CASCADE"), nullable=False)
    href = Column(Text, nullable=False)
    
    # Thiết lập mối quan hệ với bảng rooms
    room = relationship("Room", back_populates="media")

