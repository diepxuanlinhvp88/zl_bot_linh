import subprocess
import sys

def run():
    # Kiểm tra nếu đang sử dụng Python 3
    if sys.version_info[0] < 3:
        print("Vui lòng sử dụng Python 3 để chạy chương trình.")
        return
    
    # Chạy api.py
    process_api = subprocess.Popen(["python3", "bot/api.py"])
    # Chạy get_messages.py
    process_get_messages = subprocess.Popen(["python3", "bot/get_messages.py"])

    # Chờ các process hoàn thành (nếu cần thiết)
    process_api.wait()
    process_get_messages.wait()

if __name__ == "__main__":
    run()
