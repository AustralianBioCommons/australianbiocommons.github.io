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
        PUBLICATIONS = "FIELD_NAMES.PUBLICATIONS"
        GALAXY_AUSTRALIA_LAUNCH_LINK = "FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK"
        NCI_GADI_VERSION = "FIELD_NAMES.NCI_GADI_VERSION"
        PAWSEY_ZEUS_VERSION = "FIELD_NAMES.PAWSEY_ZEUS_VERSION"
        PAWSEY_MAGNUS_VERSION = "FIELD_NAMES.PAWSEY_MAGNUS_VERSION"
        QRISCLOUD_VERSION = "FIELD_NAMES.QRISCLOUD_VERSION"

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
                Dataprovider.FIELD_NAMES.INCLUSION: data["include?"] == "y"}

    def get_alt_ids(self):
        if self._needs_querying():
            self._query_remote()
        retval = {ToolMatrixDataProvider.ID_BIO_TOOLS: {}}
        for toolID in self.available_data:
            row = self.available_data[toolID]
            if row.biotoolsID not in retval[ToolMatrixDataProvider.ID_BIO_TOOLS]:
                retval[ToolMatrixDataProvider.ID_BIO_TOOLS][row.biotoolsID] = []
            retval[ToolMatrixDataProvider.ID_BIO_TOOLS][row.biotoolsID].append(toolID)
        return retval


class ZeusDataProvider(Dataprovider):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.identifier = "ZEUS"

    def _query_remote(self):
        import re
        self.available_data = {}
        data = pd.read_csv(self.filename, delimiter="/", header=None)
        data.columns = ["toolID", "version"]

        for idx, row in data.iterrows():
            toolID = row.toolID
            toolID = re.sub(r"wgs", "celera", toolID)
            toolID = re.sub(r"trinityrnaseq", "trinity", toolID)
            if toolID not in self.available_data:
                self.available_data[toolID] = []
            self.available_data[toolID].append(row.version)

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
        import re
        self.available_data = {}
        with open(self.filename, "r") as stream:
            for line in stream:
                line = line.split("/")
                toolID = line[0].strip()
                if len(line) == 3:
                    toolID = toolID + "-" + line[1].strip()
                elif len(line) > 3:
                    raise ValueError(toolID)
                toolID = toolID.lower()
                toolID = toolID.replace("genomeanalysistk", "gatk")
                toolID = toolID.replace("gatk4", "gatk")
                toolID = toolID.replace("iqtree", "iq-tree")
                toolID = re.sub(r"^pacbio$", "smrtlink", toolID)
                toolID = re.sub(r"^soapdenovo$", "soapdenovo2", toolID)
                if toolID not in self.available_data:
                    self.available_data[toolID] = []
                self.available_data[toolID].append(line[-1].strip())

    def _render(self, data):
        return {Dataprovider.FIELD_NAMES.QRISCLOUD_VERSION: data}


class GalaxyDataProvider(Dataprovider):

    GALAXY_ID = "GalaxyAustralia_ID"

    def __init__(self, parent, look_up_file):
        super().__init__()
        self.identifier = "GalaxyAustralia"
        self.parent = parent
        self.look_up_file = look_up_file

    def _query_remote(self):
        self.available_data = {}
        req = requests.request("get", "https://usegalaxy.org.au/api/tools")
        if req.status_code != 200:
            raise FileNotFoundError(req.url)
        tool_sections = json.loads(req.text)
        #Herve Menager via Slack
        tools_nested = [tool_section.get('elems') for tool_section in tool_sections if 'elems' in tool_section]
        tools = list(itertools.chain.from_iterable(tools_nested))

        #
        for tool in tools:
            galaxy_id = tool["id"]
            galaxy_id = "/".join(galaxy_id.split("/")[:-1])
            biotools_id = None
            if "xrefs" in tool:
                for item in tool["xrefs"]:
                    if item["reftype"] == "bio.tools":
                        biotools_id = item["value"]
                        break
            tool_id_list = []
            if biotools_id is not None:
                tool_id_list = self.parent.get_id_from_alt(ToolMatrixDataProvider.ID_BIO_TOOLS, biotools_id)
            if len(tool_id_list) == 0:
                tool_id_list = self.parent.get_id_from_alt(GalaxyDataProvider.GALAXY_ID, galaxy_id)
            if len(tool_id_list) == 0:
                self._save_unmatched_(galaxy_id, tool)
            for tool_id in tool_id_list:
                if tool_id not in self.available_data:
                    self.available_data[tool_id] = []
                self.available_data[tool_id].append(tool)

    def _render(self, data):
        retval = {}
        retval[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK] = [(d["link"], d["name"]) for d in data if "link" in d and "name" in d]
        return retval

    def get_alt_ids(self):
        data = pd.read_csv(self.look_up_file)
        retval = {GalaxyDataProvider.GALAXY_ID: {}}
        for idx, row in data.iterrows():
            if not pd.isna(row.BioCommons_toolID):
                id = "/".join(row.galaxy_id.split("/")[:-1])
                if id not in retval[GalaxyDataProvider.GALAXY_ID]:
                    retval[GalaxyDataProvider.GALAXY_ID][id] = []
                retval[GalaxyDataProvider.GALAXY_ID][id].append(row["BioCommons_toolID"])
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
                tool_id_list = self.parent.get_id_from_alt(ToolMatrixDataProvider.ID_BIO_TOOLS, biotools_id)
                for tool_id in tool_id_list:
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
           if tooldata["publication"]:
               retval[Dataprovider.FIELD_NAMES.PUBLICATIONS] = tooldata["publication"]
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
            line = line.split(",")
            tool_id = line[0].strip()
            tool_id = tool_id.lower()
            version = line[1]
            #tool_id, version = line.split(",")
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

    def get_formatted_table(self):
        import urllib
        tool_table = self.get_data()
        formatted_list = []
        for index, row in tool_table.iterrows():
            if not row[Dataprovider.FIELD_NAMES.INCLUSION]:
                continue
            tool_line = []
            tool_line.append("""<a href="%s" ga-product="tool" ga-id="%s">%s</a>"""%(row[Dataprovider.FIELD_NAMES.REPOSITORY_URL],row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER],row[Dataprovider.FIELD_NAMES.NAME]) if not pd.isna(row[Dataprovider.FIELD_NAMES.REPOSITORY_URL]) else row[Dataprovider.FIELD_NAMES.NAME])
            tool_line.append("""<a href="https://bio.tools/%s"  ga-product="biotool" ga-id="%s">%s</a>"""%(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID], row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER], row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) if not pd.isna(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) else "")
            tool_line.append(row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER] if not pd.isna(row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER]) else "")
            tool_line.append("""<span class="description-text">%s</span>"""%(row[Dataprovider.FIELD_NAMES.DESCRIPTION]) if not pd.isna(row[Dataprovider.FIELD_NAMES.DESCRIPTION]) else "")
            if isinstance(row[Dataprovider.FIELD_NAMES.EDAM_TOPICS], list):
                tool_line.append("<br \>".join(["""<a class="edam-terms" href="%s" ga-product="edam" ga-id="%s">%s</a>"""% (x["uri"], row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER], x["term"]) for x in row[Dataprovider.FIELD_NAMES.EDAM_TOPICS]]))
            else:
                tool_line.append("")
            if isinstance(row[Dataprovider.FIELD_NAMES.PUBLICATIONS], list):
                tool_line.append("<br \>".join(list(map(lambda x:f"""<a class="publication-title" href="https://doi.org/{x["doi"]}" ga-product="publication" ga-id="%s"">{x["metadata"]["title"] if x["metadata"] is not None else "DOI:"+x["doi"]}</a>"""% (row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER]) if x["doi"] is not None else
                                                        f"""<a class="publication-title" href="http://www.ncbi.nlm.nih.gov/pubmed/{x["pmid"]}" ga-product="publication" ga-id="%s">{x["metadata"]["title"] if x["metadata"] is not None else "PMID:"+x["pmid"]}</a>"""% (row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER]) if x["pmid"] is not None else
                                                        f"""<a class="publication-title" href="https://www.ncbi.nlm.nih.gov/pmc/articles/{x["pmcid"]}" ga-product="publication" ga-id="%s">{x["metadata"]["title"] if x["metadata"] is not None else "PMCID:"+x["pmcid"]}</a>"""% (row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER]) if x["pmcid"] is not None else
                                                        "",row[Dataprovider.FIELD_NAMES.PUBLICATIONS]))))
            else:
                tool_line.append("")
            tool_line.append("""<a href="https://biocontainers.pro/tools/%s" ga-product="containers" ga-id="%s">%s</a>"""%(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID], row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER], row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) if not pd.isna(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) else "")
            tool_line.append(row[Dataprovider.FIELD_NAMES.LICENSE] if not pd.isna(row[Dataprovider.FIELD_NAMES.LICENSE]) else "")
            tool_line.append("""<a href="%s" ga-product="biocommons" ga-id="%s">%s</a>""" %(row[Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_LINK], row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER], row[Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_DESCRIPTION]) if not pd.isna(row[Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_LINK]) else "")
            if isinstance(row[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK], list):
                # see https://stackoverflow.com/a/2906586
                # see https://stackoverflow.com/questions/5618878/how-to-convert-list-to-string
                #tool_line.append("<br \>".join(["""<button class="galaxy-link" onclick="window.open('https://usegalaxy.org.au/%s','_blank').focus()">%s</button>""" %d for d in row[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK]]))
                a = ["""<button class="galaxy-link" onclick="window.open('https://usegalaxy.org.au/%s','_blank').focus()" ga-product="galaxy" ga-id="%s">%s</button>"""% (x[0], row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER], x[1]) for x in row[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK]]
                     #%d for d in row[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK]]
                tool_line.append("""<ul class="galaxy-links-holder"><li class="closed galaxy-collapsible" onclick="$(this).parent('.galaxy-links-holder').find('.galaxy-links').toggle({duration:200,start:function(){$(this).parent('.galaxy-links-holder').find('.galaxy-collapsible').toggleClass('closed open')}})" ><span class="galaxy-link-toggle">""" + str(len(a)) + " tool" + ("s" if len(a)>1 else "") + """</span><span class="button"/></li><ul class="galaxy-links" style="display: none;">""" + str("".join(a)) + "</li></ul></ul>")
            else:
                tool_line.append("")
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
        return pd.DataFrame(formatted_list, columns=["Tool / workflow name","bio.tools link","Tool identifier (module name / bio.tools ID / placeholder)","Description","Topic (EDAM, if available)","Publications","BioContainers link","License","BioCommons Documentation","Galaxy Australia","NCI (Gadi)","Pawsey (Zeus)","Pawsey (Magnus)","QRIScloud / UQ-RCC (Flashlite, Awoonga, Tinaroo)"])

