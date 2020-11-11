import json

from sqlalchemy import Column, Integer, String
from sqlalchemy import Sequence
from werkzeug.security import generate_password_hash

from SecureVision.source.backend.database.base import Base
from SecureVision.source.backend.database.unique import UniqueMixin
from SecureVision.source.backend.database.unique import _unique


class User(UniqueMixin, Base):
    __tablename__ = 'user'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    user_pass = Column(String(100), nullable=False)
    user_rights = Column(Integer, nullable=False)
    num_feedback = Column(Integer, nullable=True)

    @classmethod
    def unique_hash(cls, name):
        """
        Returns attribute
        :param name: unique attribute
        :return:
        """
        return name

    @classmethod
    def unique_filter(cls, query, name):
        """
        Filters by unique attribute
        :param query: query object
        :param name: unique attribute
        :return:
        """
        return query.filter(User.name == name)

    @classmethod
    def as_unique(cls, session, **kw):
        """
        Adds obj as unique
        :param session: session obj
        :param kw: arguments
        :return:
        """
        return _unique(
            session,
            cls,
            cls.unique_filter,
            cls,
            kw,
            'name'
        )

    def __repr__(self):
        return "<User(name='%s', user_rights='%d')>" % (self.name, self.user_rights)


# TODO: add global session handler and not separate
class UserHandler:

    def __init__(self, session_maker):
        self.__session = session_maker()

    # ADD------------------------------------------------------------
    # TODO: ADD FUNCTION THAT REGISTERS USER WITHOUT UNIQUE CHECK, FASTER
    def register_users_unique(self, json_file_path):
        """
        Registers the user from the json file, for example see create_db and db_json/users.json
        :param json_file_path: path to the json file
        """
        with open(json_file_path, 'r') as file:
            data = json.load(file)
            for employee in data['Users']:
                User.as_unique(self.__session, name=employee['name'],
                               user_pass=generate_password_hash(employee['pass'], 'sha256'),
                               user_rights=employee['rights'])
        self.commit()

    # UPDATE------------------------------------------------------------
    def user_feedb_update_by_name(self, name):
        """
        Increment the feedback value of a user identified by its name
        :param name: name of the user
        """

        user = self.user_by_name(name)
        if user:
            user.num_feedback += 1
            self.commit()
        else:
            print('No such user')

    def user_fb_update_by_id(self, user_id):
        """
        Increment the feedback value of a user identified by its id
        :param user_id: id of the user
        """

        user = self.user_by_id(user_id)
        if user:
            user.num_feedback += 1
            self.commit()
        else:
            print('No such user')

    # QUERY------------------------------------------------------------
    def user_by_name(self, name):
        """
        Query user by name
        :param name: name of the user
        :return: User object from the database that satisfies the query
        """
        return self.__session.query(User).filter(User.name == name).one_or_none()

    def user_by_id(self, user_id):
        """
        Query user by id
        :param user_id: id of the user
        :return: User object from the database that satisfies the query
        """
        return self.__session.query(User).filter(User.id == user_id).one_or_none()

    # RESOURCES------------------------------------------------------------
    def release_resources(self):
        """
        Releases the session object
        """
        if self.__session:
            self.__session.close()

    def commit(self):
        """
        Commits to the session
        """
        if self.__session:
            self.__session.commit()
