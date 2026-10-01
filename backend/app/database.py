import os
from sqlalchemy import create_engine, Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./traces.db')
connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TraceDB(Base):
    __tablename__='traces'
    id=Column(Integer,primary_key=True)
    trace_id=Column(String,unique=True,index=True)
    agent_name=Column(String)
    created_at=Column(String)
    total_steps=Column(Integer,default=0)
    steps=relationship('TraceStepDB',back_populates='trace',cascade='all, delete-orphan')

class TraceStepDB(Base):
    __tablename__='trace_steps'
    id=Column(Integer,primary_key=True)
    trace_id=Column(String,ForeignKey('traces.trace_id'),index=True)
    step_id=Column(String,index=True)
    parent_step_id=Column(String,nullable=True)
    step_number=Column(Integer,index=True)
    step_type=Column(String)
    status=Column(String,default='completed')
    input_json=Column(Text)
    output_json=Column(Text)
    state_snapshot=Column(Text)
    latency_ms=Column(Integer,default=0)
    prompt_tokens=Column(Integer,default=0)
    completion_tokens=Column(Integer,default=0)
    trace=relationship('TraceDB',back_populates='steps')

class BranchDB(Base):
    __tablename__='branches'
    id=Column(Integer,primary_key=True)
    parent_trace_id=Column(String,index=True)
    fork_step_id=Column(String)
    new_trace_id=Column(String,unique=True,index=True)
    created_at=Column(String)

def init_db(): Base.metadata.create_all(bind=engine)