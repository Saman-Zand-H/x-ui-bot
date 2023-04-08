import pathlib
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (Application,
                          PicklePersistence,
                          MessageHandler,
                          ConversationHandler,
                          CommandHandler,
                          ContextTypes,
                          filters)
from sqlalchemy.orm import sessionmaker

from configs import ACCESS_TOKEN, BOT_NAME
from models import engine, Base
from backends import BotUsersBackend, InboundsBackend
from utils import login_required, generate_qr


Session = sessionmaker(bind=engine)()
AUTH, PRO_DASH, DASH, LOGIN = [chr(i) for i in range(4)]
PRO_RULES = [
    "وضعیت اکانت ها",
    "اکانت ها",
    "خروج از حساب کاربری"
]
GUEST_RULES = [
    "ورود به حساب",
    "برنامه ها",
    "پیشنهاد رایگان"
]


async def auth(update: Update, context):
    username = update.effective_user.username
    user_qs = BotUsersBackend.user_exists(username)
    if user_qs.scalar() and user_qs.first().is_auth:
        markup = ReplyKeyboardMarkup([PRO_RULES],
                                     True)
        await update.message.reply_text("به حساب خود خوش آمدید", 
                                        reply_markup=markup)
        return PRO_DASH
    else:
        markup = ReplyKeyboardMarkup([GUEST_RULES], 
                                     True)
        await update.message.reply_text(f"خوش آمدی {update.effective_user.name}",
                                        reply_markup=markup)
        return DASH
    
    
async def dash(update: Update, context):
    username = update.effective_user.username
    op = update.message.text
    if op == GUEST_RULES[0]:
        markup = ReplyKeyboardMarkup([["لغو"]], resize_keyboard=True)
        await update.message.reply_text("لطفا کد ورود خود را وارد کنید",
                                        reply_markup=markup)
        return LOGIN
    
    elif op == GUEST_RULES[1]:
        await update.message.reply_text(
            "به طور کلی ما V2rayN رو برای اتصال پیشنهاد میکنیم اما ممکنه همیشه کار نکنه"
        )
        await update.message.reply_chat_action("upload_document")
        await update.message.reply_document(
            pathlib.Path.cwd().joinpath("NapsternetV53.0.0.apk"))
        await update.message.reply_text(
            "یا اگر از آی او اس استفاده میکنین:"
            "https://apps.apple.com/us/app/fair-vpn/id1533873488",
            reply_markup=ReplyKeyboardMarkup([GUEST_RULES],
                                             resize_keyboard=True)
        )
        return DASH
        
    elif op == GUEST_RULES[2]:
        msg = (
            "اینجا ما به تو یک حساب فیلترشکن یکماهه یک گیگ به صورت رایگان پیشنهاد میکنیم"
        )
        await update.message.reply_text(msg)
        guest = InboundsBackend.guest_inbound(username)
        await update.message.reply_text("لینک شما")
        await update.message.reply_text(guest.inbound.get_login_url())
        qr_buff = generate_qr(guest.inbound.get_login_url())
        markup = ReplyKeyboardMarkup([GUEST_RULES],
                                     resize_keyboard=True)
        await update.message.reply_photo(photo=qr_buff,
                                         caption="کیوآر کد اکانت شما",
                                         reply_markup=markup)
        return DASH
    

async def login(update: Update, context):
    username = update.effective_user.username
    login_code = update.message.text
    if BotUsersBackend.is_login_code_valid(login_code):
        BotUsersBackend(username).log_in_from_code(login_code)
        markup = ReplyKeyboardMarkup([PRO_RULES],
                                     resize_keyboard=True)
        await update.message.reply_text("ورود با موفقیت انجام شد",
                                        reply_markup=markup)
        return PRO_DASH
    else:
        markup = ReplyKeyboardMarkup([["لغو"]], resize_keyboard=True)
        await update.message.reply_text("کد ورود نامعتبر است. دوباره امتحان کن",
                                        reply_markup=markup)
        return LOGIN
    
    
@login_required
async def pro_dash(update: Update, context):
    answer = update.message.text
    username = update.effective_user.username
    if answer == PRO_RULES[0]:
        stats = BotUsersBackend(username).get_inbound_stats()
        await update.message.reply_text(
            "وضعیت های شما به شرح زیر است:"
        )
        markup = ReplyKeyboardMarkup([PRO_RULES],
                                     resize_keyboard=True)
        await update.message.reply_text(str(stats),
                                        reply_markup=markup)
        return PRO_DASH
    
    elif answer == PRO_RULES[1]:
        accounts = BotUsersBackend(username).get_connection_urls()
        for protocol, url in accounts.items():
            await update.message.reply_text(f"{protocol}:")
            await update.message.reply_text(url)
            qr = generate_qr(url)
            await update.message.reply_photo(qr)
        markup = ReplyKeyboardMarkup([PRO_DASH],
                                     resize_keyboard=True)
        await update.message.reply_text("دیگه چطوری میتونم بهت کمک کنم؟",
                                        reply_markup=markup)
        return PRO_DASH
        
    elif answer == PRO_RULES[2]:
        BotUsersBackend(username).log_user_out()
        markup = ReplyKeyboardMarkup([GUEST_RULES],
                                     resize_keyboard=True)
        await update.message.reply_text("با موفقیت خارج شدی",
                                        reply_markup=markup)
        return DASH


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    
    application = (
        Application
        .builder()
        .token(ACCESS_TOKEN)
        .persistence(PicklePersistence("vpn_bot_persistence"))
        .build()
    )
    conv_handler = ConversationHandler(
        entry_points=[auth],
        states={
            AUTH: [MessageHandler(filters.Text(PRO_RULES+GUEST_RULES), auth)],
            PRO_DASH: [MessageHandler(filters.Text(PRO_RULES), pro_dash)],
            DASH: [MessageHandler(filters.Text(GUEST_RULES), dash)],
            LOGIN: [MessageHandler(filters.ALL, login)]
        },
        name=BOT_NAME,
        persistent=True,
        fallbacks=[MessageHandler(filters.Text(PRO_RULES+GUEST_RULES), auth)]
    )
    application.add_handler(conv_handler)
    application.run_polling()
