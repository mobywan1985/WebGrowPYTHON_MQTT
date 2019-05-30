
from sqlalchemy import DateTime, Boolean, Column, String, Integer, Date

from base import Base


class SensorLog(Base):
    __tablename__ = 'sensor_log'
    id=Column(Integer(), primary_key=True)
    temperature=Column('temperature', Integer)
    humidity=Column('humidity', Integer)
    log_date=Column('log_date', DateTime)

    def __init__(self, temperature, humidity, log_date):
        self.temperature = temperature
        self.humidity = humidity
        self.log_date  = log_date

