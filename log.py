# coding=utf-8

from sqlalchemy import DateTime, Boolean, Column, String, Integer, Date

from base import Base


class Log(Base):
    __tablename__ = 'log'
    id=Column(Integer(), primary_key=True)
    gpio=Column('d_gpio', Integer)
    dId=Column('d_id', Integer)
    state=Column('runstate', Boolean)
    runTime=Column('runtime', DateTime)
    protocol=Column('d_protocol', Integer)
    ip=Column('d_ip', String(16))

    def __init__(self, gpio, dId, state, runTime, protocol, ip):
        self.gpio = gpio
        self.dId = dId
        self.state = state
        self.runTime = runTime
        self.protocol = protocol
        self.ip = ip
        
