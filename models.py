"""
    A file containing models for managing x-ui database at /etc/x-ui/x-ui.db
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, 
                        Integer,
                        ForeignKey,
                        DateTime,
                        Text,
                        Boolean,
                        create_engine)
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
import json

from utils import random_str
from configs import XUI_DB_PATH, URL


engine = create_engine(f"sqlite+pysqlite:///{XUI_DB_PATH}", echo=True)
Base = declarative_base()


class Inbounds(Base):
    __tablename__ = "inbounds"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=1, autoincrement=True)
    up = Column(Integer, default=0)
    down = Column(Integer, default=0)
    # total is the quota
    total = Column(Integer, default=0)
    remark = Column(Text)
    enable = Column(Boolean, default=True)
    # expiry_time is timestamp*1000
    expiry_time = Column(Integer)
    listen = Column(Text, default="")
    port = Column(Integer)
    protocol = Column(Text)
    settings = Column(Text)
    stream_settings = Column(Text)
    tag = Column(Text)
    sniffing = Column(Text)
    
    bot_users = relationship("BotUsers",
                             secondary="users_inbounds_relation",
                             backref="inbounds")
    guest = relationship("GuestUsers", 
                         back_populates="inbound", 
                         uselist=False)
    
    @property
    def remaining_traffic(self) -> int:
        return self.total - (self.down + self.up)
    
    @property
    def expires_in(self) -> int:
        """Returns number of days left to the expirations."""
        expiry = datetime.fromtimestamp(self.expiry_time*1e-3)
        return (datetime.now()-expiry).days
    
    def get_login_url(self, host_address:str=URL.split(":")[0]):
        """Returns v2ray login url. host_address example: example.com:666"""
        try:
            uuid = json.loads(self.settings)["clients"]["id"]
        except Exception as e:
            print(
                f"[!] a corruption was detected for {self.__repr__()}:\n{e}"
            )
            return
        return (
            f"{self.protocol}://{uuid}@{host_address}?"
            "security=tls&encryption=none&"
            "headerType=none&type=tcp&"
            f"sni={host_address.split(':')[0]}#{self.remark}"
        )
        
    
class BotUsers(Base):
    __tablename__ = "bot_users"
    id = Column(Integer, primary_key=True)
    login_code = Column(Text, default=random_str)
    accounts = relationship("TelegramUsers", backref="bot")
    inbounds = relationship("Inbounds", 
                            secondary="users_inbounds_relation", 
                            backref="bot_users")
    

class GuestUsers(Base):
    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True, index=True)
    created = Column(DateTime, default=datetime.now)
    updated = Column(DateTime, default=datetime.now)
    inbound_id = Column(Integer, ForeignKey("inbounds.id"))
    inbound = relationship("Inbounds", back_populates="inbound")


class TelegramUsers(Base):
    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True, index=True)
    bot_id = Column(Integer, ForeignKey("bot_users.id"))
    is_auth = Column(Boolean, default=False)


class UsersInboundsRelation(Base):
    __tablename__ = "users_inbounds_relation"
    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey("bot_users.id"), 
                    primary_key=True)
    inbound_id = Column(Integer, ForeignKey("inbounds.id"), 
                        primary_key=True)
