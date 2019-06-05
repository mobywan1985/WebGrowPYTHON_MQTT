#!/usr/bin/env python
# coding=utf-8

# 1 - imports
import RPi.GPIO as RGPIO
from apscheduler.schedulers.background import BackgroundScheduler
from base import Session
from devices import Devices
from log import Log
from settings import Settings
from sensorlog import SensorLog
from gpio import GPIO
from schedule import Schedule
from mailer import AlertMailer
import time, datetime, json, os
from sockethelper import SocketHelper
from sqlalchemy import func, desc
import Adafruit_DHT
import logging
import requests
import paho.mqtt.client as mqtt
import random
time.sleep(10)
DEBUG = False

TRIGGER_NONE = 0
TRIGGER_INTERVAL = 10
TRIGGER_TIMER = 15
TRIGGER_TEMPERATURE = 20
TRIGGER_HUMIDITY = 25
TRIGGER_SCHEDULE = 30


PROTOCOL_GPIO = 0
PROTOCOL_SONOFF = 10
PROTOCOL_TASMOTA = 20

log = logging.getLogger('apscheduler.scheduler')
log.setLevel(logging.WARNING)  # DEBUG

fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
h = logging.StreamHandler()
h.setFormatter(fmt)
log.addHandler(h)

log = logging.getLogger('apscheduler.executors.default')
log.setLevel(logging.WARNING)  # DEBUG

fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
h = logging.StreamHandler()
h.setFormatter(fmt)
log.addHandler(h)

#Setup GPIO
RGPIO.setmode(RGPIO.BCM)
RGPIO.setwarnings(False)

#Background scheduler for all jobs#
job_defaults = {
    'coalesce': True,
    'misfire_grace_time': 3
}
device_scheduler = BackgroundScheduler(daemon=True, job_defaults=job_defaults)

session = Session()
devices = session.query(Devices).all()
settings = session.query(Settings).order_by(desc(Settings.id)).limit(1)
sampling_rate = settings[0].sampling
sensor_gpio = settings[0].gpio
sensor_tadj = settings[0].tadj
sensor_hadj = settings[0].hadj
sensor_celsius= settings[0].sensor_celsius
enable_sampling = settings[0].sensor
service_topic = settings[0].topic
device_objects = dict()
mqttc = mqtt.Client("py_controller",transport='websockets')
current_temp = 0
current_humidity = 0
email_alerts = settings[0].alert
alert_mailer = AlertMailer(settings[0].alert_email, settings[0].sender_email, settings[0].sender_password)

dht_sensor_job = None
def read_sensor():
    try:
       global current_temp
       global current_humidity
       global sensor_tadj 
       global sensor_hadj
       
       if(DEBUG):
          temperature1 = random.randint(10,32)
          temperature2 = random.randint(10,32)
          temperature3 = random.randint(10,32)
          temperature4 = random.randint(10,32)
          humidity1 = random.randint(30,70)
          humidity2 = random.randint(30,70)
          humidity3 = random.randint(30,70)
          humidity4 = random.randint(30,70)
       else:
          humidity1, temperature1 = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, sensor_gpio)
          time.sleep(15)
          humidity2, temperature2 = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, sensor_gpio)
          time.sleep(15)
          humidity3, temperature3 = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, sensor_gpio)
          time.sleep(15)
          humidity4, temperature4 = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, sensor_gpio)
       
       temps = [temperature1, temperature2, temperature3, temperature4]       
       temps.sort()
       humiditys = [humidity1, humidity2, humidity3, humidity4]
       humiditys.sort()
       
       print(temps)
       print(humiditys)
       if humiditys[2] is not None and temps[2] is not None:
          print('Success reading sensor!')
          if(humiditys[2] > 100):
             print('Bogus Read - Throwing results')
          else:
             if(sensor_celsius):
                current_temp = (temps[2])+sensor_tadj
             else:
                current_temp = (temps[2] * 9/5.0 + 32)+sensor_tadj
             current_humidity = humiditys[2] + sensor_hadj
       else:
          print('Failed to get reading. Try again!')

    except:
       print('Error Occured!')
       
    #if(DEBUG):
    #   current_temp = 75.5555555555
    #   current_humidity = 50
       
       
    status = [current_temp, current_humidity, os.getpid()]
    log_sensor()
    mqttc.publish("php_return_status",json.dumps(status))



def log_sensor():
    if current_temp != 0 and current_humidity != 0:
       log_session = Session()
       now = datetime.datetime.now()
       slog = SensorLog(temperature = current_temp, humidity = current_humidity, log_date = now)
       log_session.add(slog)
       log_session.commit()
       log_session.close()

def getScheduler():
    global device_scheduler
    return device_scheduler

class Device_Object:
    id = int()
    gpio =  int()
    trigger = int()
    temperature_change = None
    humidity_change = None
    temperature = int()
    humidity = int()
    interval = int()
    duration = int()
    timer = int()
    ip = ''
    protocol = int()
    name = ''
    run = None
    state = None
    last_run_time = None
    mqttObj = None    
    interval_job = None
    temperature_job = None
    humidity_job = None
    timer_job = None
    schedule_jobs = []

    def __init__(self, id, gpio, trigger, t_change, h_change, temp, humid, interval, duration, name, run, state, lastRun, protocol, ip, timer):
        self.id = id
        self.gpio = gpio
        self.trigger = trigger
        self.temperature_change = t_change
        self.humidity_change = h_change
        self.temperature  = temp
        self.humidity = humid
        self.interval = interval
        self.duration = duration
        self.timer = timer
        self.name = name
        self.run = run
        self.state = state
        self.last_run_time = lastRun
        self.interval_job = None
        self.temperature_job = None
        self.humidity_job = None
        self.timer_job = None
        self.schedule_jobs = []
        self.protocol = protocol
        self.ip = ip
        self.load_triggers_from_mysql()
        global mqttc
        self.mqttObj = mqttc
        
                
    def print_name(self):
        print('Loading Device: '+self.name)

    def add_schedule_job(self, schedule_id, schedule_state, schedule_runtime, schedule_dow):
        if(self.protocol == PROTOCOL_GPIO):
           job_name = self.gpio
        elif(self.protocol == PROTOCOL_TASMOTA):
           job_name = self.ip
        job = getScheduler().add_job(self.run_schedule, 'cron', args=[schedule_state],hour=int(schedule_runtime.hour), minute=int(schedule_runtime.minute),second=int(schedule_runtime.second),day_of_week=schedule_dow, id='S'+str(schedule_id), name=str(job_name))
        self.schedule_jobs.append(job)
        if self.run == 0:
           job.pause()
        
    
    def add_interval_job(self):
        job = getScheduler().add_job(self.run_device ,'interval', seconds=self.interval, id=str(self.id), name=self.name)
        self.interval_job = job
        if self.run == 0:
           job.pause()
           
    def add_timer_job(self):
        job = getScheduler().add_job(self.run_timer_device ,'interval', seconds=50000, id='TMR'+str(self.id), name=self.name)
        self.timer_job = job;
        if self.run == 0:
           job.pause()
    
    def add_temperature_job(self):
        job = getScheduler().add_job(self.check_temp ,'interval', seconds=sampling_rate, id='T'+str(self.id), name=self.name)
        self.temperature_job = job
        if self.run == 0:
           job.pause()
    
    def add_humidity_job(self):
        job = getScheduler().add_job(self.check_humid ,'interval', seconds=sampling_rate, id='H'+str(self.id), name=self.name)
        self.humidity_job = job
        if self.run == 0:
           job.pause()

    def load_triggers_from_mysql(self):
        try:
          device_session = Session()
          if self.trigger == TRIGGER_INTERVAL:
             self.add_interval_job()
          if self.trigger == TRIGGER_TIMER:
             print(self.timer_job)
             self.add_timer_job()   
          if self.trigger == TRIGGER_TEMPERATURE:
             self.add_temperature_job()
          if self.trigger == TRIGGER_HUMIDITY:
             self.add_humidity_job()
          if self.trigger == TRIGGER_SCHEDULE:
             schedule = device_session.query(Schedule).filter(Schedule.deviceID == self.id)
             for time in schedule:
                 self.add_schedule_job(time.id, time.onOff, time.runTime, time.day_of_week)
          device_session.close()
        except:
          print('There was an error loading. Continuing anyway.')


    def reload_triggers_from_mysql(self):
        try:
          if (self.interval_job is not None):
              self.interval_job.remove()
              self.interval_job = None
          if (self.temperature_job is not None):
              self.temperature_job.remove()
              self.temerature_job = None
          if (self.humidity_job is not None):
              self.humidity_job.remove()        
              self.humidity_job = None
          if (self.timer_job is not None):
              self.timer_job.remove()
              self.timer_job = None
          print(getScheduler().print_jobs())
          for key, job in enumerate(self.schedule_jobs):
                job.remove()
          self.schedule_jobs = []
          if(self.run == 1):
             self.run = 0
             self.toggle_off()
          self.load_triggers_from_mysql()
        except:
          print('There was an error reloading. Continuing anyway.')

    def run_timer_device(self):
        global device_scheduler
        print("Running this timer job")
        
        self.toggle_on()
        if(self.protocol == PROTOCOL_GPIO):
           print(str(datetime.datetime.now())+': Running Job #'+str(self.id)+' on GPIO '+str(self.gpio)+' for '+str(self.timer)+' seconds')
        elif(self.protocol == PROTOCOL_TASMOTA):
           print(str(datetime.datetime.now())+': Running Job #'+str(self.id)+' on Topic '+str(self.ip)+' for '+str(self.timer)+' seconds')
        device_scheduler.add_job(self.stop_device,'interval', id='del'+str(self.id), seconds=self.timer, coalesce=True)

    def run_device(self):
        global device_scheduler
        self.toggle_on()
        if(self.protocol == PROTOCOL_GPIO):
           print(str(datetime.datetime.now())+': Running Job #'+str(self.id)+' on GPIO '+str(self.gpio)+' for '+str(self.duration)+' seconds')
        elif(self.protocol == PROTOCOL_TASMOTA):
           print(str(datetime.datetime.now())+': Running Job #'+str(self.id)+' on Topic '+str(self.ip)+' for '+str(self.duration)+' seconds')
        device_scheduler.add_job(self.stop_device,'interval', id='del'+str(self.id), seconds=self.duration, coalesce=True)
        
    def stop_device(self):
        global device_scheduler
        if(self.trigger == TRIGGER_TIMER):
           self.stop_device_request()
           tmpsession = Session()
           tmpsession.query(Devices).filter(Devices.id == int(self.id)).update({'run': 0})
           tmpsession.commit()
           tmpsession.close()
        else:
           self.toggle_off()#toggle_off(cron_jobs[jobid]['gpio'], jobid)
        if(self.protocol == PROTOCOL_GPIO):
           print(str(datetime.datetime.now())+': Stopping Job #'+str(self.id)+' on GPIO '+str(self.gpio))
        elif(self.protocol == PROTOCOL_TASMOTA):
           print(str(datetime.datetime.now())+': Stopping Job #'+str(self.id)+' on Topic '+str(self.ip))
        device_scheduler.remove_job('del'+str(self.id))
        

           
    def run_schedule(self, state):
        if state == 0:
           print('Toggle off')
           self.toggle_off()#        toggle_off(schedule_jobs[int(jobid)]['gpio'], dID)
        else:
           print('Toggle on')
           self.toggle_on()#        toggle_on(schedule_jobs[int(jobid)]['gpio'], dID)
        if(self.protocol == PROTOCOL_GPIO):
           print(str(datetime.datetime.now())+': Running Job #'+str(self.id)+' on GPIO '+str(self.gpio)+" setting to state "+str(state))
        elif(self.protocol == PROTOCOL_TASMOTA):
           print(str(datetime.datetime.now())+': Running Job #'+str(self.id)+' on Topic '+str(self.ip)+" setting to state "+str(state))

    def run_device_request(self):
         if(self.state == 1):
            self.toggle_off()
         global enable_sampling
         if (self.trigger == TRIGGER_INTERVAL):
             self.interval_job.resume()
         if (self.trigger == TRIGGER_TIMER):
             self.timer_job.modify(next_run_time=datetime.datetime.now())
             
         if (self.trigger == TRIGGER_TEMPERATURE):
             if(enable_sampling == True):
                self.temperature_job.resume()
         if (self.trigger == TRIGGER_HUMIDITY):
             if(enable_sampling == True):
                self.humidity_job.resume()
         if(self.trigger == TRIGGER_SCHEDULE):
             for job in self.schedule_jobs:
                 job.resume()
         self.run = 1
         tmpsession = Session()
         tmpsession.query(Devices).filter(Devices.id == int(self.id)).update({'run': 1})
         tmpsession.commit()
         tmpsession.close()


        
    def stop_device_request(self):
         if(self.state == 1):
            self.toggle_off()
         try:
            if (self.trigger == TRIGGER_INTERVAL):
                self.interval_job.pause()
            if (self.trigger == TRIGGER_TIMER):
                self.timer_job.pause()
            if (self.trigger == TRIGGER_TEMPERATURE):
                self.temperature_job.pause()
            if (self.trigger == TRIGGER_HUMIDITY):
                self.humidity_job.pause()
            if(self.trigger == TRIGGER_SCHEDULE):
                for job in self.schedule_jobs:
                    job.pause()
         except:
            print('Error stopping')
         self.run = 0
         tmpsession = Session()
         tmpsession.query(Devices).filter(Devices.id == int(self.id)).update({'run': 0})
         tmpsession.commit()
         tmpsession.close()

    
    def gpio_protocol_off(self):
        print('Turning off :'+str(self.gpio))
        RGPIO.output(int(self.gpio), RGPIO.HIGH)
    def gpio_protocol_on(self):
        print('Turning on :'+str(self.gpio))
        RGPIO.output(int(self.gpio), RGPIO.LOW)
    
    def tasmoto_protocol_on(self):
        try:
           self.mqttObj.publish("cmnd/"+self.ip+"/POWER","1")
        except:
           print('error')
    def tasmoto_protocol_off(self):
        try:
           self.mqttObj.publish("cmnd/"+self.ip+"/POWER","0")
        except:
           print('error')
    def sonoff_protocol_on(self):
        print('SonOff not implemented! Skipping! IP:'+self.ip)
    def sonoff_protocol_off(self):
        print('SonOff not implemented! Skipping! IP:'+self.ip)

    def tasmota_state_off(self):
         if(self.state == 1):
            self.state = 0
            tmpsession = Session()
            now = datetime.datetime.now()
            tmpsession.query(Devices).filter(Devices.id == int(self.id)).update({'state': 0})
            if(self.protocol == PROTOCOL_TASMOTA):
               dlog = Log(runTime = now, state = 0, dId = int(self.id), gpio=None, protocol=20, ip=self.ip)
               tmpsession.add(dlog)
            tmpsession.commit()
            tmpsession.close()
    def tasmota_state_on(self):
         if(self.state == 0):
            self.state = 1
            tmpsession = Session()
            now = datetime.datetime.now()
            tmpsession.query(Devices).filter(Devices.id == int(self.id)).update({"lastRun": now, 'state': 1})
            if(self.protocol == PROTOCOL_TASMOTA):
               dlog = Log(runTime = now, state = 1, dId = int(self.id), gpio=None, protocol=20, ip=self.ip)
               tmpsession.add(dlog)
            tmpsession.commit()
            tmpsession.close()
          
    def toggle_off(self):
         if(self.state == 1):
            self.state = 0
            tmpsession = Session()
            now = datetime.datetime.now()
            tmpsession.query(Devices).filter(Devices.id == int(self.id)).update({'state': 0})
            if(self.protocol == PROTOCOL_GPIO):
               self.gpio_protocol_off()
               dlog = Log(runTime = now, state = 0, dId = int(self.id), gpio =int(self.gpio), protocol=0, ip='')
               tmpsession.add(dlog)
            elif(self.protocol == PROTOCOL_SONOFF):
               self.sonoff_protocol_off()
               dlog = Log(runTime = now, state = 0, dId = int(self.id), gpio=None, protocol=10, ip=self.ip)
               tmpsession.add(dlog)
            elif(self.protocol == PROTOCOL_TASMOTA):
               self.tasmoto_protocol_off()
               dlog = Log(runTime = now, state = 0, dId = int(self.id), gpio=None, protocol=20, ip=self.ip)
               tmpsession.add(dlog)
            tmpsession.commit()
            tmpsession.close()
            global service_topic
            mqttc.publish("stat/"+service_topic+"/device/"+str(self.id)+"/POWER","OFF", qos=0, retain=True)

         
    def toggle_on(self):
         if(self.state == 0):
            self.state = 1
            tmpsession = Session()
            now = datetime.datetime.now()
            tmpsession.query(Devices).filter(Devices.id == int(self.id)).update({"lastRun": now, 'state': 1})
            if(self.protocol == PROTOCOL_GPIO):
               self.gpio_protocol_on()
               dlog = Log(runTime = now, state = 1, dId = int(self.id), gpio = int(self.gpio), protocol=0, ip='')
               tmpsession.add(dlog)
            elif(self.protocol == PROTOCOL_SONOFF):
               self.sonoff_protocol_on()
               dlog = Log(runTime = now, state = 1, dId = int(self.id), gpio=None, protocol=10, ip=self.ip)
               tmpsession.add(dlog)
            elif(self.protocol == PROTOCOL_TASMOTA):
               self.tasmoto_protocol_on()
               dlog = Log(runTime = now, state = 1, dId = int(self.id), gpio=None, protocol=20, ip=self.ip)
               tmpsession.add(dlog)
            tmpsession.commit()
            tmpsession.close()
            global service_topic
            mqttc.publish("stat/"+service_topic+"/device/"+str(self.id)+"/POWER","ON", qos=0, retain=True)
            

    def delete_device(self):
        if (self.interval_job is not None):
            self.interval_job.remove()
            self.interval_job = None
        if (self.temperature_job is not None):
            self.temperature_job.remove()
            self.temerature_job = None
        if (self.humidity_job is not None):
            self.humidity_job.remove()
            self.humidity_job = None
        if (self.timer_job is not None):
            self.timer_job.remove()
            self.timer_job = None    
        for key, job in enumerate(self.schedule_jobs):
              job.remove()
        self.schedule_jobs = []
        del self
        
    def disable_sensor_device(self):
        if (self.temperature_job is not None):
            self.temperature_job.pause()
        if (self.humidity_job is not None):
            self.humidity_job.pause()

    def enable_sensor_device(self):
        if(self.run):
            if (self.temperature_job is not None):
                self.temperature_job.reschedule(trigger='interval', seconds=sampling_rate)
                self.temperature_job.resume()
                
            if (self.humidity_job is not None):
                self.humidity_job.reschedule(trigger='interval', seconds=sampling_rate)
                self.humidity_job.resume()


    def check_temp(self):
        global current_temp
        try:
              if(self.temperature_change):
                 if(current_temp > self.temperature):
                    if(self.state == 0):
                       print('Temp alert! Temperature is greater than required and %s has turned on.' % self.name)
                       if(email_alerts == 1):
                          alert_mailer.send_mail(self.name, 'Time: '+str(datetime.datetime.now())+'\nTemperature Alert! Temperature: '+str(round(current_temp,1))+'F\nTemperature Limit Greater Than: '+str(self.temperature)+'F')
                       self.toggle_on()#toggle_on(temp_jobs[jobid]['gpio'], jobid)
                 else:
                    if(self.state == 1):
                       print('No temp alert, turning off')
                       self.toggle_off()#toggle_off(temp_jobs[jobid]['gpio'], jobid)
              else:
                 if(current_temp < self.temperature):
                    if(self.state == 0):
                       print('Temp alert! Temperature is less than required and %s has turned on.' % self.name)
                       self.toggle_on()#toggle_on(temp_jobs[jobid]['gpio'], jobid)
                       if(email_alerts == 1):
                          alert_mailer.send_mail(self.name, 'Time: '+str(datetime.datetime.now())+'\nTemperature Alert! Temperature: '+str(round(current_temp,1))+'F\nTemperature Limit Less Than: '+str(self.temperature)+'F')
                 else:
                    if(self.state == 1):
                       print('No temp alert, turning off')
                       self.toggle_off()#toggle_off(temp_jobs[jobid]['gpio'], jobid)
        except Exception, e:
               print('Error: '+ str(e))
    
    def check_humid(self):
        global current_humidity
        try:
              if(self.humidity_change):
                 if(current_humidity > self.humidity):
                    if(self.state == 0):
                       print('Humidity alert! Humidity is greater than required and %s has turned on.' % self.name)
                       self.toggle_on()#toggle_on(temp_jobs[jobid]['gpio'], jobid)
                       if(email_alerts == 1):
                          alert_mailer.send_mail(self.name, 'Time: '+str(datetime.datetime.now())+'\nHumidity Alert! Humidity: '+str(round(current_humidity,1))+'%\nHumidity Limit Greater Than: '+str(self.humidity)+'%')
                 else:
                    if(self.state == 1):
                       print('No humidity alert, turning off')
                       self.toggle_off()#toggle_off(temp_jobs[jobid]['gpio'], jobid)
              else:
                 if(current_humidity < self.humidity):
                    if(self.state == 0):
                       print('Humidity alert! Humidity is less than required and %s has turned on.' % self.name)
                       self.toggle_on()#toggle_on(temp_jobs[jobid]['gpio'], jobid)
                       if(email_alerts == 1):
                          alert_mailer.send_mail(self.name, 'Time: '+str(datetime.datetime.now())+'\nHumidity Alert! Humidity: '+str(round(current_humidity,1))+'%\nHumidity Limit Less Than: '+str(self.humidity)+'%')
                 else:
                    if(device.state == 1):
                       print('No humdity alert, turning off')
                       self.toggle_off()#toggle_off(temp_jobs[jobid]['gpio'], jobid)
                            
        except:
            print('Error checking humidity')  
            


#Load Devices
def make_device(id, gpio, trigger, t_change, h_change, temp, humid, interval, duration, name, run, state, lastRun, protocol, ip, timer):
    device_obj = Device_Object(id, gpio, trigger, t_change, h_change, temp, humid, interval, duration, name, run, state, lastRun, protocol, ip, timer)
    return device_obj
for device in devices:
    RGPIO.setup(int(device.gpio), RGPIO.OUT)
    RGPIO.output(int(device.gpio), RGPIO.HIGH)
    device_objects.update({device.id : {'object' : make_device(device.id, device.gpio, device.trigger, device.t_change, device.h_change, device.temp, device.humid, device.interval, device.duration, device.name, device.run, device.state, device.lastRun, device.protocol, device.ip, device.timer)}})

#Load Sensor
dht_sensor_job = getScheduler().add_job(read_sensor, 'interval', seconds=sampling_rate, id='sensor1', name='Sensor Read')
#dht_sensor_logger_job = getScheduler().add_job(log_sensor, 'interval', seconds=300, id='sensor_logger1', name='Sensor Logging')
if(enable_sampling == True):
#   read_sensor()
   dht_sensor_job.resume()
#   dht_sensor_logger_job.resume()
else:
   dht_sensor_job.pause()
#   dht_sensor_logger_job.pause()

device_scheduler.start()
session.close()
for key in device_objects.keys():
    device_objects[key]['object'].print_name()
print(getScheduler().print_jobs())

def print_scheduler():
    print(getScheduler().print_jobs())
  
def reload_settings():
    session = Session()
    settings = session.query(Settings).order_by(desc(Settings.id)).limit(1)
    global sampling_rate
    global sensor_gpio
    global enable_sampling
    global service_topic
    global sensor_tadj
    global sensor_hadj
    global sensor_celsius
    sampling_rate = settings[0].sampling
    sensor_gpio = settings[0].gpio
    enable_sampling = settings[0].sensor
    sensor_celsius = settings[0].sensor_celsius
    mqttc.unsubscribe("cmnd/"+service_topic+"/+/+/+")
    mqttc.unsubscribe("stat/"+service_topic+"/+/+/+")
    service_topic = settings[0].topic
    mqttc.subscribe("cmnd/"+service_topic+"/+/+/+", 0)
    mqttc.subscribe("stat/"+service_topic+"/+/+/+", 0)
    sensor_tadj = settings[0].tadj
    sensor_hadj = settings[0].hadj
    session.close()
    
    

    
    if(enable_sampling == True):
       dht_sensor_job.reschedule(trigger='interval', seconds=sampling_rate)
       dht_sensor_job.resume()
       #dht_sensor_logger_job.resume()
    if(enable_sampling == False):
       dht_sensor_job.pause()
       #dht_sensor_logger_job.pause()
    for key in device_objects.keys():
       if(enable_sampling == False):
          device_objects[key]['object'].disable_sensor_device()
       if(enable_sampling == True):
          device_objects[key]['object'].enable_sensor_device()
    




#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2010-2013 Roger Light <roger@atchoo.org>
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Distribution License v1.0
# which accompanies this distribution.
#
# The Eclipse Distribution License is available at
#   http://www.eclipse.org/org/documents/edl-v10.php.
#
# Contributors:
#    Roger Light - initial implementation
# Copyright (c) 2010,2011 Roger Light <roger@atchoo.org>
# All rights reserved.

# This shows a simple example of an MQTT subscriber.

# If you want to use a specific client id, use
# mqttc = mqtt.Client("client-id")
# but note that the client id must be unique on the broker. Leaving the client
# id parameter empty will generate a random id for you.
#mqttc = mqtt.Client("py_controller")

def on_connect(mqttc, obj, flags, rc):
    print("rc: " + str(rc))


def on_message(mqttc, obj, msg):
    if(DEBUG):
       print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    global service_topic
    global device_objects    
    if msg.topic.startswith("stat/") and msg.topic.endswith("POWER"):
       topics = msg.topic.split("/")
       for key in device_objects.keys():
           if(device_objects[key]['object'].ip == topics[1]):
                 if(msg.payload == "ON" and device_objects[key]['object'].state == 0):
                    device_objects[key]['object'].tasmota_state_on()
                 if(msg.payload == "OFF" and device_objects[key]['object'].state == 1):
                    device_objects[key]['object'].tasmota_state_off()                    
    if msg.topic.startswith("cmnd/"+service_topic+"/"):
       topics = msg.topic.split("/")
       has_gpio = False
       if(topics[2] == 'gpio'):
          for key in device_objects.keys():
              if(device_objects[key]['object'].protocol == PROTOCOL_GPIO and device_objects[key]['object'].gpio == int(topics[3])):
                  has_gpio = True
                  if(topics[4] == "POWER"):
                     if(msg.payload == "ON" or msg.payload == "1"):
                        device_objects[key]['object'].toggle_on()
                     if(msg.payload == "OFF" or msg.payload == "0"):
                        device_objects[key]['object'].toggle_off()
          if(has_gpio == False):
              if(topics[4] == "POWER"):
                 if(msg.payload == "ON" or msg.payload == "1"):
                    print('Turning on gpio :'+str(topics[3]))
                    RGPIO.output(int(topics[3]), RGPIO.LOW)
                 if(msg.payload == "OFF" or msg.payload == "0"):
                    print('Turning off gpio:'+str(topics[3]))
                    RGPIO.output(int(topics[3]), RGPIO.HIGH)
       if(topics[2] == 'device'):
          for key in device_objects.keys():
              if(device_objects[key]['object'].id == int(topics[3])):
                 if(msg.payload == "ON" or msg.payload == "1"):
                    if(topics[4] == "POWER"):
                       device_objects[key]['object'].toggle_on()
                    if(topics[4] == "RUN"):
                       device_objects[key]['object'].run_device_request()
                       print_scheduler()
                 if(msg.payload == "OFF" or msg.payload == "0"):
                    if(topics[4] == "POWER"):
                       device_objects[key]['object'].toggle_off()
                    if(topics[4] == "RUN"):
                       device_objects[key]['object'].stop_device_request()
                       print_scheduler()
    if(msg.topic == 'php_function'):
       d = json.loads(msg.payload)
       if(DEBUG):
          print(d['device']+':'+d['function'])
       if(d['function'] == 'apply_schedule'):
           device_objects[int(d['device'])]['object'].reload_triggers_from_mysql()
       if(d['function'] == 'apply'):
          device_objects[int(d['device'])]['object'].toggle_off()
          device_objects[int(d['device'])]['object'].delete_device()
          device_objects[int(d['device'])]['object'] = None     
          session = Session()
          new_device = session.query(Devices).filter(Devices.id == int(d['device']))
          device = new_device[0]
          RGPIO.setup(int(device.gpio), RGPIO.OUT)
          RGPIO.output(int(device.gpio), RGPIO.HIGH)
          device_objects.update({device.id : {'object' : make_device(device.id, device.gpio, device.trigger, device.t_change, device.h_change, device.temp, device.humid, device.interval, device.duration, device.name, device.run, device.state, device.lastRun, device.protocol, device.ip, device.timer)}})
          session.close()
       if(d['function'] == 'run'):
          device_objects[int(d['device'])]['object'].run_device_request()
          print_scheduler()
       if(d['function'] == 'stop'):
          device_objects[int(d['device'])]['object'].stop_device_request()
          print_scheduler()
       if(d['function'] == 'off'):
          device_objects[int(d['device'])]['object'].toggle_off()
       if(d['function'] == 'on'):
          device_objects[int(d['device'])]['object'].toggle_on()
       if(d['function'] == 'create'):
          session = Session()
          max_devices = session.query(func.max(Devices.id))
          for device in max_devices:
               new_device = session.query(Devices).filter(Devices.id == device[0])
               device = new_device[0]
               RGPIO.setup(int(device.gpio), RGPIO.OUT)
               RGPIO.output(int(device.gpio), RGPIO.HIGH)
               device_objects.update({device.id : {'object' : make_device(device.id, device.gpio, device.trigger, device.t_change, device.h_change, device.temp, device.humid, device.interval, device.duration, device.name, device.run, device.state, device.lastRun, device.protocol, device.ip, device.timer)}})
          session.close()
       if(d['function'] == 'delete'):
          device_objects[int(d['device'])]['object'].delete_device()
          device_objects[int(d['device'])]['object'] = None
       if(d['function'] == 'sql_reload'):
          sql_reload()
       if(d['function'] == 'get_status'):
          status = [current_temp, current_humidity, os.getpid()]
          mqttc.publish("php_return_status",json.dumps(status))
       if(d['function'] == 'reload_settings'):
          reload_settings()



def on_publish(mqttc, obj, mid):
    print("mid: " + str(mid))


def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


def on_log(mqttc, obj, level, string):
    print(string)



mqttc.on_message = on_message
mqttc.on_connect = on_connect
#mqttc.on_publish = on_publish
#mqttc.on_subscribe = on_subscribe
# Uncomment to enable debug messages
#mqttc.on_log = on_log
mqttc.connect("localhost", 9001, 60)
mqttc.subscribe("php_function", 0)
mqttc.subscribe("stat/+/POWER", 0)
mqttc.subscribe("cmnd/"+service_topic+"/+/+/+", 0)
mqttc.subscribe("stat/"+service_topic+"/+/+/+", 0)
print(service_topic)
mqttc.loop_forever()


