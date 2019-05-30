# coding=utf-8

from sqlalchemy import Column, String, Integer, Date

from base import Base


class GPIO(Base):
    __tablename__ = 'gpio'
    id=Column(Integer(), primary_key=True)
    gpio=Column('gpio', Integer)

    def __init__(self, gpio):
        self.gpio = gpio


