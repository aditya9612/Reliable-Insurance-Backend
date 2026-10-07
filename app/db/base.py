from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 Declarative Base.
    Domain models will inherit from this base in subsequent phases.
    """
    pass
