# models.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship

DATABASE_URL = "mysql+mysqlconnector://root@localhost/db_python"
# DATABASE_URL = "mysql+mysqlconnector://uzsmvxzzixy0w996:0odbm5rkOIqb3zDliHEA@bi5x6l0tpj40dbbsr5lc-mysql.services.clever-cloud.com:3306/bi5x6l0tpj40dbbsr5lc"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# This script defines SQLAlchemy models representing tables in a MySQL database
# for a web application. It establishes a connection to the database using 
# the specified URL, creates a session for database operations,
# and declares a base class for declarative model definitions.

# 2.
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(length=50), unique=True, index=True)
    email = Column(String(length=60), unique=True, index=True)
    hashed_password = Column(String(length=60))
    role = Column(String(length=60), default="researcher")

class ImagePrediction(Base):
    __tablename__ = "image_predictions"
    id = Column(Integer, primary_key=True, index=True)
    plant_name = Column(String(255))
    disease = Column(String(255))
    growth_stage = Column(String(255))
    captured_images_id = Column(Integer, ForeignKey("captured_images.id"))

class CapturedImage(Base):
    __tablename__ = 'captured_images'
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(length=255), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))

# 1. CapturedImages and ScheduleCapture relationship
class ScheduleCapture(Base):
    __tablename__ = 'schedule_captures'
    id = Column(Integer, primary_key=True, index=True)
    intervals = Column(Integer)
    times = Column(Integer)
    captured_images_id = Column(Integer, ForeignKey("captured_images.id"))


# 5. users and ImagePredictions and ResearchHub relationship
class ResearchHub(Base):
    __tablename__ = "research_hub"
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(255))  # Specify the length here
    image_prediction_id = Column(Integer, ForeignKey("image_predictions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))


# 6. users and ImagePredictions and ResearchHub relationship
class Remarks(Base):
    __tablename__ = "remarks"
    id = Column(Integer, primary_key=True, index=True)
    replies = Column(String(255))  # Specify the length here
    research_hub_id = Column(Integer, ForeignKey("research_hub.id"))
    user_id = Column(Integer, ForeignKey("users.id"))


Base.metadata.create_all(bind=engine)
