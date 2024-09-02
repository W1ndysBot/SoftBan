# script/SoftBan/main.py
# 软封禁模块，不禁言，但撤回每一条该用户消息

import logging
import os
import sys
import re


# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.config import owner_id
from app.api import *
from app.switch import load_switch, save_switch


# 数据存储路径，实际开发时，请将SoftBan替换为具体的数据存放路径
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "SoftBan",
)


# 检查是否有权限（管理员、群主或root管理员）
def is_authorized(role, user_id):
    is_admin = is_group_admin(role)
    is_owner = is_group_owner(role)
    return (is_admin or is_owner) or (user_id in owner_id)


# 查看功能开关状态
def load_SoftBan_status(group_id):
    return load_switch(group_id, "SoftBan_status")


# 获取软封禁用户列表
def load_SoftBan_users(group_id):
    file_path = os.path.join(DATA_DIR, f"{group_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# 保存软封禁用户列表
def save_SoftBan_users(group_id, users):
    file_path = os.path.join(DATA_DIR, f"{group_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)


# 添加软封禁用户
def add_SoftBan_user(group_id, user_id):
    softban_list = load_SoftBan_users(group_id)
    if user_id not in softban_list:
        softban_list.append(user_id)
        save_SoftBan_users(group_id, softban_list)


# 删除软封禁用户
def remove_SoftBan_user(group_id, user_id):
    softban_list = load_SoftBan_users(group_id)
    if user_id in softban_list:
        softban_list.remove(user_id)
        save_SoftBan_users(group_id, softban_list)


# 保存功能开关状态
def save_SoftBan_status(group_id, status):
    save_switch(group_id, "SoftBan_status", status)


# 软封禁管理
async def manage_SoftBan(websocket, message_id, group_id, raw_message, is_authorized):

    if not is_authorized:
        return

    if raw_message == "sb-list":
        softban_list = load_SoftBan_users(group_id)
        if softban_list:
            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]群{group_id}软封禁用户列表:\n"
                + "\n".join(softban_list),
            )
        else:
            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]群{group_id}软封禁用户列表为空",
            )
    elif raw_message.startswith("sb-add"):
        match = re.search(r"\[CQ:at,qq=([0-9]+)\]", raw_message)
        if match:
            target_user_id = match.group(1)  # 获取目标用户ID
            add_SoftBan_user(group_id, target_user_id)
            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]用户 {target_user_id} 已被软封禁",
            )
    elif raw_message.startswith("sb-rm"):
        match = re.search(r"\[CQ:at,qq=([0-9]+)\]", raw_message)
        if match:
            target_user_id = match.group(1)
            remove_SoftBan_user(group_id, target_user_id)
            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]用户 {target_user_id} 已从软封禁列表中删除",
            )


# 群消息处理函数
async def handle_SoftBan_group_message(websocket, msg):
    try:
        user_id = str(msg.get("user_id"))
        group_id = str(msg.get("group_id"))
        raw_message = str(msg.get("raw_message"))
        role = str(msg.get("sender", {}).get("role"))
        message_id = str(msg.get("message_id"))

        is_authorized_qq = is_authorized(role, user_id)

        if user_id in load_SoftBan_users(group_id):
            logging.info(f"软封禁用户: {user_id} 发送了消息，执行撤回")
            await delete_msg(websocket, message_id)

        await manage_SoftBan(
            websocket, message_id, group_id, raw_message, is_authorized_qq
        )

    except Exception as e:
        logging.error(f"处理SoftBan群消息失败: {e}")


async def SoftBan_main(websocket, msg):

    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)

    await handle_SoftBan_group_message(websocket, msg)
