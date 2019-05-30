# coding=utf-8

from sqlalchemy import create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('mysql+pymysql://web:webgrow1985@localhost/webgrow')
Session = sessionmaker(bind=engine)

Base = declarative_base()