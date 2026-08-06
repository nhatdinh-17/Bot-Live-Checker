import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils.data_utils import get_user_data, update_user_data, load_token_pool
from services.checkers import (
    check_facebook_uid_status,
    check_instagram_user,
    check_tiktok_user,
    clean_target
)
from core.auto_check import auto_check_all

logger = logging.getLogger(__name__)

# Conversation states — check
WAITING_FB_TARGET, WAITING_IG_TARGET, WAITING_TT_TARGET = range(3)
# Conversation states — add (3 steps each: UID → Note → Price)
(
    WAITING_ADD_FB, WAITING_ADD_FB_NOTE, WAITING_ADD_FB_PRICE,
    WAITING_ADD_IG, WAITING_ADD_IG_NOTE, WAITING_ADD_IG_PRICE,
    WAITING_ADD_TT, WAITING_ADD_TT_NOTE, WAITING_ADD_TT_PRICE,
) = range(3, 12)
# Conversation states — delete
WAITING_DEL_FB, WAITING_DEL_IG, WAITING_DEL_TT = range(12, 15)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    user_data = get_user_data(user_id)
    if not user_data.get("name"):
        user_data["name"] = user.full_name
        update_user_data(user_id, user_data)

    fb_cnt = len(user_data.get("fb_targets", []))
    ig_cnt = len(user_data.get("ig_targets", []))
    tt_cnt = len(user_data.get("tiktok_targets", []))

    text = (
        f"⚡ <b>TOOL CHECK LIVE / DIE - TELEGRAM BOT</b>\n"
        f"─────────────────────────────\n"
        f"👤 Người dùng: <b>{user.full_name}</b> (ID: <code>{user_id}</code>)\n"
        f"📊 Đang theo dõi: <b>FB: {fb_cnt}</b> | <b>IG: {ig_cnt}</b> | <b>TikTok: {tt_cnt}</b>\n"
        f"─────────────────────────────\n"
        f"👇 <b>Bấm các nút bên dưới hoặc gõ lệnh để check:</b>\n"
    )

    keyboard = [
        [
            InlineKeyboardButton("📘 Check Facebook", callback_data="btn_checkfb"),
            InlineKeyboardButton("📷 Check Instagram", callback_data="btn_checkig"),
        ],
        [
            InlineKeyboardButton("🎵 Check TikTok", callback_data="btn_checktt"),
            InlineKeyboardButton("📋 Danh sách theo dõi", callback_data="btn_list"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await update.message.reply_html(text, reply_markup=reply_markup)

async def prompt_fb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if target provided directly with command (e.g. /checkfb zuck)
    if context.args:
        return await process_fb_check(update, context, context.args[0])

    text = "📘 <b>Vui lòng nhập hoặc dán UID / Link Facebook cần check:</b>"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML")
    else:
        await update.message.reply_html(text)
    return WAITING_FB_TARGET

async def prompt_ig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        return await process_ig_check(update, context, context.args[0])

    text = "📷 <b>Vui lòng nhập hoặc dán Username / Link Instagram cần check:</b>"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML")
    else:
        await update.message.reply_html(text)
    return WAITING_IG_TARGET

async def prompt_tt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        return await process_tt_check(update, context, context.args[0])

    text = "🎵 <b>Vui lòng nhập hoặc dán Username / Link TikTok cần check:</b>"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML")
    else:
        await update.message.reply_html(text)
    return WAITING_TT_TARGET

async def handle_fb_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.text.strip()
    await process_fb_check(update, context, target)
    return ConversationHandler.END

async def handle_ig_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.text.strip()
    await process_ig_check(update, context, target)
    return ConversationHandler.END

async def handle_tt_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.text.strip()
    await process_tt_check(update, context, target)
    return ConversationHandler.END

async def process_fb_check(update: Update, context: ContextTypes.DEFAULT_TYPE, target: str):
    msg = await (update.message or update.callback_query.message).reply_text("⏳ Đang kiểm tra Facebook...")
    tokens = load_token_pool()
    token = tokens[0] if tokens else ""
    res = check_facebook_uid_status(target, token)
    status_str = "🟢 <b>LIVE</b>" if res["live"] else "🔴 <b>DIE</b>"
    err_str = f"\n⚠️ Ghi chú: <i>{res['error']}</i>" if res.get("error") else ""
    text = (
        f"📘 <b>KẾT QUẢ CHECK FACEBOOK</b>\n"
        f"──────────────────────\n"
        f"🆔 Target: <code>{res['target']}</code>\n"
        f"👤 Tên/UID: <b>{res.get('name', res['target'])}</b>\n"
        f"📊 Trạng thái: {status_str}{err_str}"
    )
    await msg.edit_text(text, parse_mode="HTML")

async def process_ig_check(update: Update, context: ContextTypes.DEFAULT_TYPE, target: str):
    msg = await (update.message or update.callback_query.message).reply_text("⏳ Đang kiểm tra Instagram...")
    res = check_instagram_user(target)
    status_str = "🟢 <b>LIVE</b>" if res["live"] else "🔴 <b>DIE</b>"
    err_str = f"\n⚠️ Ghi chú: <i>{res['error']}</i>" if res.get("error") else ""
    text = (
        f"📷 <b>KẾT QUẢ CHECK INSTAGRAM</b>\n"
        f"──────────────────────\n"
        f"👤 Username: <b>@{res['target']}</b>\n"
        f"📊 Trạng thái: {status_str}{err_str}"
    )
    await msg.edit_text(text, parse_mode="HTML")

async def process_tt_check(update: Update, context: ContextTypes.DEFAULT_TYPE, target: str):
    msg = await (update.message or update.callback_query.message).reply_text("⏳ Đang kiểm tra TikTok...")
    res = check_tiktok_user(target)
    status_str = "🟢 <b>LIVE</b>" if res["live"] else "🔴 <b>DIE</b>"
    err_str = f"\n⚠️ Ghi chú: <i>{res['error']}</i>" if res.get("error") else ""
    text = (
        f"🎵 <b>KẾT QUẢ CHECK TIKTOK</b>\n"
        f"──────────────────────\n"
        f"👤 Username: <b>@{res['target']}</b>\n"
        f"📊 Trạng thái: {status_str}{err_str}"
    )
    await msg.edit_text(text, parse_mode="HTML")

async def cancel_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Đã hủy thao tác.")
    return ConversationHandler.END

# ── HELPER: nút Quay lại Menu ───────────────────────────────────────────────────
def _back_menu_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("← Quay lại Menu", callback_data="btn_back_menu")]])

# ── HELPER: format kết quả add ───────────────────────────────────────────────
def _fmt_add_result(
    platform_icon: str, platform_label: str,
    target: str, name: str, note: str, price: str,
    status: str, now_str: str
) -> str:
    status_icon = "✅" if status == "LIVE" else "❌"
    status_line = f"🟢 LIVE {status_icon}" if status == "LIVE" else f"🔴 DIE {status_icon}"
    return (
        f"✅ <b>ĐÃ LÊN ĐƠN THÀNH CÔNG</b>\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"{platform_icon} Nền tảng: <b>{platform_label}</b>\n"
        f"🆔 UID/User: <code>{target}</code>\n"
        f"👤 Tên FB: <b>{name}</b>\n"
        f"📝 Ghi chú: {note or 'Không có'}\n"
        f"💰 Giá: {price} VNĐ\n"
        f"📊 Trạng thái: {status_line}\n"
        f"⏰ Time: {now_str}"
    )

# ── ADD FACEBOOK (3 bước) ──────────────────────────────────────────────────
async def add_fb_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bước 1: Hỏi UID/Link"""
    context.user_data.pop("add_fb", None)
    text = (
        f"➕ <b>THÊM TÀI NGUYÊN MỚI</b>\n"
        f"Vui lòng gửi Link Facebook hoặc UID cần theo dõi.\n"
        f"👇 <i>Hoặc bấm nút bên dưới để quay lại.</i>"
    )
    await update.message.reply_html(text, reply_markup=_back_menu_markup())
    return WAITING_ADD_FB

async def handle_add_fb_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bước 2: Đã nhận UID, hỏi Tên & Ghi chú"""
    raw = update.message.text.strip()
    target = clean_target(raw)
    user_id = str(update.effective_user.id)
    user_data = get_user_data(user_id)
    if any(t.get("target") == target for t in user_data["fb_targets"]):
        await update.message.reply_text("⚠️ UID Facebook này đã có trong danh sách.")
        return ConversationHandler.END
    context.user_data["add_fb"] = {"target": target}
    text = (
        f"✅ <b>Đã nhận:</b> <code>{target}</code>\n\n"
        f"👤 Vui lòng nhập <b>TÊN kèm GHI CHÚ</b> (Gộp chung 1 dòng):\n"
        f"<i>Ví dụ: Nguyễn Văn A kèo của B</i>"
    )
    await update.message.reply_html(text, reply_markup=_back_menu_markup())
    return WAITING_ADD_FB_NOTE

async def handle_add_fb_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bước 3: Đã nhận Tên+Ghi chú, hỏi Giá"""
    note_input = update.message.text.strip()
    context.user_data["add_fb"]["note"] = note_input
    text = (
        f"👤 <b>Tên & Ghi chú:</b> {note_input}\n\n"
        f"💰 Vui lòng nhập <b>GIÁ TIỀN</b> (VNĐ):\n"
        f"<i>(Nhập 0 nếu không cần ghi giá)</i>"
    )
    await update.message.reply_html(text, reply_markup=_back_menu_markup())
    return WAITING_ADD_FB_PRICE

async def handle_add_fb_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bước cuối: Lưu và hiện kết quả"""
    price_raw = update.message.text.strip()
    data = context.user_data.pop("add_fb", {})
    target = data.get("target", "")
    note_input = data.get("note", "")
    # Tách Tên và Ghi chú nếu có từ khóa riêng (tuỳ ý dùng tất cả làm ghi chú)
    note = note_input  # Giữ nguyên, người dùng tự gộp
    price = price_raw if price_raw else "0"
    user_id = str(update.effective_user.id)
    user_data = get_user_data(user_id)
    msg = await update.message.reply_text("⏳ Đang kiểm tra và thêm Facebook...")
    tokens = load_token_pool()
    res = check_facebook_uid_status(target, tokens[0] if tokens else "")
    status = "LIVE" if res["live"] else "DIE"
    fb_name = res.get("name", target)
    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    user_data["fb_targets"].append({
        "target": target, "name": fb_name,
        "note": note, "price": price,
        "status": status, "created_at": now_str, "last_check": now_str
    })
    update_user_data(user_id, user_data)
    await msg.edit_text(
        _fmt_add_result("📘", "Facebook", target, fb_name, note, price, status, now_str),
        parse_mode="HTML"
    )
    return ConversationHandler.END

# ── ADD INSTAGRAM (3 bước) ────────────────────────────────────────────────
async def add_ig_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("add_ig", None)
    text = (
        f"➕ <b>THÊM TÀI NGUYÊN MỚI</b>\n"
        f"Vui lòng gửi Username hoặc Link Instagram cần theo dõi.\n"
        f"👇 <i>Hoặc bấm nút bên dưới để quay lại.</i>"
    )
    await update.message.reply_html(text, reply_markup=_back_menu_markup())
    return WAITING_ADD_IG

async def handle_add_ig_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    target = clean_target(raw)
    user_id = str(update.effective_user.id)
    user_data = get_user_data(user_id)
    if any(t.get("target") == target for t in user_data["ig_targets"]):
        await update.message.reply_text("⚠️ Username IG này đã có trong danh sách.")
        return ConversationHandler.END
    context.user_data["add_ig"] = {"target": target}
    text = (
        f"✅ <b>Đã nhận:</b> @<b>{target}</b>\n\n"
        f"👤 Vui lòng nhập <b>TÊN kèm GHI CHÚ</b> (Gộp chung 1 dòng):\n"
        f"<i>Ví dụ: Nguyễn Văn A kèo của B</i>"
    )
    await update.message.reply_html(text, reply_markup=_back_menu_markup())
    return WAITING_ADD_IG_NOTE

async def handle_add_ig_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note_input = update.message.text.strip()
    context.user_data["add_ig"]["note"] = note_input
    text = (
        f"👤 <b>Tên & Ghi chú:</b> {note_input}\n\n"
        f"💰 Vui lòng nhập <b>GIÁ TIỀN</b> (VNĐ):\n"
        f"<i>(Nhập 0 nếu không cần ghi giá)</i>"
    )
    await update.message.reply_html(text, reply_markup=_back_menu_markup())
    return WAITING_ADD_IG_PRICE

async def handle_add_ig_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_raw = update.message.text.strip()
    data = context.user_data.pop("add_ig", {})
    target = data.get("target", "")
    note = data.get("note", "")
    price = price_raw if price_raw else "0"
    user_id = str(update.effective_user.id)
    user_data = get_user_data(user_id)
    msg = await update.message.reply_text("⏳ Đang kiểm tra và thêm Instagram...")
    res = check_instagram_user(target)
    status = "LIVE" if res["live"] else "DIE"
    ig_name = res.get("name", target)
    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    user_data["ig_targets"].append({
        "target": target, "name": ig_name,
        "note": note, "price": price,
        "status": status, "created_at": now_str, "last_check": now_str
    })
    update_user_data(user_id, user_data)
    await msg.edit_text(
        _fmt_add_result("📷", "Instagram", target, ig_name, note, price, status, now_str),
        parse_mode="HTML"
    )
    return ConversationHandler.END

# ── ADD TIKTOK (3 bước) ───────────────────────────────────────────────────────
async def add_tt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("add_tt", None)
    text = (
        f"➕ <b>THÊM TÀI NGUYÊN MỚI</b>\n"
        f"Vui lòng gửi Username hoặc Link TikTok cần theo dõi.\n"
        f"👇 <i>Hoặc bấm nút bên dưới để quay lại.</i>"
    )
    await update.message.reply_html(text, reply_markup=_back_menu_markup())
    return WAITING_ADD_TT

async def handle_add_tt_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    target = clean_target(raw)
    user_id = str(update.effective_user.id)
    user_data = get_user_data(user_id)
    if any(t.get("target") == target for t in user_data["tiktok_targets"]):
        await update.message.reply_text("⚠️ Username TikTok này đã có trong danh sách.")
        return ConversationHandler.END
    context.user_data["add_tt"] = {"target": target}
    text = (
        f"✅ <b>Đã nhận:</b> @<b>{target}</b>\n\n"
        f"👤 Vui lòng nhập <b>TÊN kèm GHI CHÚ</b> (Gộp chung 1 dòng):\n"
        f"<i>Ví dụ: Nguyễn Văn A kèo của B</i>"
    )
    await update.message.reply_html(text, reply_markup=_back_menu_markup())
    return WAITING_ADD_TT_NOTE

async def handle_add_tt_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note_input = update.message.text.strip()
    context.user_data["add_tt"]["note"] = note_input
    text = (
        f"👤 <b>Tên & Ghi chú:</b> {note_input}\n\n"
        f"💰 Vui lòng nhập <b>GIÁ TIỀN</b> (VNĐ):\n"
        f"<i>(Nhập 0 nếu không cần ghi giá)</i>"
    )
    await update.message.reply_html(text, reply_markup=_back_menu_markup())
    return WAITING_ADD_TT_PRICE

async def handle_add_tt_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_raw = update.message.text.strip()
    data = context.user_data.pop("add_tt", {})
    target = data.get("target", "")
    note = data.get("note", "")
    price = price_raw if price_raw else "0"
    user_id = str(update.effective_user.id)
    user_data = get_user_data(user_id)
    msg = await update.message.reply_text("⏳ Đang kiểm tra và thêm TikTok...")
    res = check_tiktok_user(target)
    status = "LIVE" if res["live"] else "DIE"
    tt_name = res.get("name", target)
    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    user_data["tiktok_targets"].append({
        "target": target, "name": tt_name,
        "note": note, "price": price,
        "status": status, "created_at": now_str, "last_check": now_str
    })
    update_user_data(user_id, user_data)
    await msg.edit_text(
        _fmt_add_result("🎵", "TikTok", target, tt_name, note, price, status, now_str),
        parse_mode="HTML"
    )
    return ConversationHandler.END

# ── DELETE FACEBOOK ────────────────────────────────────────────────────────────
async def delete_fb_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        return await _do_delete_fb(update, context, context.args[0])
    await update.message.reply_html("📘 <b>Nhập UID / Link Facebook cần xóa khỏi danh sách:</b>")
    return WAITING_DEL_FB

async def handle_del_fb_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_delete_fb(update, context, update.message.text.strip())
    return ConversationHandler.END

async def _do_delete_fb(update: Update, context: ContextTypes.DEFAULT_TYPE, raw_target: str):
    target = clean_target(raw_target)
    user_id = str(update.effective_user.id)
    user_data = get_user_data(user_id)
    original_len = len(user_data.get("fb_targets", []))
    user_data["fb_targets"] = [t for t in user_data["fb_targets"] if (t.get("target") or t.get("uid")) != target]
    if len(user_data["fb_targets"]) < original_len:
        update_user_data(user_id, user_data)
        await update.message.reply_html(f"🗑 Đã xóa FB <code>{target}</code> khỏi danh sách.")
    else:
        await update.message.reply_text("⚠️ Không tìm thấy target trong danh sách.")

# ── DELETE INSTAGRAM ───────────────────────────────────────────────────────────
async def delete_ig_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        return await _do_delete_ig(update, context, context.args[0])
    await update.message.reply_html("📷 <b>Nhập Username / Link Instagram cần xóa khỏi danh sách:</b>")
    return WAITING_DEL_IG

async def handle_del_ig_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_delete_ig(update, context, update.message.text.strip())
    return ConversationHandler.END

async def _do_delete_ig(update: Update, context: ContextTypes.DEFAULT_TYPE, raw_target: str):
    target = clean_target(raw_target)
    user_id = str(update.effective_user.id)
    user_data = get_user_data(user_id)
    original_len = len(user_data.get("ig_targets", []))
    user_data["ig_targets"] = [t for t in user_data["ig_targets"] if (t.get("target") or t.get("username")) != target]
    if len(user_data["ig_targets"]) < original_len:
        update_user_data(user_id, user_data)
        await update.message.reply_html(f"🗑 Đã xóa Instagram @<b>{target}</b> khỏi danh sách.")
    else:
        await update.message.reply_text("⚠️ Không tìm thấy target trong danh sách.")

# ── DELETE TIKTOK ──────────────────────────────────────────────────────────────
async def delete_tt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        return await _do_delete_tt(update, context, context.args[0])
    await update.message.reply_html("🎵 <b>Nhập Username / Link TikTok cần xóa khỏi danh sách:</b>")
    return WAITING_DEL_TT

async def handle_del_tt_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_delete_tt(update, context, update.message.text.strip())
    return ConversationHandler.END

async def _do_delete_tt(update: Update, context: ContextTypes.DEFAULT_TYPE, raw_target: str):
    target = clean_target(raw_target)
    user_id = str(update.effective_user.id)
    user_data = get_user_data(user_id)
    original_len = len(user_data.get("tiktok_targets", []))
    user_data["tiktok_targets"] = [t for t in user_data["tiktok_targets"] if (t.get("target") or t.get("username")) != target]
    if len(user_data["tiktok_targets"]) < original_len:
        update_user_data(user_id, user_data)
        await update.message.reply_html(f"🗑 Đã xóa TikTok @<b>{target}</b> khỏi danh sách.")
    else:
        await update.message.reply_text("⚠️ Không tìm thấy target trong danh sách.")

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user_data(user_id)
    fb_list = user_data.get("fb_targets", [])
    ig_list = user_data.get("ig_targets", [])
    tt_list = user_data.get("tiktok_targets", [])

    if not fb_list and not ig_list and not tt_list:
        text = "📋 Danh sách theo dõi đang trống.\nDùng /addfb, /addig, /addtt để thêm tài khoản."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    text = "📋 <b>DANH SÁCH TÀI KHOẢN THEO DÕI</b>\n──────────────────────\n"
    if fb_list:
        text += "📘 <b>FACEBOOK:</b>\n"
        for i, t in enumerate(fb_list, 1):
            st = "🟢 LIVE" if t.get("status") == "LIVE" or t.get("trangthai") == "LIVE" else "🔴 DIE"
            text += f"{i}. <code>{t.get('target') or t.get('uid')}</code> | {st}\n"
        text += "\n"
    if ig_list:
        text += "📷 <b>INSTAGRAM:</b>\n"
        for i, t in enumerate(ig_list, 1):
            st = "🟢 LIVE" if t.get("status") == "LIVE" or t.get("trangthai") == "LIVE" else "🔴 DIE"
            text += f"{i}. @<b>{t.get('target') or t.get('username')}</b> | {st}\n"
        text += "\n"
    if tt_list:
        text += "🎵 <b>TIKTOK:</b>\n"
        for i, t in enumerate(tt_list, 1):
            st = "🟢 LIVE" if t.get("status") == "LIVE" or t.get("trangthai") == "LIVE" else "🔴 DIE"
            text += f"{i}. @<b>{t.get('target') or t.get('username')}</b> | {st}\n"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML")
    else:
        await update.message.reply_html(text)



async def checknow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Đang tiến hành re-check toàn bộ danh sách...")
    await auto_check_all(context.application)
    await msg.edit_text("✅ Đã hoàn tất kiểm tra lại toàn bộ danh sách!")
