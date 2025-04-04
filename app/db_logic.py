import config
import psycopg2
from psycopg2 import sql
import share as shared
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from room import Base, Room, RoomMedia
import json
from sqlalchemy import text


DATABASE_URL = "postgresql://postgres:Culinh%40102@localhost/my_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(engine)

def insert_room_with_media(message_object, media_list, mid):
    msg_data = {
        "msg_id": getattr(message_object, "msgId", mid),
        "cli_msg_id": getattr(message_object, "cliMsgId", None),
        "msg_type": getattr(message_object, "msgType", None),
        "uid_from": getattr(message_object, "uidFrom", None),
        "id_to": getattr(message_object, "idTo", None),
        "d_name": getattr(message_object, "dName", None),
        "ts": int(getattr(message_object, "ts", 0)),
        "status": getattr(message_object, "status", None),
        "content": message_object.content,
    }

    extracted_info = shared.extract_info_from_gemini(msg_data["content"])
    cleaned_json_str = extracted_info.strip("```json").strip("```")
    extracted_info = json.loads(cleaned_json_str)

    address_lat, address_lon = shared.geocoding_openmaps(extracted_info["address"])

    session = SessionLocal()
    try:
        room = Room(
            msg_id=msg_data["msg_id"],
            cli_msg_id=msg_data.get("cli_msg_id"),
            msg_type=msg_data.get("msg_type"),
            uid_from=msg_data.get("uid_from"),
            id_to=msg_data.get("id_to"),
            d_name=msg_data.get("d_name"),
            ts=msg_data.get("ts"),
            status=msg_data.get("status"),
            content=msg_data["content"],
            address=extracted_info.get("address"),
            price=extracted_info.get("price"),
            room_type=extracted_info.get("room_type"),
            floor=extracted_info.get("floor"),
            elevator=extracted_info.get("elevator"),
            area=extracted_info.get("area"),
            furniture=extracted_info.get("furniture")
            if extracted_info.get("furniture")
            else None,
            services=extracted_info.get("services")
            if extracted_info.get("services")
            else None,
            contract=extracted_info.get("contract")
            if extracted_info.get("contract")
            else None,
            notes=extracted_info.get("notes") if extracted_info.get("notes") else None,
            lon=address_lon,
            lat=address_lat,
        )

        room_media_list = [RoomMedia(href=link["href"]) for link in media_list]
        room.media = room_media_list

        session.add(room)
        session.commit()
        print("Dữ liệu đã được lưu thành công!")
    except Exception as e:
        session.rollback()
        print("Có lỗi xảy ra:", e)
    finally:
        session.close()
        
def delete_duplicate_rooms():
    session = SessionLocal()
    """
    Xoá các bản ghi trùng lặp trong bảng rooms dựa trên các cột:
    content, lat, lon, address. Chỉ giữ lại bản ghi có id nhỏ nhất của mỗi nhóm.
    """
    sql = text("""
        WITH duplicates AS (
            SELECT 
                id,
                ROW_NUMBER() OVER (PARTITION BY content, lat, lon, address ORDER BY id) AS rn
            FROM rooms
        )
        DELETE FROM rooms
        WHERE id IN (
            SELECT id FROM duplicates WHERE rn > 1
        );
    """)
    
    session.execute(sql)
    session.commit()
    print("Xoá các bản ghi trùng lặp thành công!")

def get_count_of_rooms():
    session = SessionLocal()
    return session.query(Room).count()

def connect_db():
    try:
        # Kết nối đến PostgreSQL
        conn = psycopg2.connect(
            dbname=config.db_config["dbname"],
            user=config.db_config["user"],
            password=config.db_config["password"],
            host=config.db_config["host"],
        )
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print("Lỗi kết nối hoặc cập nhật cơ sở dữ liệu:", e)
        return None, None


def create_table_messages(conn, cursor):
    """
    Tạo bảng messages trong PostgreSQL.
    """

    cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    msg_id TEXT NOT NULL,
                    cli_msg_id TEXT,
                    msg_type TEXT,
                    uid_from TEXT,
                    id_to TEXT,
                    d_name TEXT,
                    ts BIGINT,
                    status TEXT,
                    content TEXT,  
                    address TEXT,
                    price INTEGER,
                    room_type TEXT,
                    floor TEXT,
                    elevator BOOLEAN,
                    area TEXT,
                    furniture TEXT[],
                    services JSONB,
                    contract JSONB,
                    notes TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    lon DOUBLE PRECISION,
                    lat DOUBLE PRECISION
                )
            """)

    print("Bảng messages đã được tạo.")


# def insert_message_to_messages_table(conn, cursor, msg_data):
#     extracted_info = shared.extract_info_from_gemini(msg_data["content"])
#     cleaned_json_str = extracted_info.strip("```json").strip("```")
#     extracted_info = json.loads(cleaned_json_str)

#     address_lat, address_lon = shared.geocoding_openmaps(extracted_info["address"])

#     cursor.execute(
#         """
#                 INSERT INTO messages (
#                     msg_id, cli_msg_id, msg_type, uid_from, id_to, d_name, ts, status,
#                     content, address, price, room_type, floor, elevator, area,
#                     furniture, services, contract, notes, lon, lat
#                 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """,
#         (
#             msg_data["msg_id"],
#             msg_data.get("cli_msg_id"),
#             msg_data.get("msg_type"),
#             msg_data.get("uid_from"),
#             msg_data.get("id_to"),
#             msg_data.get("d_name"),
#             msg_data.get("ts"),
#             msg_data.get("status"),
#             msg_data["content"],
#             extracted_info.get("address"),
#             extracted_info.get("price"),
#             extracted_info.get("room_type"),
#             extracted_info.get("floor") if extracted_info.get("floor") else None,
#             extracted_info.get("elevator"),
#             extracted_info.get("area"),
#             extracted_info.get("furniture")
#             if extracted_info.get("furniture")
#             else None,
#             json.dumps(extracted_info.get("services"))
#             if extracted_info.get("services")
#             else None,
#             json.dumps(extracted_info.get("contract"))
#             if extracted_info.get("contract")
#             else None,
#             extracted_info.get("notes") if extracted_info.get("notes") else None,
#             address_lon,
#             address_lat,
#         ),
#     )


def delete_duplicates(order_by="created_at"):
    """
    Xóa dữ liệu trùng lặp, giữ lại bản ghi đầu tiên theo thứ tự sắp xếp.

    :param db_config: Thông tin kết nối database (dict).
    :param table_name: Tên bảng cần kiểm tra (str).
    :param columns: Danh sách cột để kiểm tra trùng lặp (list).
    :param order_by: Cột dùng để xác định bản ghi cũ nhất (str).
    """
    columns = ["uid_from", "address", "price", "room_type", "lat", "lon"]
    table_name = "messages"
    conn = connect_db()[0]
    cursor = connect_db()[1]

    column_str = ", ".join(columns)
    query = f"""
        DELETE FROM {table_name}
        WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY {column_str} ORDER BY {order_by}) AS row_num
                FROM {table_name}
            ) t
            WHERE row_num > 1
        );
    """

    cursor.execute(query)
    conn.commit()

    cursor.close()
    conn.close()
    print("Dữ liệu trùng đã được xóa.")


def count_records(conn, table_name, condition=None, params=None):
    """
    Đếm số lượng bản ghi trong bảng.

    :param conn: Đối tượng kết nối PostgreSQL (psycopg2 connection)
    :param table_name: Tên bảng cần đếm (string)
    :param condition: (Tùy chọn) Điều kiện WHERE (string), ví dụ: "user_id = %s"
    :param params: (Tùy chọn) Tuple chứa giá trị cho điều kiện, ví dụ: (123,)
    :return: Số lượng bản ghi (int)
    """
    # Xây dựng truy vấn SQL an toàn
    query = sql.SQL("SELECT COUNT(*) FROM {table}").format(
        table=sql.Identifier(table_name)
    )
    if condition:
        query = query + sql.SQL(" WHERE ") + sql.SQL(condition)

    with conn.cursor() as cur:
        cur.execute(query, params)
        count = cur.fetchone()[0]

    return count
