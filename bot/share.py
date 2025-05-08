from google import genai
from datetime import datetime, timezone, timedelta
import requests
import math
import psycopg2
import config
from tqdm import tqdm
import json
import time

client = genai.Client(api_key="AIzaSyBRvzfm-")


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


def extract_info_from_gemini(content):
    prompt = f"""Extract the rental room information from the following text.
                Output a valid JSON object that contains exactly the following fields:
                - floor,
                - elevator (a boolean, true or false),
                - area,
                - furniture (an array of strings),
                - services (a JSON object),
                - contract (a JSON object),
                - notes (an array of strings).

                Do not include any additional text or explanation. Output only the JSON.

                Text:
                {content}
                """

    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    return response.text


def convert_to_vietnamtime(ts):
    return datetime.fromtimestamp(ts / 1000, timezone.utc).astimezone(
        timezone(timedelta(hours=7))
    )


def filter_price_type(min_price=None, max_price=None, room_type=None):
    try:
        conn = connect_db()[0]
    except Exception as e:
        print("Kết nối PostgreSQL thất bại:", e)
        return []

    cur = connect_db()[1]

    # Xây dựng truy vấn SQL với các điều kiện lọc
    query = "SELECT content, lat, lon from messages"
    filters = []
    params = []

    if min_price is not None:
        filters.append("price >= %s")
        params.append(min_price)
    if max_price is not None:
        filters.append("price <= %s")
        params.append(max_price)
    if room_type:
        filters.append("room_type ILIKE %s")
        params.append(f"%{room_type}%")

    if filters:
        query += " WHERE " + " AND ".join(filters)

    try:
        cur.execute(query, params)
        rows = cur.fetchall()
    except Exception as e:
        print("Lỗi khi truy vấn:", e)
        rows = []

    rooms = []
    for row in rows:
        rooms.append(
            {
                "content": row[0],
                "lat": row[1],
                "lon": row[2],
            }
        )

    cur.close()
    conn.close()
    return rooms


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Tính khoảng cách giữa 2 điểm (lat1, lon1) và (lat2, lon2) theo công thức Haversine.
    Đầu ra là khoảng cách tính theo km.
    """
    # Chuyển đổi độ sang radian
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    R = 6371  # bán kính Trái Đất tính theo km
    return R * c


def geocoding_goong(address):
    url = "https://rsapi.goong.io/Geocode"
    params = {
        "address": f"{address}",
        "api_key": "Y7oJg8gUpTS9Jj91QqjNhdgJYSx6snDTFHjW8xGq",
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data:
            location = data["results"][0]["geometry"]["location"]
            lat = location["lat"]
            lon = location["lng"]
            return lat, lon

    else:
        raise ValueError("Không tìm thấy địa chỉ")


def geocoding_openmaps(address):
    base_url = "https://mapapis.openmap.vn/v1"
    apikey = "dOVlwo9Ti1GAQKUppioXoyQ"

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


def filter_address(address, min_price=0, max_price=None, room_type=None, radius=3):
    try:
        lat, lon = geocoding_openmaps(address)
        all_addresses = filter_price_type(
            min_price=min_price, max_price=max_price, room_type=room_type
        )
        # print(all_addresses)
        res_address = []

        for item in tqdm(all_addresses):
            if haversine_distance(lat, lon, item["lat"], item["lon"]) <= radius:
                res_address.append(item["content"])
            # if get_distance_matrix(lat, lon, item["lat"], item["lon"]) <= radius:
            #     res_address.append(item["content"])

        return res_address
    except Exception as e:
        raise ValueError(str(e))


def generate_unique_msg_id(conn):
    """
    Sinh msg_id theo dạng số 13 chữ số dựa trên thời gian (mili giây),
    kiểm tra đảm bảo không bị trùng trong bảng messages.
    """
    cur = conn.cursor()
    while True:
        msg_id = str(int(time.time() * 1000))
        cur.execute("SELECT 1 FROM messages WHERE msg_id = %s", (msg_id,))
        if not cur.fetchone():
            break
        # Nếu trùng, chờ một chút (0.001 giây) rồi thử lại
        time.sleep(0.001)
    cur.close()
    return msg_id


def insert_to_db(content):
    try:
        conn = connect_db()[0]
        cur = connect_db()[1]
        print("kết nôi db thành công ")
    except Exception as e:
        print("Kết nối PostgreSQL thất bại:", e)
        return []

    msg_id = generate_unique_msg_id(conn)

    try:
        extracted_info = extract_info_from_gemini(content)
        cleaned_json_str = extracted_info.strip("```json").strip("```")
        extracted_info = json.loads(cleaned_json_str)
    except Exception as e:
        print("Lỗi khi trích xuất thông tin từ gemini:", e)

    try:
        address_lat, address_lon = geocoding_openmaps(extracted_info["address"])

    except Exception as e:
        print("Lỗi khi chuyển địa chỉ sang tọa độ:", e)

    try:
        query = """
        INSERT INTO messages (msg_id,
            content, address, price, room_type, floor, elevator, area,
            furniture, services, contract, notes, lon, lat
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            msg_id,
            content,
            extracted_info.get("address"),
            extracted_info.get("price"),
            extracted_info.get("room_type"),
            extracted_info.get("floor") if extracted_info.get("floor") else None,
            extracted_info.get("elevator"),
            extracted_info.get("area"),
            extracted_info.get("furniture")
            if extracted_info.get("furniture")
            else None,
            json.dumps(extracted_info.get("services"))
            if extracted_info.get("services")
            else None,
            json.dumps(extracted_info.get("contract"))
            if extracted_info.get("contract")
            else None,
            extracted_info.get("notes") if extracted_info.get("notes") else None,
            address_lon,
            address_lat,
        )
        cur.execute(query, params)
        print("Chèn dữ liệu thành công")
    except Exception as e:
        print("Lỗi khi chèn dữ liệu vào PostgreSQL:", e)

    conn.commit()

    cur.close()
    conn.close()
