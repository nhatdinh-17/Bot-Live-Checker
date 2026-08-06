import asyncio
import os
import logging
from telegram import Update, BotCommand, BotCommandScopeDefault
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from config import BOT_TOKEN, CHECK_INTERVAL_MINUTES
from core.auto_check import auto_check_all
from handlers.commands import (
    start,
    prompt_fb, prompt_ig, prompt_tt,
    handle_fb_input, handle_ig_input, handle_tt_input,
    cancel_check,
    WAITING_FB_TARGET, WAITING_IG_TARGET, WAITING_TT_TARGET,
    # Add states
    add_fb_cmd, handle_add_fb_uid, handle_add_fb_note, handle_add_fb_price,
    WAITING_ADD_FB, WAITING_ADD_FB_NOTE, WAITING_ADD_FB_PRICE,
    add_ig_cmd, handle_add_ig_uid, handle_add_ig_note, handle_add_ig_price,
    WAITING_ADD_IG, WAITING_ADD_IG_NOTE, WAITING_ADD_IG_PRICE,
    add_tt_cmd, handle_add_tt_uid, handle_add_tt_note, handle_add_tt_price,
    WAITING_ADD_TT, WAITING_ADD_TT_NOTE, WAITING_ADD_TT_PRICE,
    # Delete states
    delete_fb_cmd, handle_del_fb_input, WAITING_DEL_FB,
    delete_ig_cmd, handle_del_ig_input, WAITING_DEL_IG,
    delete_tt_cmd, handle_del_tt_input, WAITING_DEL_TT,
    list_cmd,
    checknow
)
from utils.data_utils import save_token_pool

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def set_bot_commands(app):
    commands = [
        BotCommand("start", "⚡ Bảng điều khiển & Hướng dẫn sử dụng"),
        BotCommand("checkfb", "📘 Kiểm tra Live/Die Facebook"),
        BotCommand("checkig", "📷 Kiểm tra Live/Die Instagram"),
        BotCommand("checktt", "🎵 Kiểm tra Live/Die TikTok"),
        BotCommand("addfb", "➕ Thêm Facebook vào danh sách theo dõi"),
        BotCommand("addig", "➕ Thêm Instagram vào danh sách theo dõi"),
        BotCommand("addtt", "➕ Thêm TikTok vào danh sách theo dõi"),
        BotCommand("list", "📋 Danh sách theo dõi & Trạng thái"),
        BotCommand("deletefb", "🗑 Xóa Facebook khỏi danh sách"),
        BotCommand("deleteig", "🗑 Xóa Instagram khỏi danh sách"),
        BotCommand("deletett", "🗑 Xóa TikTok khỏi danh sách"),
        BotCommand("checknow", "🔄 Kiểm tra lại tất cả ngay"),
    ]
    try:
        await app.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    except Exception as e:
        logger.warning(f"Chưa cài đặt được menu bot command: {e}")

def main():
    if not os.path.exists("data/fb_tokens.json"):
        save_token_pool([])

    logger.info("Đang khởi tạo Telegram Bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation Handlers for Interactive Check Prompts
    fb_conv = ConversationHandler(
        entry_points=[
            CommandHandler("checkfb", prompt_fb),
            CallbackQueryHandler(prompt_fb, pattern="^btn_checkfb$")
        ],
        states={
            WAITING_FB_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fb_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel_check)]
    )

    ig_conv = ConversationHandler(
        entry_points=[
            CommandHandler("checkig", prompt_ig),
            CallbackQueryHandler(prompt_ig, pattern="^btn_checkig$")
        ],
        states={
            WAITING_IG_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ig_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel_check)]
    )

    tt_conv = ConversationHandler(
        entry_points=[
            CommandHandler("checktt", prompt_tt),
            CallbackQueryHandler(prompt_tt, pattern="^btn_checktt$")
        ],
        states={
            WAITING_TT_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tt_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel_check)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(fb_conv)
    app.add_handler(ig_conv)
    app.add_handler(tt_conv)

    # Add Facebook conversation (3 bước: UID → Note → Price)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("addfb", add_fb_cmd)],
        states={
            WAITING_ADD_FB:       [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_fb_uid)],
            WAITING_ADD_FB_NOTE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_fb_note)],
            WAITING_ADD_FB_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_fb_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel_check), CallbackQueryHandler(start, pattern="^btn_back_menu$")]
    ))
    # Add Instagram conversation (3 bước)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("addig", add_ig_cmd)],
        states={
            WAITING_ADD_IG:       [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_ig_uid)],
            WAITING_ADD_IG_NOTE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_ig_note)],
            WAITING_ADD_IG_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_ig_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel_check), CallbackQueryHandler(start, pattern="^btn_back_menu$")]
    ))
    # Add TikTok conversation (3 bước)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("addtt", add_tt_cmd)],
        states={
            WAITING_ADD_TT:       [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_tt_uid)],
            WAITING_ADD_TT_NOTE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_tt_note)],
            WAITING_ADD_TT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_tt_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel_check), CallbackQueryHandler(start, pattern="^btn_back_menu$")]
    ))
    # Delete Facebook conversation
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("deletefb", delete_fb_cmd)],
        states={WAITING_DEL_FB: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_del_fb_input)]},
        fallbacks=[CommandHandler("cancel", cancel_check)]
    ))
    # Delete Instagram conversation
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("deleteig", delete_ig_cmd)],
        states={WAITING_DEL_IG: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_del_ig_input)]},
        fallbacks=[CommandHandler("cancel", cancel_check)]
    ))
    # Delete TikTok conversation
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("deletett", delete_tt_cmd)],
        states={WAITING_DEL_TT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_del_tt_input)]},
        fallbacks=[CommandHandler("cancel", cancel_check)]
    ))

    app.add_handler(CallbackQueryHandler(list_cmd, pattern="^btn_list$"))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("checknow", checknow))

    # Auto check job
    if app.job_queue:
        app.job_queue.run_repeating(auto_check_all, interval=CHECK_INTERVAL_MINUTES * 60, first=10)
        app.job_queue.run_once(lambda _: asyncio.ensure_future(set_bot_commands(app)), when=1)
    else:
        logger.warning("Job queue không có sẵn. Vui lòng cài đặt python-telegram-bot[job-queue]")

    logger.info("Bot Live/Die Checker đang chạy...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
