import random, string, io, qrcode
from functools import wraps
from telegram import Update
from backends import BotUsersBackend


def random_str(length=8) -> int:
    """Returns a random string of given length"""
    return "".join(random.choices(string.ascii_lowercase+string.digits,
                                  k=length))


def login_required(function):
    @wraps(function)
    async def wrapper(update: Update, context):
        username = update.effective_user.username
        user_qs = BotUsersBackend.user_exists(username)
        if user_qs.scalar() and user_qs.first().is_auth:
            return await function(update, context)
        await update.message.reply_text(
            "برای استفاده از این قابلیت لطفا ابتدا وارد حساب کاربری خود شوید")
        return chr(0)
    return wrapper


def generate_qr(data):
    qr = qrcode.QRCode(version=1,
                  box_size=10,
                  border=5)
    qr.add_data(data)
    qr.make()
    buff = io.BytesIO()
    qr_image = qr.make_image()
    qr_image.save(buff, format="PNG") 
    buff.seek(0)
    return buff
