from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base, engine

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    op_number = Column(String, index=True)
    risk_score = Column(Float)
    uncertainty = Column(Float)
    confidence = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)
