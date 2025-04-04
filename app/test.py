import requests
import psycopg2
import config
import os
import share as shared
import db_logic 
from zlapi.Async import ZaloAPI
from zlapi.models import *

def get_coordinates(address):
    # Gửi yêu cầu đến Nominatim API
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}
    headers = {
        "User-Agent": "MyApp (diepxuanlinhvp88@egmail.com)"
    }  # Thay bằng thông tin của bạn

    response = requests.get(url, params=params, headers=headers).json()

    if response:
        lat = float(response[0]["lat"])
        lon = float(response[0]["lon"])
        return lat, lon
    else:
        raise ValueError("Không tìm thấy địa chỉ")


def get_coordinates_google(api_key, address):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    response = requests.get(url).json()
    if response["status"] == "OK":
        location = response["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]
    else:
        raise ValueError("Không tìm thấy địa chỉ")


def get_coordinates_mapbox(address):
    access_token = "pk.eyJ1IjoiZGllcHh1YW5saW5oIiwiYSI6ImNtNzlicWFyMTAzcjUya3B6emlndnl5aWYifQ.aXGKJJvspqirGYZn0op3Uw"
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json?access_token={access_token}"
    response = requests.get(url).json()
    if response["features"]:
        lon, lat = response["features"][0]["center"]
        return lat, lon
    else:
        raise ValueError("Không tìm thấy địa chỉ")


def get_walking_distance(origin_lat, origin_lon, dest_lat, dest_lon):
    # Định dạng URL cho OSRM (chế độ đi bộ: 'foot')
    url = f"http://router.project-osrm.org/route/v1/foot/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"

    response = requests.get(url).json()

    if response.get("code") == "Ok":
        distance = response["routes"][0]["distance"] / 1000  # Chuyển sang km

        return distance
    else:
        raise ValueError("Không thể tính toán tuyến đường")


def test_api_filter():
    # Địa chỉ của API FastAPI
    api_url = "http://103.211.201.85:8080/filter"

    # Các tham số cần truyền vào query string
    params = {
        "address": "ngõ 59 văn tiến dũng",
        "min_price": 0,
        "max_price": 4000000,
        "radius": 10,
    }

    # Gửi request GET với các tham số
    response = requests.get(api_url, params=params)

    # Kiểm tra kết quả trả về từ API
    if response.status_code == 200:
        print("Kết quả trả về:", response.json())  # Hiển thị kết quả trả về từ API
        data = response.json().get("data")
        cnt = 0
        if data:
            for item in data:
                cnt += 1
                print(cnt, item, "__________________________\n")
            print(f"Tìm thấy {cnt} phòng thỏa mãn")
        else:
            print("Không tìm thấy phòng")
    else:
        print(f"Lỗi khi gửi request. Mã lỗi: {response.status_code}")


def geocoding(address):
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


def get_distance_matrix(origin_lat, origin_lng, dest_lat, dest_lng):
    url = "https://rsapi.goong.io/DistanceMatrix"
    params = {
        "origins": f"{origin_lat},{origin_lng}",
        "destinations": f"{dest_lat},{dest_lng}",
        "api_key": "Y7oJg8gUpTS9Jj91QqjNhdgJYSx6snDTFHjW8xGq",
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        distance = data["rows"][0]["elements"][0]["distance"]["value"]
        return distance / 1000
    else:
        print("Lỗi:", response.status_code, response.text)
        return None


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


def update_db_coordinates(db_config):
    """
    Kết nối đến PostgreSQL, lấy danh sách các bản ghi từ bảng rooms (bao gồm id, address),
    gọi API để lấy tọa độ và cập nhật lại trường lat, lon.
    """
    try:
        # # Kết nối đến PostgreSQL
        # conn = psycopg2.connect(
        #     dbname=db_config["dbname"],
        #     user=db_config["user"],
        #     password=db_config["password"],
        #     host=db_config["host"],
        # )
        # cursor = conn.cursor()
        conn = connect_db()[0]
        cursor = connect_db()[1]

        cursor.execute("SELECT msg_id, address FROM messages")
        rows = cursor.fetchall()

        for msg_id, address in rows:
            lat, lon = geocoding(address)
            if lat is not None and lon is not None:
                cursor.execute(
                    "UPDATE messages SET lat = %s, lon = %s WHERE msg_id = %s",
                    (lat, lon, msg_id),
                )
                print(f"Đã cập nhật room id {msg_id}: lat = {lat}, lon = {lon}")
            else:
                print(f"Không cập nhật được room id {msg_id} với địa chỉ: {address}")

        conn.commit()
    except Exception as e:
        print("Lỗi kết nối hoặc cập nhật cơ sở dữ liệu:", e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def geocoding_openmaps(address):
    base_url = "https://mapapis.openmap.vn/v1"
    apikey = "dOVlwo9Ti1GAQKUppoeHuD2oq9ioXoyQ"

    res = requests.get(f"{base_url}/geocode/forward?address={address}&apikey={apikey}")

    if res.status_code == 200:
        data = res.json()
        if data:
            location = data["results"][0]["geometry"]["location"]
            lat = location["lat"]
            lng = location["lng"]
            print(lat, lng)
            return lat, lng
        else:
            raise ValueError("Không tìm thấy địa chỉ")
    else:
        raise ValueError(f"lỗi kết nối đến openmaps {res.status_code}")


if __name__ == "__main__":
        

    # Địa chỉ API, giả sử API đang chạy trên localhost:8000
    url = "http://127.0.0.1:8080/search"
  

    # Các tham số truy vấn, chỉ cần bắt buộc 'address' và các trường khác tùy chọn
    params = {
        "address": "Ngõ 59 Văn Tiến Dũng",
        "radius": 1,             # Bán kính (km)
        "min_price": 0,      # Giá phòng tối thiểu (nếu có)
        "max_price": 5000000,     # Giá phòng tối đa (nếu có)
             # Loại phòng (nếu có)
    }

    # Gửi yêu cầu GET với các tham số query
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        print("Response data:", data)
    else:
        print("Error:", response.status_code, response.text)

    # diachi1 = "số nhà 59, ngõ 59 văn tiến dũng"
    # diachi2 = "Trường đại học công nghiệp hà nội"

    # khoangcach = get_distance_matrix(*geocoding(diachi1), *geocoding(diachi2))
    # print(khoangcach)

    # update_db_coordinates(db_config=config.db_config)
    # test_api_filter()
    # test_api_insert()
    # shared.geocoding_openmaps("ngõ 59 văn tiến dũng")
    # print("share")
   
    


    




    
