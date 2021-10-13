from flask_sqlalchemy import Model, SQLAlchemy, BaseQuery
from sqlalchemy.orm import DeclarativeMeta


class BaseQueryExtension(BaseQuery):
    """
    some extensions to flask sql alchemy
    """

    def one(self, **kwargs):
        """
        wraps filter and first
        """
        return self.filter_by(**kwargs).first()

    def many(self, **kwargs):
        """
        wraps filter and all
        """
        return self.filter_by(**kwargs).all()

    def exists(self, **kwargs):
        """
        true when models exists
        """
        return bool(self.filter_by(**kwargs).first())

    def delete_by(self, **kwargs):
        """
        true when models exists
        """
        self.filter_by(**kwargs).delete()


class BaseModel(Model):
    """
    extensions to all models
    """

    # prevents "unresolved reference" warnings
    query: BaseQueryExtension

    def to_dict(self) -> dict:
        """
        used in templates
        """
        return {key: self.__dict__[key] for key in sorted(self.__dict__.keys()) if not key.startswith('_')}


class Database:
    """
    wraps sql alchemy
    """
    sql_alchemy: SQLAlchemy
    Model: DeclarativeMeta

    def __init__(self):
        self.sql_alchemy: SQLAlchemy = SQLAlchemy(query_class=BaseQueryExtension, model_class=BaseModel)
        self.Model = self.sql_alchemy.Model

    def __iadd__(self, other):
        self.sql_alchemy.session.add(other)

    def __isub__(self, other):
        self.sql_alchemy.session.delete(other)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        commits changes made on database objects
        """
        self.sql_alchemy.session.commit()

    @property
    def alchemy(self):
        """
        returns sql alchemy object
        """
        return self.sql_alchemy

    @property
    def session(self):
        """
        returns sql alchemy session object
        """
        return self.sql_alchemy.session


database = Database()
