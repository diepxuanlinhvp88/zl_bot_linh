from zlapi.Async import ZaloAPI
from zlapi.models import *
import share as shared
import json
import psycopg2
import config
import db_logic as dblogic
import message_controller
import asyncio
import time
import os
import group_type as gr_type


class CurrentRoom:
    def __init__(self):
        self.info = []
        self.media = []


class CustomBot(ZaloAPI):
    current_rooms = {}
    count = dblogic.get_count_of_rooms()

    def get_current_room(self, from_id, uid_to):
        key = (from_id, uid_to)
        if key not in self.current_rooms:
            self.current_rooms[key] = CurrentRoom()
        return self.current_rooms[key]

    async def save_room(self, room, from_id, uid_to, mid):
        grId = "656644798532396185"

        try:
            dblogic.insert_room_with_media(room.info[0], room.media, mid)
            print(
                f"✅ Dữ liệu của phòng {from_id} -> {uid_to} đã được lưu vào database \n phòng số {self.count}"
            )

        except Exception as e:
            print("❌ Lỗi khi lưu dữ liệu vào database:", str(e))

        # try:
        #     for media in room.media:
        #         if media["href"].endswith(".jpg"):
        #             await self.sendRemoteImage(
        #                 media["href"], thread_id=grId, thread_type=ThreadType.GROUP
        #             )
        #         else:
        #             # Lấy chuỗi JSON từ key 'params'
        #             params_str = media.get("params", "{}")
        #             # Chuyển đổi chuỗi JSON thành dict
        #             params = json.loads(params_str)
        #             # Lấy giá trị duration
        #             duration = params.get("duration")
        #             width = params.get("video_original_width")
        #             height = params.get("video_original_height")
        #             await self.sendRemoteVideo(
        #                 videoUrl=media["href"],
        #                 thread_id=grId,
        #                 thread_type=ThreadType.GROUP,
        #                 thumbnailUrl=media["thumb"],
        #                 duration=duration,
        #                 width=width,
        #                 height=height,
        #             )
        #     await self.sendMessage(
        #         Message(text=room.info[0]), thread_id=grId, thread_type=ThreadType.GROUP
        #     )
        #     print("✅ Dữ liệu đã được gửi vào group")
        # except Exception as e:
        #     print("❌ Lỗi khi gửi dữ liệu vào group:", str(e))

        # Sau khi lưu, bạn có thể reset trạng thái của room:
        self.current_rooms[(from_id, uid_to)] = CurrentRoom()

    def save_message_to_postgresql(self, msg_data):
        """
        Lưu dữ liệu tin nhắn vào PostgreSQL, bao gồm cả tin nhắn gốc và thông tin trích xuất.
        """
        try:
            conn = dblogic.connect_db()[0]

            # self.count = dblogic.count_records(conn, "messages")

            cur = conn.cursor()

            # Tạo bảng messages nếu chưa tồn tại
            dblogic.create_table_messages(conn, cur)
            dblogic.insert_message_to_messages_table(conn, cur, msg_data)

            conn.commit()
            print("✅ Dữ liệu tin nhắn đã được lưu vào PostgreSQL")

            cur.close()
            conn.close()
        except Exception as e:
            print("❌ Lỗi khi lưu tin nhắn vào PostgreSQL:", str(e))

    async def onMessage(
        self, mid, author_id, message, message_object, thread_id, thread_type
    ):
        # Lấy thông tin phân biệt từ message_object: từ uidFrom và idTo (hoặc từ các trường tương ứng)
        uid_from = message_object.uidFrom
        id_to = message_object.idTo

        current_room = self.get_current_room(uid_from, id_to)

        if id_to == "656644798532396185":
            return

        # tin nhắn có sticker ngăn cách -
        if id_to in gr_type.nhom1:
            # Lấy current room ứng với cặp (uid_from, id_to)
            print("nhóm 1")

            if message_object.msgType == "chat.sticker":
                print("Đã nhận được sticker o nhom 1")
                if len(current_room.info) == 1 and len(current_room.media) != 0:
                    print("Đã có media, lưu thông tin và media vào database")
                    await self.save_room(current_room, uid_from, id_to, mid)
                    current_room.info = []
                    current_room.media = []
                    return
                elif len(current_room.info) == 0 and len(current_room.media) == 0:
                    return
                else:
                    current_room.info = []
                    current_room.media = []
                    return
            if message_controller.is_info_message(message_object):
                print("Nhận được tin nhắn thông tin o nhom 1", uid_from, "đến", id_to)
                current_room.info.append(message_object)
            if message_object.msgType in ["chat.photo", "chat.video.msg"]:
                current_room.media.append(message_object.content)
                print("Đã thêm media vào phòng của", uid_from, "đến", id_to)

            return
        if id_to in gr_type.nhom2:
            print("nhóm 2")
            return
        if id_to in gr_type.nhom3:
            print("nhóm 3")

            # Nếu tin nhắn là tin thông tin phòng (webchat được xác định qua hàm is_info_message)
            if message_controller.is_info_message(message_object):
                print("Nhận được tin nhắn thông tin từ", uid_from, "đến", id_to)

                if len(current_room.info) == 0 and len(current_room.media) != 0:
                    print("Đã có media, lưu thông tin và media vào database")
                    current_room.info.append(message_object)

                    await self.save_room(current_room, uid_from, id_to, mid)
                    current_room.info = []
                    current_room.media = []
                    return
                elif len(current_room.info) != 0 and len(current_room.media) == 0:
                    current_room.info = []
                    current_room.media = []
                    return
                else:
                    current_room.info = []
                    current_room.media = []
                    return

            if message_object.msgType in ["chat.photo", "chat.video.msg"]:
                current_room.media.append(message_object.content)
                print("Đã thêm media vào phòng của", uid_from, "đến", id_to)

            return
        # thong tin truoc anh sau
        if id_to in gr_type.nhom4:
            print("nhóm 4")

            if message_controller.is_info_message(message_object):
                print("Nhận được tin nhắn thông tin từ", uid_from, "đến", id_to)
                # Nếu đã có thông tin trong current_room (đã có phòng mở) thì lưu dữ liệu hiện tại và tạo phòng mới
                if len(current_room.info) == 1:
                    print(
                        "Phòng đã có thông tin và media, lưu lại và khởi tạo nhóm mới"
                    )
                    # Lưu dữ liệu của room hiện tại
                    await self.save_room(current_room, uid_from, id_to, mid)
                    # Tạo phòng mới: reset info và media cho cuộc hội thoại này
                    current_room.info.append(message_object)
                    current_room.media = []
                    print("Bắt đầu lưu thông tin mới cho phòng")
                    return
                if len(current_room.info) == 0:
                    print("nhom 4 batws dau them thong tin phongf vao")
                    current_room.info.append(message_object)

                    if len(current_room.media) != 0:
                        print("Đã có media, lưu thông tin và media vào database")
                        await self.save_room(current_room, uid_from, id_to, mid)
                        return

            # Nếu tin nhắn là media (ảnh, video)
            if message_object.msgType in ["chat.photo", "chat.video.msg"]:
                # Thêm link media vào danh sách media của current_room
                # href = message_object.content["href"]
                current_room.media.append(message_object.content)
                print("Đã thêm media vào phòng của", uid_from, "đến", id_to)

            return

        self.count = dblogic.get_count_of_rooms()

        if self.count % 50 == 0:
            dblogic.delete_duplicate_rooms()
            print("Dữ liệu đã được xóa trùng lặp.")


if __name__ == "__main__":
    imei = config.imei
    cookies = config.cookies

    bot = CustomBot(imei=imei, cookies=cookies)

    gridVerMap = {
        "5995417883685869233": "1740666933868",
        "4180026171086571911": "1740640988176",
        "3551345029004249293": "1740659051562",
        "2620245674910927321": "1740656714721",
        "1586747907959530112": "1740643285702",
        "656644798532396185": "1740645718953",
        "7969181481987917597": "1740625046358",
        "6410459256912715635": "1740646657255",
        "7143889258887902881": "1740642050708",
        "7332339398060709188": "1740663052185",
        "971045881455363580": "1740651966110",
        "796533044466268040": "1740662585080",
        "5906065609019266675": "1740659046299",
        "5546063285028293234": "1740659954919",
        "7506999140408096683": "1738575025777",
        "839871850990771490": "1740641287734",
        "2911716473059930605": "1740666139231",
        "110157126383023874": "1740633445310",
        "4529605636203795289": "1740665407119",
        "1934944382725452127": "1740602159081",
        "6864640287247936193": "1740602955865",
        "6038488857883225928": "1740648886729",
        "3490267106156146410": "1740662028170",
        "8483003348021411132": "1740399290049",
        "1246730871273745864": "1740663045166",
        "2533263204883215778": "1740622495990",
        "3102823993952998794": "1740661701963",
        "8448101811437304248": "1740663064189",
        "2758582474915635149": "1740649960179",
    }
    # for i in gridVerMap:
    #     print(i)

    #     # print(asyncio.run(bot.fetchGroupInfo(i)))
    # hoa = asyncio.run(bot.fetchPhoneNumber("0334889291"))
    # uid = "7095346275289179378"

    # asyncio.run(bot.sendText(uid, 'hoa'))
    # print(asyncio.run(bot.fetchUserInfo(uid)))
    # print(asyncio.run(bot.addUsersToGroup(uid,"656644798532396185")))
    # print(asyncio.run(bot.sendMessage(message=Message(text="alô"),thread_id=uid, thread_type= ThreadType.USER)))

    # print(hoa)
    # group = asyncio.run(bot.fetchGroupInfo('8448101811437304248'))
    # print(group.gridInfoMap)
    # mem_ver_list = group['gridInfoMap']['8448101811437304248']['memVerList']
    # print(len(mem_ver_list))
    # print(mem_ver_list)
    # print(asyncio.run(bot.fetchUserInfo("709816448129884508")))

    bot.listen()
    # for i in mem_ver_list:
    #     print(i)
    #     print(asyncio.run(bot.fetchUserInfo(i)))
    # print(asyncio.run(bot.fetchUserInfo("8419675329682840925_0")))
    # dblogic.insert_room_with_media()
