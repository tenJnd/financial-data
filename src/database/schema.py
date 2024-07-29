from database_tools.adapters.postgresql import PostgresqlAdapter
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Table, Column, ForeignKey, String, Integer, Float, JSON, Boolean, DateTime, PickleType,
                        UniqueConstraint, and_)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import select, func


database = PostgresqlAdapter.from_env_vars()

metadata = database.get_metadata()
Base = declarative_base(metadata=metadata)


class Fgi(Base):

    __tablename__ = 'fgi'

    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(Integer)
    valueText = Column(String)
    timestamp = Column(DateTime)
