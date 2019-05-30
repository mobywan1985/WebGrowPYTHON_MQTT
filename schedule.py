
from sqlalchemy import DateTime, Boolean, Column, String, Integer, Date

from base import Base


class Schedule(Base):
    __tablename__ = 'schedule'
    id=Column(Integer(), primary_key=True)
    runTime=Column('runTime', String(32))
    onOff=Column('d_state', Integer)
    deviceID=Column('d_id', Integer)
    day_of_week=Column('d_dayofwk', String(30))
    
    def __init__(self, runTime, onOff, deviceID, day_of_week):
        self.runTime = runTime
        self.onOff = onOff
        self.deviceID  = deviceID
        self.day_of_week = day_of_week

