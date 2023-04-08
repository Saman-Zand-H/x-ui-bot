import pickle, uuid, random, subprocess, shlex
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta as rel_delta
from sqlalchemy.orm import sessionmaker

from models import engine, BotUsers, TelegramUsers, GuestUsers, Inbounds
from configs import BOT_SESSIONS_PATH, SSL_PRIVATE, SSL_PUBLIC, URL


class BotUsersBackend:
    def __init__(self, username):
        self.Session = sessionmaker(bind=engine)()
        self.username = username
        self.instance = (
            self
            .Session
            .query(BotUsers)
            .join(TelegramUsers)
            .filter(TelegramUsers.username==username)
        )
        self.bot = None
        self._get_bot_ready()
        
    def _get_bot_ready(self):
        bot_qs = (
            self
            .Session
            .query(BotUsers)
            .join(TelegramUsers)
            .filter(TelegramUsers.username==self.username)
        )
        if bot_qs.scalar():
            self.bot = bot_qs.first()
        
    def log_in_from_code(self, login_code):
        bot_qs = self.Session.query(BotUsers).filter_by(login_code=login_code)
        if not bot_qs.scalar():
            return False
        if not self.instance.scalar():
            tel_user = TelegramUsers(username=self.username,
                                     is_auth=True,
                                     bot_id=bot_qs.first().id)
            self.Session.add(tel_user)
            self.Session.commit()
        else:
            self.instance.update({"is_auth": True}, synchronize_session=False)
            self.Session.commit()

    def log_user_out(self, username):
        Session = sessionmaker(bind=engine)()
        qs = Session.query(TelegramUsers).filter_by(username=username)
        if qs.scalar():
            self.instance.delete(synchronize_session=False)
            self.Session.commit()
    
    def get_connection_urls(self):
        qs = (
            self
            .Session
            .query(Inbounds)
            .join(TelegramUsers)
            .filter(TelegramUsers.username==self.username)
            .all()
        )
        return {i.protocol: i.get_login_url() for i in qs}
    
    def get_inbound_stats(self):
        inbounds = (
            self.Session
            .query(Inbounds)
            .join(TelegramUsers)
            .join(GuestUsers)
            .filter(TelegramUsers.username==self.username
                    or GuestUsers.username==self.username)
            .all()
        )
        stats = {
            i.remark: {
                "دانلود": i.down,
                "آپلود": i.up,
                "سهم کل": i.total,
                "حجم باقی مانده": i.remaining_traffic,
                "روز های باقی مانده": i.expires_in,
            }
            for i in inbounds
        }
        return stats
    
    @property
    def connected_usernames(self):
        bot = (
            self
            .Session
            .query(BotUsers)
            .join(TelegramUsers)
            .filter(TelegramUsers==self.username)
            .first()
        )
        return [i.username for i in bot]
    
    @property
    def remaining_traffic(self):
        if not self.bot:
            return False
        remainings = [i.total-(i.down+i.up) for i in self.bot.inbounds]
        return sum(remainings) if len(remainings) > 0 else 0
    
    @property
    def get_remaining_days(self):
        if not self.bot:
            return False
        remaining = {
            i.protocol: i.expires_in
            for i in self.bot.inbounds
        }
        return remaining
    
    @property
    def enabled_accounts(self):
        if not self.bot:
            return False
        enabled = [i for i in self.bot.inbounds if i.enable]
        return enabled if len(enabled) > 0 else None
    
    @classmethod
    def user_exists(cls, username):
        Session = sessionmaker(bind=engine)()
        return Session.query(TelegramUsers).filter_by(username=username)
    
    @classmethod
    def is_login_code_valid(cls, login_code):
        Session = sessionmaker(bind=engine)()
        return bool(Session.query(BotUsers).filter_by(login_code=login_code).scalar())
        
    
class InboundsBackend:
    def __init__(self, username):
        self.Session = sessionmaker(bind=engine)()
        self.inbounds = (
            self
            .Session
            .query(Inbounds)
            .join(GuestUsers)
            .join(TelegramUsers)
            .filter(
                GuestUsers.username==username
                or TelegramUsers.username==username
            )
            .all()
        )
        
    @classmethod
    def create_inbound(cls,
                       protocol,
                       remark,
                       quota=0,
                       expires_in=0):
        settings = {
            "clients": [
                {
                    "id": str(uuid.uuid4()),
                    "flow": "xtls-rprx-direct"
                }
            ],
            "decryption": "none",
            "fallbacks": []
        }
        stream_settings = {
            "network": "tcp",
            "security": "tls",
            "tlsSettings": {
                "serverName": URL.split(":")[0],
                "certificates": [
                    {
                        "certificateFile": SSL_PUBLIC,
                        "keyFile": SSL_PRIVATE
                    }
                ]
            },
            "tcpSettings": {
                "header": {
                    "type": "none"
                }
            }
        }
        sniffing = {
            "enabled": True,
            "destOverride": [
                "http",
                "tls"
            ]
        }
        if expires_in != 0:
            expiration = (datetime.now() + timedelta(days=expires_in)).timestamp()*1e3
        if quota != 0:
            quota *= 2**30
        Session = sessionmaker(bind=engine)()
        ports_in_use = [
            i.port 
            for i in Session.query(Inbounds).all()
        ]
        port = random.randint(1e4, 65353)
        while port in ports_in_use:
            port = random.randint(1e4, 65353)
        inbound = Inbounds(
            total=quota,
            remark=remark,
            enable=True,
            expiry_time=expiration,
            port=port,
            protocol=protocol,
            settings=settings,
            stream_settings=stream_settings,
            tag=f"inbound-{port}",
            sniffing=sniffing
        )
        Session.add(inbound)
        Session.commit()
        subprocess.run(
            shlex.split("systemctl restart x-ui"),
            check=True
        )
        return inbound
    
    @classmethod
    def guest_inbound(cls, username):
        Session = sessionmaker(bind=engine)()
        qs = (
            Session
            .query(Inbounds)
            .join(GuestUsers)
            .filter(GuestUsers.username==username)
        )
        if not qs.scalar():
            inbound = cls.create_inbound("vless", f"{username}_test", 1, 30)
            guest = GuestUsers(username=username, inbound_id=inbound.id)
            Session.add(guest)
            Session.commit()
            return guest
        elif (
            rel_delta(seconds=(datetime.now() - qs.first().guest.updated).total_seconds())
            >= rel_delta(months=1)
        ):
            Session.query(GuestUsers).filter_by(
                username=username).update({"updated": datetime.now()},
                                          synchronize_session=False)
            Session.commit()
        guest = Session.query(GuestUsers).filter_by(username=username).first()
        return guest
    
    
class UserSession(dict):    
    def __init__(self, username):
        self.username = username
        self.session_path = BOT_SESSIONS_PATH.joinpath(f"{self.username}.pickle")
        self._load_session()
    
    def _load_session(self):
        try:
            with open(self.session_path, "rb") as f:
                self.update(pickle.load(f))
        except FileNotFoundError:
            pass
        
    def _save(self):
        with open(self.session_path, "wb") as f:
            pickle.dump(self, f)
            
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._save()
    
    def __delitem__(self, key):
        super().__delitem__(key)
        self._save()
    
    def clear(self):
        super().clear()
        self._save()
    
    def pop(self, key, default=None):
        val = super().pop(key, default)
        self._save()
        return val
    