from abc import abstractmethod
import datetime
import pandas as pd
from typing import List


class Dataprovider:
    """
    Class represting a data source, which enriches informaiton about a tool.
    """
    def __init__(self):
        self.identifier = ""
        """available_data is keyed buy the toolid and should contain all information received by this data provider"""
        self.available_data = {}
        self.last_queried = datetime.datetime.min()


    def query_remote(self):
        if self._needs_querying():
            self._query_remote()

    """
    _query_remote queries a remote data source, transforms the informaiton recieved into internal identifiers to be later joined onto all available tools.
    """
    @abstractmethod
    def _query_remote(self):
        pass

    """needs re-querying if data is more than 7 days old"""
    def _needs_querying(self):
        return (datetime.datetime.now() - self.last_queried) > datetime.timedelta(days=7)

    """get information """
    def get_information(self, uid):
        if uid in self.available_data:
            return self.available_data[uid]
        else:
            return None

    """Data provider are keyed by id"""
    def __eq__(self, other):
        if isinstance(other,Dataprovider):
            return self.identifier == other.identifier
        else:
            return False

    """public wrapper for _render"""
    def render(self,tool):
        data = tool.get_data(self)
        return self._render(data)

    """render information"""
    @abstractmethod
    def _render(self,data):
        pass


class Tool:
    """
    Class representing a tool.
    """

    def __init__(self,uid):
        self.ID = uid
        self.data = {}

    """Add data to a tool for a provider"""
    def add_data(self, provider):
        self.data[provider.identifier]= provider.get_information(self.ID)

    """retrieve data for a provider"""
    def get_data(self, provider):
        return self.data[provider.identifier]

    """Tools are keyed by ID"""
    def __eq__(self, other):
        if isinstance(other,Tool):
            return self.ID == other.ID
        else:
            return False


class ToolDB:
    """represents the database for all known tools"""
    def __init__(self):
        self.db = {}
        self.dataprovider: List[Dataprovider]
        self.dataprovider = []


    """enrich the DB with what the dataprovider has queried from its datasource"""
    def _enrich(self,dataprovider : Dataprovider):
        dataprovider.query_remote()

        for i in self.data:
            tool = self.db[i]
            tool.add_data(dataprovider)

    """add a dataprovider to the list of providers"""
    def add_provider(self,provider : Dataprovider):
        self.dataprovider.append(provider)
        self._enrich(provider)

    def get_data(self):
        columns = ["ID"]
        columns.extend([i for i in self.dataprovider.identifier])
        data = []
        for i in self.db:
            line= [i]
            for dp in self.dataprovider:
                line.append(dp.render(self.db[i]))
            data.append(line)

        return pd.DataFrame(data,columns=columns)


