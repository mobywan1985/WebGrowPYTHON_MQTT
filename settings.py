# coding=utf-8

from sqlalchemy import DateTime, Boolean, Column, String, Integer, Date

from base import Base

class Settings(Base):
    __tablename__ = 'settings'
    id=Column(Integer(), primary_key=True)
    topic=Column('d_name', String(100))
    webcam=Column('e_webcam', Boolean)
    sensor=Column('e_sensor', Boolean)
    sensor_celsius=Column('e_cels', Boolean)
    sampling=Column('s_samp', Integer)
    gpio=Column('s_gpio', Integer)
    tadj=Column('s_tadj', Integer)
    hadj=Column('s_hadj', Integer)
    alert=Column('s_alert', Integer)
    alert_email=Column('s_alert_email', String(100))
    sender_email=Column('s_send_email', String(100))
    sender_password=Column('s_send_pw', String(100))

    def __init__(self, topic, wecam, sensor, sampling, gpio, tadj, hadj, sensor_celsius, alert, alert_email, sender_email, sender_password):
        self.topic = topic
        self.webcam = webcam
        self.sensor = sensor
        self.sampling = sampling
        self.gpio = gpio
        self.tadj = tadj
        self.hadj = hadj
        self.sensor_celsius = sensor_celsius
        self.alert = alert
        self.alert_email = alert_email
        self.sender_email = sender_email
        self.sender_password = sender_password
