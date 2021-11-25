from abc import abstractmethod
import datetime
from enum import Enum

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
    class FIELD_NAMES(Enum):
        REPOSITORY_URL = "repository_url"
        NAME = "name"
        TOOL_IDENTIFIER = "tool_identifier"
        BIOTOOLS_ID = "biotools_id"
        INCLUSION = "inclusion"
        BIOCOMMONS_DOCUMENTATION_DESCRIPTION = "biocommons_documentation_desc"
        BIOCOMMONS_DOCUMENTATION_LINK = "biocommons_documentation_link"
        DESCRIPTION = "description"
        LICENSE = "license"
        EDAM_TOPICS = "edam_topics"
        GALAXY_SEARCH_TERM = "galaxy_search_term"
        GALAXY_AUSTRALIA_LAUNCH_LINK = "galaxy_au_launch_link"
        NCI_GADI_VERSION = "nci_gadi_version"
        PAWSEY_ZEUS_VERSION = "pawsey_zeus_version"
        PAWSEY_MAGNUS_VERSION = "pawsey_magnus_version"
        QRISCLOUD_VERSION = "qriscloud_version"

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
        if data is not None:
            return self._render(data)
        return {}

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
        return {Dataprovider.FIELD_NAMES.REPOSITORY_URL: data["Info URL"],
                Dataprovider.FIELD_NAMES.NAME: data["Tool / workflow name"],
                Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER: data["toolID"],
                Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_DESCRIPTION: data["additional_documentation_description"],
                Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_LINK: data["additional_documentation"],
                Dataprovider.FIELD_NAMES.EDAM_TOPICS: data["Primary purpose (EDAM, if available)"],
                Dataprovider.FIELD_NAMES.GALAXY_SEARCH_TERM: data["Galaxy toolshed name / search term"],
                Dataprovider.FIELD_NAMES.INCLUSION: data["include?"]}

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
        return {Dataprovider.FIELD_NAMES.PAWSEY_ZEUS_VERSION: data}


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
        return {Dataprovider.FIELD_NAMES.PAWSEY_MAGNUS_VERSION: data}


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
        return {Dataprovider.FIELD_NAMES.QRISCLOUD_VERSION: data}


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
        retval = {}
        if "link" in data:
            retval[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK] = data["link"]
        return retval


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
            url = """https://bio.tools/api/t/?biotoolsID="%s"&format=json""" % biotools_id
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
       retval = {}
       if "list" in data and len(data["list"])>0:
           tooldata = data["list"][0]
           if tooldata["biotoolsID"]:
               retval[Dataprovider.FIELD_NAMES.BIOTOOLS_ID] = tooldata["biotoolsID"]
           if tooldata["homepage"]:
               retval[Dataprovider.FIELD_NAMES.REPOSITORY_URL] = tooldata["homepage"]
           if tooldata["description"]:
               retval[Dataprovider.FIELD_NAMES.DESCRIPTION] = tooldata["description"]
           if tooldata["license"]:
               retval[Dataprovider.FIELD_NAMES.LICENSE] = tooldata["license"]
           if tooldata["topic"]:
               retval[Dataprovider.FIELD_NAMES.EDAM_TOPICS] = tooldata["topic"]
       return retval


class GadiDataProvider(Dataprovider):

    def __init__(self, key_file):
        super().__init__()
        self.key = open(key_file, "r").readline()
        self.identifier = "GADI"

    def _query_remote(self):
        self.available_data = {}
        #https://stackoverflow.com/a/8685813
        req = requests.get("http://gadi-test-apps.nci.org.au:5000/dump", headers={"Authorization": self.key})
        if req.status_code != 200:
            raise FileNotFoundError(req.url)
        for line in req.text.split("\n")[:-1]:
            tool_id, version = line.split(",")
            if tool_id not in self.available_data:
                self.available_data[tool_id] = []
            self.available_data[tool_id].append(version)


    def _render(self, data):
        return {Dataprovider.FIELD_NAMES.NCI_GADI_VERSION: data}


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

    def get_formatted_table(self):
        import urllib
        tool_table = self.get_data()
        formatted_list = []
        for index, row in tool_table.iterrows():
            tool_line = []
            tool_line.append("""<a href="%s">%s</a>"""%(row[Dataprovider.FIELD_NAMES.REPOSITORY_URL],row[Dataprovider.FIELD_NAMES.NAME]) if not pd.isna(row[Dataprovider.FIELD_NAMES.REPOSITORY_URL]) else "")
            tool_line.append("""<a href="https://bio.tools/%s">%s</a>"""%(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID], row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) if not pd.isna(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) else "")
            tool_line.append(row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER] if not pd.isna(row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER]) else "")
            tool_line.append(row[Dataprovider.FIELD_NAMES.DESCRIPTION] if not pd.isna(row[Dataprovider.FIELD_NAMES.DESCRIPTION]) else "")
            if isinstance(row[Dataprovider.FIELD_NAMES.EDAM_TOPICS], list):
                tool_line.append("<br \>".join(["""<a href="%s">%s</a>"""% (x["uri"], x["term"]) for x in row[Dataprovider.FIELD_NAMES.EDAM_TOPICS]]))
            else:
                tool_line.append("")
            tool_line.append("""<a href="https://biocontainers.pro/tools/%s">%s</a>"""%(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID], row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) if not pd.isna(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) else "")
            tool_line.append(row[Dataprovider.FIELD_NAMES.LICENSE] if not pd.isna(row[Dataprovider.FIELD_NAMES.LICENSE]) else "")
            tool_line.append("""<a href="https://toolshed.g2.bx.psu.edu/repository/browse_repositories?f-free-text-search=%s">%s</a>"""%(row[Dataprovider.FIELD_NAMES.GALAXY_SEARCH_TERM], row[Dataprovider.FIELD_NAMES.GALAXY_SEARCH_TERM]) if not pd.isna(row[Dataprovider.FIELD_NAMES.GALAXY_SEARCH_TERM]) else "")
            tool_line.append("""<a href="%s">%s</a>""" %(row[Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_LINK], row[Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_DESCRIPTION]) if not pd.isna(row[Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_LINK]) else "")
            tool_line.append("""<a href="https://usegalaxy.org.au/%s">Launch</a>""" %(row[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK]) if not pd.isna(row[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK]) else "")
            if isinstance(row[Dataprovider.FIELD_NAMES.NCI_GADI_VERSION], list):
                tool_line.append("<br \>".join(row[Dataprovider.FIELD_NAMES.NCI_GADI_VERSION]))
            else:
                tool_line.append("")
            if isinstance(row[Dataprovider.FIELD_NAMES.PAWSEY_ZEUS_VERSION], list):
                tool_line.append("<br \>".join(row[Dataprovider.FIELD_NAMES.PAWSEY_ZEUS_VERSION]))
            else:
                tool_line.append("")
            if isinstance(row[Dataprovider.FIELD_NAMES.PAWSEY_MAGNUS_VERSION], list):
                tool_line.append("<br \>".join(row[Dataprovider.FIELD_NAMES.PAWSEY_MAGNUS_VERSION]))
            else:
                tool_line.append("")
            if isinstance(row[Dataprovider.FIELD_NAMES.QRISCLOUD_VERSION], list):
                tool_line.append("<br \>".join(row[Dataprovider.FIELD_NAMES.QRISCLOUD_VERSION]))
            else:
                tool_line.append("")
            formatted_list.append(tool_line)
        return pd.DataFrame(formatted_list, columns=["Tool / workflow name","bio.tools link","Tool identifier (module name / bio.tools ID / placeholder)","Description","Topic (EDAM, if available)","BioContainers link","License","Available in Galaxy toolshed","BioCommons Documentation","Galaxy Australia","NCI (Gadi)","Pawsey (Zeus)","Pawsey (Magnus)","QRIScloud / UQ-RCC (Flashlite, Awoonga, Tinaroo)"])

