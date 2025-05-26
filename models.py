from sqlalchemy import Column, String, Integer, Date, Boolean
from db import Base


class House(Base):
    __tablename__ = "houses"

    id = Column(Integer, primary_key=True, index=True)
    position = Column(String)
    state_type = Column(String)
    state_date = Column(String)
    inspection_date = Column(String)
    link = Column(String)
    actual = Column(Boolean, default=True)
