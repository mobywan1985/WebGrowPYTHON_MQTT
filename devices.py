# coding=utf-8

from sqlalchemy import DateTime, Boolean, Column, String, Integer, Date

from base import Base


class Devices(Base):
    __tablename__ = 'devices'
    id=Column(Integer(), primary_key=True)
    gpio=Column('d_gpio', Integer)
    trigger=Column('d_trigger', Integer)
    t_change=Column('d_tchange', Boolean)
    h_change=Column('d_hchange', Boolean)
    temp=Column('d_temp', Integer)
    humid=Column('d_humid', Integer)
    interval=Column('d_interval', Integer)
    duration=Column('d_duration', Integer)
    timer=Column('d_timer', Integer)
    name=Column('d_name', String(32))
    run=Column('d_run', Boolean)
    state=Column('d_state', Boolean)
    lastRun=Column('d_lastrun', DateTime)
    protocol=Column('d_protocol', Integer)
    ip=Column('d_ip', String(16))

    def __init__(self, gpio, trigger, t_change, h_change, temp, humid, interval, duration, name, run, state, lastRun, protocol, ip, timer):
        self.gpio = gpio
        self.trigger = trigger
        self.t_change = t_change
        self.h_change = h_change
        self.temp  = temp
        self.humid = humid
        self.interval = interval
        self.duration = duration
        self.name = name
        self.run = run
        self.state = state
        self.lastRun = lastRun
        self.protocol = protocol
        self.ip = ip
        self.timer = timer