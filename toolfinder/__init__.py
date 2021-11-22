from abc import abstractmethod
import datetime

import numpy as np
import pandas as pd
from typing import List
import requests
import json
import itertools

class Dataprovider:
    """
    Class representing a data source, which enriches information about a tool.
    """

    def __init__(self):
        self.identifier = ""
        """available_data is keyed by the toolid and should contain all information received by this data provider"""
        self.available_data = {}
        self.last_queried = datetime.datetime.min

    def query_remote(self):
        if self._needs_querying():
            self._query_remote()

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
        return self._render(data)

    """render information"""

    @abstractmethod
    def _render(self, data):
        pass

    def get_alt_ids(self):
        return{}


class ToolMatrixDataProvider(Dataprovider):
    ID_BIO_TOOLS = "bio.tools"

    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.identifier = "TOOL_MATRIX"

    def _query_remote(self):
        self.available_data = {}
        data = pd.read_excel(self.filename, header=2)

        for idx, row in data.iterrows():
            self.available_data[row.toolID] = row.copy()

    def _render(self, data):
        return {"show": data["include?"]}

    def get_alt_ids(self):
        if self._needs_querying():
            self._query_remote()
        retval = {ToolMatrixDataProvider.ID_BIO_TOOLS: {}}
        for toolID in self.available_data:
            row = self.available_data[toolID]
            retval[ToolMatrixDataProvider.ID_BIO_TOOLS][row.biotoolsID] = toolID
        return retval


class ZeusDataProvider(Dataprovider):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.identifier = "ZEUS"

    def _query_remote(self):
        self.available_data = {}
        data = pd.read_csv(self.filename, delimiter="/", header=None)
        data.columns = ["toolID", "version"]

        for idx, row in data.iterrows():
            if row.toolID not in self.available_data:
                self.available_data[row.toolID] = []
            self.available_data[row.toolID].append(row.version)

    def _render(self, data):
        return data


class MagnusDataProvider(Dataprovider):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.identifier = "MAGNUS"

    def _query_remote(self):
        self.available_data = {}
        data = pd.read_csv(self.filename, delimiter="/", header=None)
        data.columns = ["toolID", "version"]

        for idx, row in data.iterrows():
            if row.toolID not in self.available_data:
                self.available_data[row.toolID] = []
            self.available_data[row.toolID].append(row.version)

    def _render(self, data):
        return data


class QriscloudDataProvider(Dataprovider):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.identifier = "QRIScloud"

    def _query_remote(self):
        self.available_data = {}
        with open(self.filename, "r") as stream:
            for line in stream:
                line = line.split("/")
                toolID = line[0].strip()
                if len(line) == 3:
                    toolID = toolID + "-" + line[1].strip()
                elif len(line) > 3:
                    raise ValueError(toolID)
                if toolID not in self.available_data:
                    self.available_data[toolID] = []
                self.available_data[toolID].append(line[-1].strip())

    def _render(self, data):
        return data


class GalaxyDataProvider(Dataprovider):

    def __init__(self, parent):
        super().__init__()
        self.identifier = "GalaxyAustralia"
        self.parent = parent
        self.unmatched_galaxy_biotools_ids = set()

    def _query_remote(self):
        self.available_data = {}
        req = requests.request("get", "https://usegalaxy.org.au/api/tools")
        if req.status_code != 200:
            raise FileNotFoundError(req.url)
        tool_sections = json.loads(req.text)
        #Herve Menager via Slack
        tools_nested = [tool_section.get('elems') for tool_section in tool_sections if 'elems' in tool_section]
        tools = list(itertools.chain.from_iterable(tools_nested))
        tools_with_biotools = []
        for tool in tools:
            xref = []
            for ref in tool.get("xrefs", []):
                if ref["reftype"] == "bio.tools":
                    xref.append(ref)
            if len(xref) > 0:
                tools_with_biotools.append(tool)
        #tools_with_biotools = [tool for tool in tools if [xref for xref in tool.get('xrefs', []) if xref["reftype"] == "bio.tools"]]
        #tools_with_biotools = [tool for tool in tools if filter(lambda x: x["reftype"] == "bio.tools", tool.get('xrefs', []))]

        #
        for tool in tools_with_biotools:
            biotools_id = list(filter(lambda x: x["reftype"] == "bio.tools", tool['xrefs']))[0]['value']
            tool_id = self.parent.get_id_from_alt(ToolMatrixDataProvider.ID_BIO_TOOLS, biotools_id)
            if tool_id is None:
                self.unmatched_galaxy_biotools_ids.add(biotools_id)
            self.available_data[tool_id] = tool

    def get_unmatched_galaxy_biotools_ids(self):
        return self.unmatched_galaxy_biotools_ids

    def _render(self, data):
        return data


class BiotoolsDataProvider(Dataprovider):

    def __init__(self, toolmatrix, parent):
        super().__init__()
        self.identifier = "BioTools"
        self.filename = toolmatrix
        self.parent = parent

    def _query_remote(self):
        self.available_data = {}
        data = pd.read_excel(self.filename, header=2)
        unique_biotools_ids = set(data.biotoolsID.unique())
        unique_biotools_ids.remove(np.nan)
        # create an array with all the urls we want to request
        url_array = []
        for biotools_id in unique_biotools_ids:
            url = "https://bio.tools/api/t/?biotoolsID=%s&format=json" % biotools_id
            url_array.append((biotools_id, url))
        import concurrent.futures
        def fetch_url(url, biotools_id):
            return requests.get(url, timeout=10), biotools_id
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            future_urls = [executor.submit(fetch_url, url, biotools_id) for biotools_id, url in url_array]
            for future in concurrent.futures.as_completed(future_urls):
                response, biotools_id = future.result()
                if response.status_code != 200:
                    raise FileNotFoundError(response.url)
                tool_metadata = json.loads(response.text)
                tool_id = self.parent.get_id_from_alt(ToolMatrixDataProvider.ID_BIO_TOOLS, biotools_id)
                self.available_data[tool_id] = tool_metadata

            #response = requests.get("https://bio.tools/api/t/?biotoolsID=%s&format=json" %biotools_id)


    def _render(self, data):
        return data


class GadiDataProvider(Dataprovider):

    def __init__(self, key_file):
        super().__init__()
        self.key = open(key_file, "r").readline()
        self.identifier = "GADI"

    def _query_remote(self):
        self.available_data = {}
        req = requests.get("http://gadi-test-apps.nci.org.au:5000/dump", headers={"Authorization": self.key})
        if req.status_code != 200:
            raise FileNotFoundError(req.url)
        for line in req.text.split("\n")[:-1]:
            tool_id, version = line.split(",")
            if tool_id not in self.available_data:
                self.available_data[tool_id] = []
            self.available_data[tool_id].append(version)


    def _render(self, data):
        return data


class Tool:
    """
    Class representing a tool.
    """

    def __init__(self, uid):
        self.ID = uid
        self.data = {}

    """Add data to a tool for a provider"""

    def add_data(self, provider):
        self.data[provider.identifier] = provider.get_information(self.ID)

    """retrieve data for a provider"""

    def get_data(self, provider):
        return self.data[provider.identifier]

    """Tools are keyed by ID"""

    def __eq__(self, other):
        if isinstance(other, Tool):
            return self.ID == other.ID
        else:
            return False


class ToolDB:
    """represents the database for all known tools"""

    def __init__(self, tool_matrix_file):
        self.db = {}
        self.dataprovider: List[Dataprovider]
        self.dataprovider = []
        self.alternateids = {}
        data = pd.read_excel(tool_matrix_file, header=2)
        for i in data.toolID:
            self.db[i] = Tool(i)
        del self.db[np.nan]

    """enrich the DB with what the dataprovider has queried from its datasource"""

    def _enrich(self, dataprovider: Dataprovider):
        dataprovider.query_remote()

        for i in self.db:
            tool = self.db[i]
            tool.add_data(dataprovider)

        alt_ids = dataprovider.get_alt_ids()
        # https://stackoverflow.com/a/26853961 & https://www.python.org/dev/peps/pep-0584/
        self.alternateids = {**self.alternateids, **alt_ids}

    def get_id_from_alt(self, provider:str, unique_id:str):
        if provider in self.alternateids:
            if unique_id in self.alternateids[provider]:
                return self.alternateids[provider][unique_id]
        return None


    """add a dataprovider to the list of providers"""

    def add_provider(self, provider: Dataprovider):
        self.dataprovider.append(provider)
        self._enrich(provider)

    def get_data(self):
        columns = ["ID"]
        columns.extend([i.identifier for i in self.dataprovider])
        data = []
        for i in self.db:
            line = [i]
            for dp in self.dataprovider:
                line.append(dp.render(self.db[i]))
            data.append(line)

        return pd.DataFrame(data, columns=columns)
