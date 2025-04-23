from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, PrimaryKeyConstraint, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from .config import config
from .utils import RoleEnum


Base = declarative_base()


class HW(Base):
    __tablename__ = 'hw'
    hw_id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    cluster = Column(String, nullable=False)
    name = Column(String, nullable=False)


class Pair(Base):
    __tablename__ = 'pair'
    hw_from_id = Column(Integer, ForeignKey('hw.hw_id', ondelete='CASCADE'), nullable=False)
    hw_to_id = Column(Integer, ForeignKey('hw.hw_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.user_id', ondelete='CASCADE'), nullable=False)
    label = Column(Integer, nullable=False)
    comment = Column(Text)

    __table_args__ = (
        PrimaryKeyConstraint('hw_from_id', 'hw_to_id', 'user_id'),
    )

    hw_from = relationship("HW", foreign_keys=[hw_from_id], backref="pairs_from")
    hw_to = relationship("HW", foreign_keys=[hw_to_id], backref="pairs_to")
    user = relationship("User", backref="pairs")


class User(Base):
    __tablename__ = 'user'
    user_id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # Store hashed passwords
    role = Column(Enum(RoleEnum), nullable=False)  # admin | teacher


engine = create_engine(config.DB_URI)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

default_user = User(user_id=0, username=config.ADMIN_LOGIN, password=config.ADMIN_PASSWORD, role=RoleEnum.admin)