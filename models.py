from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True)
    current_username = Column(String(100))
    current_firstname = Column(String(100))
    current_lastname = Column(String(100))
    messages = relationship("Message", back_populates="user")
    name_changes = relationship("UserNameChange", back_populates="user")

    def __lt__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.user_id < other.user_id

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.user_id == other.user_id

class UserNameChange(Base):
    __tablename__ = 'user_name_changes'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    old_username = Column(String(100))
    old_firstname = Column(String(100))
    old_lastname = Column(String(100))
    changed_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="name_changes")

class Chat(Base):
    __tablename__ = 'chats'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(String(50), unique=True)
    chat_type = Column(String(20))
    chat_name = Column(String(255))
    messages = relationship("Message", back_populates="chat")

    def __lt__(self, other):
        if not isinstance(other, Chat):
            return NotImplemented
        return str(self.chat_id) < str(other.chat_id)

    def __eq__(self, other):
        if not isinstance(other, Chat):
            return NotImplemented
        return str(self.chat_id) == str(other.chat_id)

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    chat_id = Column(Integer, ForeignKey('chats.id'))
    message_text = Column(Text)
    response_text = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="messages")
    chat = relationship("Chat", back_populates="messages") 