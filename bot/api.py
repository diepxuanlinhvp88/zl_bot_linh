from fastapi import FastAPI, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from math import radians, sin, cos, acos
import share as shared
from datetime import datetime
import json
import uuid
import requests

from room import Room, RoomMedia
from db_logic import SessionLocal
from sqlalchemy import func


# Khởi tạo FastAPI app
app = FastAPI()


@app.get("/")
def home():
    return {"message": "Room rental API is running"}


# @app.get("/filter")
# def get_filtered_addresses(
#     address: str = Query(..., description="Địa chỉ tìm kiếm"),
#     min_price: Optional[int] = Query(0, description="Giá tối thiểu"),
#     max_price: Optional[int] = Query(None, description="Giá tối đa"),
#     room_type: Optional[str] = Query(None, description="Loại phòng"),
#     radius: Optional[int] = Query(3, description="Bán kính tìm kiếm (km)"),
# ):
#     """
#     API để lọc tin nhắn theo địa chỉ, khoảng giá, loại phòng và bán kính.
#     """
#     try:
#         results = shared.filter_address(
#             address=address,
#             min_price=min_price,
#             max_price=max_price,
#             room_type=room_type,
#             radius=radius,
#         )
#         return {"status": "success", "data": results}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}


# @app.post("/insert")
# def insert_message(
#     content: str = Body(..., description="Nội dung tin nhắn cần chèn vào DB"),
# ):
#     """
#     API để chèn dữ liệu tin nhắn vào database bằng cách gọi hàm insert_to_db từ share.py.
#     """
#     try:
#         shared.insert_to_db(content)
#         return {"status": "success", "message": "Dữ liệu đã được chèn thành công"}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

class RoomInsertRequest(BaseModel):
    content: str
    media: List[str] = []  # danh sách URL hình ảnh
    
class RoomMediaOut(BaseModel):
    url: str

    class Config:
        orm_mode = True
        from_attributes = True


class RoomOut(BaseModel):
    id: int
    msg_id: str
    cli_msg_id: Optional[str] = None
    msg_type: Optional[str] = None
    uid_from: Optional[str] = None
    id_to: Optional[str] = None
    d_name: Optional[str] = None
    ts: Optional[int] = None
    status: Optional[str] = None
    content: Optional[str] = None
    address: Optional[str] = None
    price: Optional[int] = None
    room_type: Optional[str] = None
    floor: Optional[str] = None
    elevator: Optional[bool] = None
    area: Optional[str] = None
    furniture: Optional[List[str]] = None
    services: Optional[Dict[str, Any]] = None
    contract: Optional[Dict[str, Any]] = None
    notes: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    lat: float
    lon: float
    media: List[str] = []  # Changed to List[str] to store URLs directly
    distance: Optional[float] = None

    class Config:
        orm_mode = True
        from_attributes = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def geocoding_openmaps(address):
    base_url = "https://mapapis.openmap.vn/v1"
    apikey = "tKqXn5rUkQ5QOvZrMdrXa5g279xpOxt7"

    res = requests.get(f"{base_url}/geocode/forward?address={address}&apikey={apikey}")

    if res.status_code == 200:
        data = res.json()
        if data:
            location = data["results"][0]["geometry"]["location"]
            lat = location["lat"]
            lng = location["lng"]
            return lat, lng
        else:
            raise ValueError("Không tìm thấy địa chỉ")
    else:
        raise ValueError("lỗi kết nối đến openmaps")

# Hàm tính khoảng cách giữa hai tọa độ (sử dụng công thức Haversine)
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # bán kính Trái Đất (km)
    # chuyển đổi độ sang radian
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    return R * acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon2 - lon1))


@app.get("/search", response_model=List[RoomOut])
def search_rooms(
    address: str = Query(..., description="Địa chỉ tìm kiếm (bắt buộc)"),
    radius: float = Query(3.0, description="Bán kính tìm kiếm (km)"),
    min_price: Optional[int] = Query(None, description="Giá tối thiểu"),
    max_price: Optional[int] = Query(None, description="Giá tối đa"),
    room_type: Optional[str] = Query(None, description="Loại phòng"),
    db: Session = Depends(get_db),
):
    lat_input, lon_input = geocoding_openmaps(address)

    # Lọc theo các tiêu chí cơ bản (giá, loại phòng) trực tiếp trên DB
    query = db.query(Room)
    if min_price is not None:
        query = query.filter(Room.price >= min_price)
    if max_price is not None:
        query = query.filter(Room.price <= max_price)
    if room_type is not None:
        query = query.filter(func.lower(Room.content).like(f"%{room_type.lower()}%"))

    # Lấy các phòng thỏa mãn các điều kiện trên
    rooms = query.all()

    # Lọc theo bán kính bằng cách tính khoảng cách giữa tọa độ nhập vào và tọa độ của phòng
    filtered_rooms = []
    for room in rooms:
        # Nếu phòng chưa có tọa độ, bỏ qua
        if room.lat is None or room.lon is None:
            continue
        distance = haversine(lat_input, lon_input, room.lat, room.lon)
        if distance <= radius:
            # Chuyển ORM object sang Pydantic model và gán thêm trường distance
            room_out = RoomOut.from_orm(room)
            # Transform media to list of URLs
            room_out.media = [media.url for media in room.media]
            room_out.distance = distance
            filtered_rooms.append(room_out)

    # Sắp xếp danh sách theo khoảng cách (tăng dần)
    filtered_rooms.sort(key=lambda r: r.distance if r.distance is not None else 9999)
    return filtered_rooms


@app.post("/insert", response_model=RoomOut)
def insert_room(request: RoomInsertRequest, db: Session = Depends(get_db)):
    # Tạo một đối tượng giả lập message để xử lý các thuộc tính cần thiết
    class DummyMessage:
        pass
    message_object = DummyMessage()
    message_object.content = request.content
    # Tạo msg_id tự động
    message_object.msgId = str(uuid.uuid4())
    # Các trường khác có thể để None hoặc giá trị mặc định
    message_object.cliMsgId = None
    message_object.msgType = None
    message_object.uidFrom = None
    message_object.idTo = None
    message_object.dName = None
    message_object.ts = None
    message_object.status = None

    mid = message_object.msgId

    try:
        # Trích xuất thông tin từ content
        # Hàm extract_info_from_gemini giả định rằng nội dung được định dạng theo kiểu: 
        # ```json ... ```
        extracted_info = shared.extract_info_from_gemini(message_object.content)
        cleaned_json_str = extracted_info.strip("```json").strip("```")
        extracted_info = json.loads(cleaned_json_str)
        
        # Lấy tọa độ từ địa chỉ (nếu có)
        address = extracted_info.get("address")
        if address:
            address_lat, address_lon = geocoding_openmaps(address)
        else:
            address_lat, address_lon = None, None

        # Tạo đối tượng Room
        room = Room(
            msg_id=message_object.msgId,
            cli_msg_id=message_object.cliMsgId,
            msg_type=message_object.msgType,
            uid_from=message_object.uidFrom,
            id_to=message_object.idTo,
            d_name=message_object.dName,
            ts=message_object.ts,
            status=message_object.status,
            content=message_object.content,
            address=extracted_info.get("address"),
            price=extracted_info.get("price"),
            room_type=extracted_info.get("room_type"),
            floor=extracted_info.get("floor"),
            elevator=extracted_info.get("elevator"),
            area=extracted_info.get("area"),
            furniture=extracted_info.get("furniture") if extracted_info.get("furniture") else None,
            services=extracted_info.get("services") if extracted_info.get("services") else None,
            contract=extracted_info.get("contract") if extracted_info.get("contract") else None,
            notes=extracted_info.get("notes") if extracted_info.get("notes") else None,
            lat=address_lat,
            lon=address_lon,
        )

        # Tạo danh sách RoomMedia từ request.media (giả sử mỗi phần tử là URL ảnh)
        room_media_list = [RoomMedia(href=link) for link in request.media]
        room.media = room_media_list

        db.add(room)
        db.commit()
        db.refresh(room)
        return room

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Có lỗi xảy ra: {e}")