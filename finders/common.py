import datetime
from enum import Enum
from abc import abstractmethod
import pandas as pd
from typing import List
import numpy as np

class Dataprovider:
    """
    Class representing a data source, which enriches information about a tool.
    """
    class FIELD_NAMES(Enum):
        # toolfinder
        REPOSITORY_URL = "FIELD_NAMES.REPOSITORY_URL"
        NAME = "FIELD_NAMES.NAME"
        TOOL_IDENTIFIER = "FIELD_NAMES.TOOL_IDENTIFIER"
        BIOTOOLS_ID = "FIELD_NAMES.BIOTOOLS_ID"
        INCLUSION = "FIELD_NAMES.INCLUSION"
        BIOCOMMONS_DOCUMENTATION_DESCRIPTION = "FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_DESCRIPTION"
        BIOCOMMONS_DOCUMENTATION_LINK = "FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_LINK"
        DESCRIPTION = "FIELD_NAMES.DESCRIPTION"
        LICENSE = "FIELD_NAMES.LICENSE"
        EDAM_TOPICS = "FIELD_NAMES.EDAM_TOPICS"
        EDAM_OPERATIONS = "FIELD_NAMES.EDAM_OPERATIONS"
        EDAM_DATA_INPUT = "FIELD_NAMES.EDAM_DATA_INPUT"
        EDAM_DATA_OUTPUT = "FIELD_NAMES.EDAM_DATA_OUTPUT"
        PUBLICATIONS = "FIELD_NAMES.PUBLICATIONS"
        GALAXY_AUSTRALIA_LAUNCH_LINK = "FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK"
        NCI_GADI_VERSION = "FIELD_NAMES.NCI_GADI_VERSION"
        NCI_IF89_VERSION = "FIELD_NAMES.NCI_IF89_VERSION"
        #PAWSEY_ZEUS_VERSION = "FIELD_NAMES.PAWSEY_ZEUS_VERSION"
        #PAWSEY_MAGNUS_VERSION = "FIELD_NAMES.PAWSEY_MAGNUS_VERSION"
        QRISCLOUD_VERSION = "FIELD_NAMES.QRISCLOUD_VERSION"
        PAWSEY_SETONIX_VERSION = "FIELD_NAMES.PAWSEY_SETONIX_VERSION"
        # workflowfinder
        REMOTE_LINK = "FIELD_NAMES.REMOTE_LINK"
        UPDATED_AT = "FIELD_NAMES.UPDATED_AT"
        PROJECTS = "FIELD_NAMES.PROJECTS"
        TITLE = "FIELD_NAMES.TITLE"
        TAGS = "FIELD_NAMES.TAGS"
        DOI = "FIELD_NAMES.DOI"
        EDAM_OPS = "FIELD_NAMES.EDAM_OPS"
        EDAM_TOP = "FIELD_NAMES.EDAM_TOP"
        URL = "FIELD_NAMES.URL"
        LAUNCH_LINK = "FIELD_NAMES.LAUNCH_LINK"
        GUIDE_LINK = "FIELD_NAMES.GUIDE_LINK"

    def __init__(self):
        self.identifier = ""
        """available_data is keyed by the toolid and should contain all information received by this data provider"""
        self.available_data = {}
        self.unmatched_data = {}
        self.last_queried = datetime.datetime.min

    def _save_unmatched_(self, key, data):
        self.unmatched_data[key] = data

    def query_remote(self):
        if self._needs_querying():
            self._query_remote()
            self.last_queried = datetime.datetime.now()

    """
    _query_remote queries a remote data source, transforms the information received into internal identifiers to be later joined onto all available tools.
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
        if isinstance(other, Dataprovider):
            return self.identifier == other.identifier
        else:
            return False

    """public wrapper for _render"""

    def render(self, tool):
        data = tool.get_data(self)
        if data is not None:
            return self._render(data)
        return {}

    """render information"""

    @abstractmethod
    def _render(self, data):
        pass

    def get_alt_ids(self):
        return{}


class DB:
    """represents the database for all known tools"""

    def __init__(self):
        self.db = {}
        self.dataprovider: List[Dataprovider]
        self.dataprovider = []
        self.alternateids = {}

    """enrich the DB with what the dataprovider has queried from its datasource"""

    def _enrich(self, dataprovider: Dataprovider):

        alt_ids = dataprovider.get_alt_ids()
        # https://stackoverflow.com/a/26853961 & https://www.python.org/dev/peps/pep-0584/
        self.alternateids = {**self.alternateids, **alt_ids}

        dataprovider.query_remote()

        for i in self.db:
            tool = self.db[i]
            tool.add_data(dataprovider)

    def get_id_from_alt(self, provider:str, unique_id:str):
        #unique_id = unique_id.lower()
        if provider in self.alternateids:
            if unique_id in self.alternateids[provider]:
                return self.alternateids[provider][unique_id]
        return []

    def get_unmatched_ids(self, dp:Dataprovider):
        a = dp.unmatched_data
        unmatched_ids = set(dp.available_data.keys()).difference(self.db.keys())
        return(a, unmatched_ids)


    """add a dataprovider to the list of providers"""

    def add_provider(self, provider: Dataprovider):
        self.dataprovider.append(provider)
        self._enrich(provider)

    def get_data(self):
        data = []
        for i in self.db:
            line = []
            for dp in self.dataprovider:
                line.append(dp.render(self.db[i]))
            result = {}
            for element in line:
                result.update(element)
            data.append(result)

        return pd.DataFrame(data)


    def get_data_only(self):
        data = []
        for i in self.db:
            line = []
            for dp in self.dataprovider:
                line.append(dp.render(self.db[i]))
            result = {}
            for element in line:
                result.update(element)
            data.append(result)

        return data


    @abstractmethod
    def get_formatted_table(self) -> pd.DataFrame:
        pass