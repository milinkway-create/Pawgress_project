"""Small, transactional document store. Private tables; no public Data API access."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, String, JSON, Integer, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from . import config

def now():
    return datetime.now(timezone.utc).isoformat()

def uid():
    return str(uuid4())

def initial_state():
    return {'projects': [], 'memories': [], 'history': [], 'chats': {}, 'proposals': [], 'focus': []}

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'pawgress_users'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    username: Mapped[str] = mapped_column(String(80), unique=True)
    disabled: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[dict] = mapped_column(JSON, default=initial_state)

class Setting(Base):
    __tablename__ = 'pawgress_settings'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[int] = mapped_column(Integer)

class Usage(Base):
    __tablename__ = 'pawgress_usage'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    cost: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))

engine = create_engine(config.DATABASE_URL, connect_args={'check_same_thread': False, 'timeout': 30} if config.DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)

def initialize():
    Base.metadata.create_all(engine)
    if engine.dialect.name == 'postgresql':
        with engine.begin() as connection:
            for table in ['pawgress_users','pawgress_settings','pawgress_usage']:
                connection.execute(text(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY'))
                connection.execute(text(f'REVOKE ALL ON {table} FROM PUBLIC'))
                # Supabase API roles must never reach this backend-owned document store.
                for role in ['anon','authenticated']:
                    exists=connection.execute(text('SELECT 1 FROM pg_roles WHERE rolname=:role'),{'role':role}).scalar()
                    if exists:connection.execute(text(f'REVOKE ALL ON {table} FROM {role}'))
    with Session(engine) as db:
        if db.get(Setting, 'budget') is None:
            db.add(Setting(id='budget', value=config.BUDGET))
            db.commit()

@contextmanager
def transaction():
    with Session(engine) as db:
        if engine.dialect.name == 'sqlite':
            db.execute(text('BEGIN IMMEDIATE'))
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

def locked_user(db, user_id):
    return db.scalar(select(User).where(User.id == user_id).with_for_update())

def read_state(user_id):
    with Session(engine) as db:
        return deepcopy(db.get(User, user_id).state)

@contextmanager
def edit_state(user_id):
    with transaction() as db:
        user = locked_user(db, user_id)
        state = deepcopy(user.state)
        yield state
        user.state = state

def record(state, project_id, action, detail):
    state['history'].append({'id': uid(), 'project_id': project_id, 'action': action, 'detail': detail, 'at': now()})
    state['history'] = state['history'][-500:]
