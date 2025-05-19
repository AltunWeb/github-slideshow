
import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from telegram import Update, ChatMember, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

draw_active = False
joined_users = set()
user_message_counts = {}
cooldown_users = {}
required_messages = 0
cooldown_duration = 60

# Sadece admin mi?
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]

# Çekilişi başlat
async def start_draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global draw_active, required_messages, joined_users, cooldown_duration

    if not await is_admin(update, context):
        return await update.message.reply_text("Bu komut sadece yöneticiler içindir.")

    if draw_active:
        return await update.message.reply_text("Zaten aktif bir çekiliş var.")

    try:
        cooldown_duration = int(context.args[0])
        required_messages = int(context.args[1])
    except:
        return await update.message.reply_text("Kullanım: /cekilis [saniye] [min_mesaj]")

    draw_active = True
    joined_users = set()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Katıl", callback_data="join_draw")]
    ])

    await update.message.reply_text(
        f"Çekiliş başladı! Katılmak için aşağıdaki butona tıklayın.
"
        f"Katılım için minimum {required_messages} mesaj gerekir.
"
        f"Kazanan kişi(ler) {cooldown_duration} saniye boyunca tekrar katılamaz.",
        reply_markup=keyboard
    )

# Butona tıklayınca çalışır
async def handle_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global draw_active

    if not draw_active:
        return await update.callback_query.answer("Aktif çekiliş yok.", show_alert=True)

    query = update.callback_query
    user_id = query.from_user.id
    now = datetime.now()

    if user_message_counts.get(user_id, 0) < required_messages:
        return await query.answer("Katılmak için yeterli mesajınız yok.", show_alert=True)

    if user_id in cooldown_users and cooldown_users[user_id] > now:
        kalan = (cooldown_users[user_id] - now).seconds
        return await query.answer(f"{kalan} saniye beklemelisin.", show_alert=True)

    if user_id in joined_users:
        return await query.answer("Zaten katıldınız.", show_alert=True)

    joined_users.add(user_id)
    await query.answer("Çekilişe başarıyla katıldınız!")

# Kazanan(lar)ı seç
async def pick_winners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global draw_active

    if not await is_admin(update, context):
        return await update.message.reply_text("Bu komut sadece yöneticiler içindir.")

    if not draw_active:
        return await update.message.reply_text("Aktif bir çekiliş yok.")

    if not joined_users:
        draw_active = False
        return await update.message.reply_text("Katılım olmadı, çekiliş iptal edildi.")

    try:
        count = int(context.args[0]) if context.args else 1
    except:
        return await update.message.reply_text("Kullanım: /kazanan [adet]")

    count = min(count, len(joined_users))
    winners = random.sample(list(joined_users), count)
    draw_active = False

    mesaj = "Kazananlar:
"
    for user_id in winners:
        cooldown_users[user_id] = datetime.now() + timedelta(seconds=cooldown_duration)
        user = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        mesaj += f"- {user.user.full_name}
"

    await update.message.reply_text(mesaj)

# Mesaj sayacını artır
async def count_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message_counts[user_id] = user_message_counts.get(user_id, 0) + 1

# Botu başlat
async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("cekilis", start_draw))
    app.add_handler(CommandHandler("kazanan", pick_winners))
    app.add_handler(CallbackQueryHandler(handle_join_callback, pattern="^join_draw$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, count_messages))

    print("Bot çalışıyor...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
