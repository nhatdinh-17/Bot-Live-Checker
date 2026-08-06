import logging
from datetime import datetime
from utils.data_utils import load_all_data, update_user_data, load_token_pool
from services.checkers import (
    check_facebook_uid_status,
    check_instagram_user,
    check_tiktok_user
)

logger = logging.getLogger(__name__)


def _parse_dt(s: str):
    """Parse datetime string từ định dạng '%H:%M:%S - %d/%m/%Y'."""
    try:
        return datetime.strptime(s, "%H:%M:%S - %d/%m/%Y")
    except Exception:
        return None


def _fmt_elapsed(seconds: float) -> str:
    """Chuyển số giây thành chuỗi ngắn gọn, vd: '4d 14h 49p'."""
    seconds = int(abs(seconds))
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}p")
    if not parts:
        parts.append(f"{s}s")
    return " ".join(parts)


def _fmt_status_card(
    platform_icon: str,
    platform: str,
    target: str,
    name: str,
    new_status: str,
    created_at: str,
    now_str: str,
) -> str:
    if new_status == "LIVE":
        header = "🟢 <b>Thông báo tài khoản LIVE</b>"
        status_line = "LIVE ✅"
        elapsed_label = "⏰ Đã sống lại sau"
    else:
        header = "🔴 <b>Thông báo tài khoản DIE</b>"
        status_line = "DIE ❌"
        elapsed_label = "⏰ Đã die sau"

    created_dt = _parse_dt(created_at)
    now_dt = _parse_dt(now_str)
    if created_dt and now_dt:
        elapsed = _fmt_elapsed((now_dt - created_dt).total_seconds())
    else:
        elapsed = "N/A"

    return (
        f"{header}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{platform_icon} Nền tảng: <b>{platform}</b>\n"
        f"🆔 UID: <code>{target}</code>\n"
        f"👤 Tên: <b>{name}</b>\n"
        f"📝 Ghi chú: Không có\n"
        f"💰 Giá: 0\n"
        f"📊 Trạng thái mới: {status_line}\n"
        f"{elapsed_label}: {elapsed}\n"
        f"⏱ Thời gian xử lý: {elapsed}\n"
        f"🆕 Tạo: {created_at}\n"
        f"🔎 Check gần đây: {now_str}"
    )


async def auto_check_all(app):
    """Periodically check LIVE/DIE status for all monitored targets."""
    logger.info("Bắt đầu auto-check trạng thái Live/Die...")
    data = load_all_data()
    tokens = load_token_pool()
    token = tokens[0] if tokens else ""
    now_str = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")

    for user_id, user_data in data.items():
        changed = False

        # ── Facebook targets ────────────────────────────────────────────────
        for entry in user_data.get("fb_targets", []):
            target = entry.get("target") or entry.get("uid")
            if not target:
                continue
            old_status = entry.get("status") or entry.get("trangthai", "UNKNOWN")
            res = check_facebook_uid_status(target, token)
            new_status = "LIVE" if res["live"] else "DIE"
            entry["status"] = new_status
            entry["trangthai"] = new_status
            entry["last_check"] = now_str
            if old_status != "UNKNOWN" and old_status != new_status:
                changed = True
                created_at = entry.get("created_at") or entry.get("last_change") or entry.get("last_check", now_str)
                entry["last_change"] = now_str
                if not entry.get("created_at"):
                    entry["created_at"] = created_at
                msg = _fmt_status_card(
                    platform_icon="📘", platform="Facebook",
                    target=target, name=entry.get("name", target),
                    new_status=new_status,
                    created_at=created_at,
                    now_str=now_str,
                )
                try:
                    await app.bot.send_message(chat_id=int(user_id), text=msg, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Gửi thông báo FB thất bại ({user_id}): {e}")

        # ── Instagram targets ───────────────────────────────────────────────
        for entry in user_data.get("ig_targets", []):
            target = entry.get("target") or entry.get("username")
            if not target:
                continue
            old_status = entry.get("status") or entry.get("trangthai", "UNKNOWN")
            res = check_instagram_user(target)
            new_status = "LIVE" if res["live"] else "DIE"
            entry["status"] = new_status
            entry["trangthai"] = new_status
            entry["last_check"] = now_str
            if old_status != "UNKNOWN" and old_status != new_status:
                changed = True
                created_at = entry.get("created_at") or entry.get("last_change") or entry.get("last_check", now_str)
                entry["last_change"] = now_str
                if not entry.get("created_at"):
                    entry["created_at"] = created_at
                msg = _fmt_status_card(
                    platform_icon="📷", platform="Instagram",
                    target=f"@{target}", name=entry.get("name", target),
                    new_status=new_status,
                    created_at=created_at,
                    now_str=now_str,
                )
                try:
                    await app.bot.send_message(chat_id=int(user_id), text=msg, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Gửi thông báo IG thất bại ({user_id}): {e}")

        # ── TikTok targets ──────────────────────────────────────────────────
        for entry in user_data.get("tiktok_targets", []):
            target = entry.get("target") or entry.get("username")
            if not target:
                continue
            old_status = entry.get("status") or entry.get("trangthai", "UNKNOWN")
            res = check_tiktok_user(target)
            new_status = "LIVE" if res["live"] else "DIE"
            entry["status"] = new_status
            entry["trangthai"] = new_status
            entry["last_check"] = now_str
            if old_status != "UNKNOWN" and old_status != new_status:
                changed = True
                created_at = entry.get("created_at") or entry.get("last_change") or entry.get("last_check", now_str)
                entry["last_change"] = now_str
                if not entry.get("created_at"):
                    entry["created_at"] = created_at
                msg = _fmt_status_card(
                    platform_icon="🎵", platform="TikTok",
                    target=f"@{target}", name=entry.get("name", target),
                    new_status=new_status,
                    created_at=created_at,
                    now_str=now_str,
                )
                try:
                    await app.bot.send_message(chat_id=int(user_id), text=msg, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Gửi thông báo TikTok thất bại ({user_id}): {e}")

        if changed:
            update_user_data(user_id, user_data)

    logger.info("Hoàn tất auto-check.")
