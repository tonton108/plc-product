from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine

# スレッドセーフなセッション管理のためのSQLAlchemy設定
db = SQLAlchemy(
    engine_options={
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'echo': False,
    }
) 