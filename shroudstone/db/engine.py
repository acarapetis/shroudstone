from pathlib import Path
from sqlalchemy.orm import sessionmaker
from shroudstone.config import db_file
from sqlalchemy import create_engine
import alembic.command
import alembic.config

here = Path(__file__).parent
dburl = f"sqlite:///{db_file}"
engine = create_engine(dburl)
Session = sessionmaker(engine)

def migrate(revision: str = "head"):
    cfg = alembic.config.Config()
    cfg.set_main_option("script_location", str(here / "alembic"))
    cfg.set_main_option("sqlalchemy.url", dburl)
    alembic.command.upgrade(cfg, revision)
