
def is_info_message(message_object):
    keywords = ["🏡",
        "💰",
        "✅",
        "nhà",
        "phòng",
        "hợp đồng",
        "gọi trước",
        "báo trước",
        "HH",
        "hoa hồng",
        "giá",
        "địa chỉ",
        "khách",]
    message = message_object.content
    type = message_object.msgType
    if len(message) > 200 and type == 'webchat':
        if any(key in message for key in keywords):
            return True
    return False

def group_messages(messages):
    """
    Hàm group_messages xử lý danh sách tin nhắn theo thứ tự thời gian và nhóm chúng theo phòng.
    Quy tắc:
      - Nếu tin nhắn là "webchat":
           + Nếu current_room rỗng: bắt đầu một phòng mới (Group 1)
           + Nếu current_room không rỗng:
                 * Nếu tin đầu tiên của current_room là "webchat": đó là phòng Group 1 đang hoàn thiện, bắt đầu phòng mới.
                 * Ngược lại (tin đầu tiên là media): tin webchat này là thông tin của phòng Group 2 (media trước, info sau).
      - Các tin nhắn media (hoặc sticker) sẽ được thêm vào current_room.
    """
    rooms = []
    current_room = []
    
    for message in messages:
        if message['type'] == 'webchat':
            if not current_room:
                # current_room rỗng, bắt đầu phòng mới với webchat (Group 1)
                current_room.append(message)
            else:
                if current_room[0]['type'] == 'webchat':
                    # Phòng hiện tại là Group 1, bắt đầu một phòng mới khi gặp webchat mới
                    rooms.append(current_room)
                    current_room = [message]
                else:
                    # current_room chứa media trước đó, nên tin webchat này đánh dấu kết thúc của Group 2
                    current_room.append(message)
                    rooms.append(current_room)
                    current_room = []
        elif message['type'] in ['media', 'sticker']:
            # Với media hoặc sticker, thêm vào current_room
            current_room.append(message)
        else:
            # Nếu có loại tin nhắn khác (rác đã được lọc thì không xuất hiện)
            continue

    # Nếu sau khi duyệt hết tin nhắn mà current_room vẫn chưa rỗng, thêm nó vào danh sách phòng
    if current_room:
        rooms.append(current_room)
    
    return rooms

def separate_groups(rooms):
    """
    Hàm separate_groups phân chia các phòng thành 2 nhóm:
      - Group 1: Những phòng mà tin nhắn đầu tiên là "webchat" (thông tin trước, sau đó media).
      - Group 2: Những phòng mà tin nhắn cuối cùng là "webchat" (media trước, thông tin sau).
      - Với các trường hợp không rõ, bạn có thể điều chỉnh theo nhu cầu.
    """
    group1 = []
    group2 = []
    
    for room in rooms:
        if room:
            # Nếu tin nhắn đầu tiên là webchat, đó là Group 1
            if room[0]['type'] == 'webchat':
                group1.append(room)
            # Nếu tin nhắn cuối cùng là webchat (và tin đầu tiên không phải webchat), đó là Group 2
            elif room[-1]['type'] == 'webchat':
                group2.append(room)
            else:
                # Nếu không rõ, ví dụ: chỉ có media, bạn có thể gán mặc định hoặc bỏ qua.
                group1.append(room)
    return group1, group2

# # Ví dụ về danh sách tin nhắn
# messages = [
#     # Phòng 1: Group 1 (webchat trước, sau đó media)
#     {'type': 'webchat', 'text': 'Thông tin phòng 1'},
#     {'type': 'media', 'url': 'image1.jpg'},
#     {'type': 'media', 'url': 'video1.mp4'},
    
#     # Phòng 2: Group 2 (media trước, webchat sau)
#     {'type': 'media', 'url': 'image2.jpg'},
#     {'type': 'media', 'url': 'video2.mp4'},
#     {'type': 'webchat', 'text': 'Thông tin phòng 2'},
    
#     # Phòng 3: Group 1 (webchat trước, media sau)
#     {'type': 'webchat', 'text': 'Thông tin phòng 3'},
#     {'type': 'media', 'url': 'image3.jpg'},
    
#     # Phòng 4: Group 2 (media trước, webchat sau)
#     {'type': 'media', 'url': 'image4.jpg'},
#     {'type': 'sticker', 'url': 'sticker1.png'},
#     {'type': 'webchat', 'text': 'Thông tin phòng 4'},
# ]

# # Nhóm tin nhắn thành các phòng
# rooms = group_messages(messages)

# # Tách các phòng thành 2 nhóm theo thứ tự tin nhắn
# group1, group2 = separate_groups(rooms)

# print("Group 1 (Thông tin trước, media sau):")
# for room in group1:
#     print(room)
    
# print("\nGroup 2 (Media trước, thông tin sau):")
# for room in group2:
#     print(room)
