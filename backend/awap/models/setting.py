from sqlalchemy import Column, String, Boolean
from .base import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(String, primary_key=True, default="default")
    email_enabled = Column(Boolean, default=False)
    email_alert = Column(String, nullable=True)
    slack_enabled = Column(Boolean, default=False)
    slack_webhook = Column(String, nullable=True)
    telegram_enabled = Column(Boolean, default=False)
    telegram_token = Column(String, nullable=True)
    telegram_chat_id = Column(String, nullable=True)
