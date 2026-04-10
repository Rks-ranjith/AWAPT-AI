from sqlalchemy import Column, Integer, String, Boolean, Enum
import enum
from awap.core.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ATTACKER = "attacker"
    VIEWER = "viewer"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True)
