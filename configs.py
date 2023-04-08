import os, pathlib
from datetime import date
from dotenv import load_dotenv


env_path = pathlib.Path(__file__).with_name()
load_dotenv(env_path)

ACCESS_TOKEN = os.environ.get("BOT_TOKEN", None)
XUI_DB_PATH = os.environ.get("XUI_DB_PATH", "/etc/x-ui/x-ui.db")
LOG_PATH = f"/var/log/vpn_bot/{date.today().isoformat()}_run.log"
BOT_NAME = os.environ.get("BOT_NAME", None)
SSL_PUBLIC = os.environ.get("SSL_PUBLIC", None)
SSL_PRIVATE = os.environ.get("SSL_PRIVATE", None)
URL = os.environ.get("XUI_URL", None)
BOT_SESSIONS_PATH = os.environ.get("BOT_SESSIONS_PATH", 
                                   pathlib.Path.cwd().joinpath("sessions"))
LOGGING = {
    "version": 1,
    "handlers": {
        "file": {
            "level": "DEBUG",
            "class": "loggin.FileHandler",
            "filename": LOG_PATH,
            "formatter": "default"
        }
    },
    "formatters": {
        "default": {
            "format": "[%(levelname)s] - %(asctime)s (%(name)s %(lineno)s): %(message)s",
            "date_fmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "root": {
        "handlers": ["file"],
        "level": "DEBUG"
    }
}
