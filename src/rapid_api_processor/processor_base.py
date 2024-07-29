import requests
from src import config as cf
from src.database import database, schema
from sqlalchemy import insert
from datetime import datetime


class BaseProcessor:
    _table_str = None
    _endpoint = None

    def __init__(self):
        self.database = database
        self.response_json = ...
        self.data = ...

    @classmethod
    def create(cls, service: str, endpoint: str = None, params: dict = None):
        _api = cf.SERVICES.get(service)

        _host = _api['host']
        _endpoints = _api['endpoints']

        if endpoint in _endpoints:
            cls._endpoint = endpoint
            cls._url = cls._get_url(_host, cls._endpoint)
        else:
            raise ValueError()

        if params:
            cls._params = params
        else:
            cls._params = _endpoints.get(endpoint)['params']

        cls._headers = {'X-RapidAPI-Key': cf.RAPIDAPI_KEY, 'X-RapidAPI-Host': _host}
        cls._table_str = _endpoints.get(endpoint)['table']
        # cls._table = cls.get_class_by_tablename(cls._table_str)

    @staticmethod
    def _get_url(host, endpoint):
        return f"https://{host}{endpoint}"

    @staticmethod
    def get_class_by_tablename(table_fullname):
        """Return class reference mapped to table.

        :param table_fullname: String with fullname of table.
        :return: Class reference or None.
        """
        for c in schema.Base._decl_class_registry.values():
            try:
                name = str.split(c.__table__.fullname, '.')[1]
                if hasattr(c, '__table__') and name == table_fullname:
                    return c
            except AttributeError as e:
                pass  # TODO we'll see

    def download_base(self):
        response = requests.request("GET", self._url,
                                    headers=self._headers,
                                    params=self._params)

        if not response.status_code == 200:
            raise ConnectionError(f"Response: {response}")
        else:
            self.response_json = response.json()

    def save_df(self):
        self.data['timestamp'] = datetime.now()
        with self.database.engine.connect() as conn:
            self.data.to_sql(name=self._table_str,
                             con=conn,
                             schema=cf.DB_SCHEMA,
                             if_exists='append',
                             index=False)

    def save_dict(self):
        self.data['timestamp'] = datetime.now()
        with self.database.engine.connect() as conn:
            stmt = (
                insert(self._table).
                values(self.data)
            )
            conn.execute(stmt)

    def save_base(self):
        if isinstance(self.data, dict):
            return self.save_dict()
        else:
            return self.save_df()

    def download_and_save(self):
        self.download_base()
        self.save_base()
