from .common import Dataprovider, DB, get_request
import pandas as pd
import requests
import json
import itertools
import numpy as np
import re
import yaml

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


class SetonixDataProvider(Dataprovider):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.identifier = "SETONIX"

    def _query_remote(self):
        import re
        self.available_data = {}
        data = pd.read_csv(self.filename, delimiter="/", header=None)
        data.columns = ["toolID", "version"]

        for idx, row in data.iterrows():
            toolID = row.toolID
            toolID = re.sub(r"gatk4", "gatk", toolID)
            toolID = re.sub(r"beast1", "beast", toolID)
            if toolID not in self.available_data:
                self.available_data[toolID] = []
            self.available_data[toolID].append(row.version)

    def _render(self, data):
        return {Dataprovider.FIELD_NAMES.PAWSEY_SETONIX_VERSION: data}


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
                version = line[1].strip()
                if version == 0000:
                    version = "install in progress"
                toolID = toolID.lower()
                toolID = toolID.replace("miniconda3", "miniconda")
                toolID = toolID.replace("alphafold", "alphafold_2")
                toolID = toolID.replace("cellranger-arc", "cellranger")
                toolID = toolID.replace("chai-lab", "chai-1")
                toolID = toolID.replace("localcolabfold", "colabfold")
                toolID = toolID.replace("salsa2", "salsa")
                toolID = toolID.replace("anaconda3", "anaconda")
                toolID = toolID.replace("braker3", "braker")
                toolID = toolID.replace("scipy-bundle", "scipy")
                toolID = toolID.replace("iqtree", "iq-tree")
                toolID = toolID.replace("gtdbtk", "gtdb-tk")
                toolID = toolID.replace("sra-toolkit", "sra-tools")
                #toolID = re.sub(r"^soapdenovo$", "soapdenovo2", toolID)
                if toolID not in self.available_data:
                    self.available_data[toolID] = []
                #self.available_data[toolID].append(line[-1].strip())
                self.available_data[toolID].append(version)

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
        #req = requests.request("get", "https://usegalaxy.org.au/api/tools/?in_panel=False")
        req = get_request("https://usegalaxy.org.au/api/tools/")
        if req.status_code == 200:
            tool_sections = json.loads(req.text)
            #Herve Menager via Slack
            tools_nested = [tool_section.get('elems') for tool_section in tool_sections if 'elems' in tool_section]
            tools = list(itertools.chain.from_iterable(tools_nested))

            #
            other_galaxy_id_types = {}
            for tool in tools:
                galaxy_id = tool["id"]
                version = tool["version"]
                # https://stackoverflow.com/a/70672659
                # https://stackoverflow.com/a/12595082
                # https://stackoverflow.com/a/4843178
                # https://stackoverflow.com/a/15340694
                if isinstance(galaxy_id, str):
                    match_string = "toolshed.g2.bx.psu.edu/repos"
                    if re.search(match_string, galaxy_id):
                        galaxy_id = "/".join(galaxy_id.split("/")[:-1])
                    else:
                        other_galaxy_id_types[galaxy_id] = tool
                        galaxy_id = galaxy_id
                        #print(other_galaxy_id_types[galaxy_id]["id"])
                ### example datasource_tool link "/tool_runner/data_source_redirect?tool_id=ucsc_table_direct1"
                if tool["model_class"] != "ToolSectionLabel" and tool["model_class"] != "ToolSection":
                    if tool["model_class"] == "DataSourceTool":
                        tool["link"] = tool["link"]
                    else:
                        # https://stackoverflow.com/a/4945558
                        tool["link"] = "root?" + tool["link"][13:]
                biotools_id = None
                if "xrefs" in tool:
                    for item in tool["xrefs"]:
                        if item["type"] == "bio.tools":
                            biotools_id = item["value"]
                            break
                tool_id_list = []
                ### removed as prioritising the bio.tools ID here was replicating tools across ToolFinder entries with the same bio.tools ID
                ### may need to add this back in later, so keep the code
                ###if biotools_id is not None:
                ###    tool_id_list = self.parent.get_id_from_alt(ToolMatrixDataProvider.ID_BIO_TOOLS, biotools_id)
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
        retval[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK] = [(d["link"], d["name"], d["description"], d["version"]) for d in data if "link" in d and "name" in d and "description" in d and "version" in d]
        return retval

    def get_alt_ids(self):
        data = pd.read_csv(self.look_up_file)
        retval = {GalaxyDataProvider.GALAXY_ID: {}}
        for idx, row in data.iterrows():
            if not pd.isna(row.BioCommons_toolID):
                ### https://stackoverflow.com/a/12595082
                ### https://stackoverflow.com/a/4843178
                ### https://stackoverflow.com/a/15340694
                if isinstance(row.galaxy_id, str):
                    match_string = "toolshed.g2.bx.psu.edu/repos"
                    if re.search(match_string, row.galaxy_id):
                        id = "/".join(row.galaxy_id.split("/")[:-1])
                    else:
                        id = row.galaxy_id
                        #print(id)
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
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
           if tooldata["function"]:
               retval[Dataprovider.FIELD_NAMES.EDAM_OPERATIONS] = tooldata["function"][0]["operation"]
           if tooldata["function"]:
               retval[Dataprovider.FIELD_NAMES.EDAM_DATA_INPUT] = tooldata["function"][0]["input"]
           if tooldata["function"]:
               retval[Dataprovider.FIELD_NAMES.EDAM_DATA_OUTPUT] = tooldata["function"][0]["output"]
       return retval


class BiocontainersDataProvider(Dataprovider):

    def __init__(self, toolmatrix, parent):
        super().__init__()
        self.identifier = "BioContainers"
        self.filename = toolmatrix
        self.parent = parent

    def _query_remote(self):
        self.available_data = {}
        data = pd.read_excel(self.filename, header=2)
        unique_biotools_ids = set(data.biotoolsID.unique())
        unique_biotools_ids.remove(np.nan)
        unique_tool_ids = set(data.toolID.unique())
        unique_tool_ids.remove(np.nan)

        ### import BioContainers metadata via TRS implementation
        biocontainers = get_request("https://api.biocontainers.pro/ga4gh/trs/v2/tools?limit=200000&sort_field=id&sort_order=asc")
        if biocontainers.status_code == 200:
            biocontainers_data = json.loads(biocontainers.text)
            ### create list of bio.tools IDs with their associated BioContainers IDs
            biocontainers_list = {}
            for container in range(len(biocontainers_data)):
                container_id = biocontainers_data[container]["id"]
                if "identifiers" in biocontainers_data[container]:
                    identifiers = biocontainers_data[container]["identifiers"]
                    # https://stackoverflow.com/a/70672659
                    # https://stackoverflow.com/a/12595082
                    # https://stackoverflow.com/a/4843178
                    # https://stackoverflow.com/a/15340694
                    for id in identifiers:
                        if isinstance(id, str):
                            match_string = "biotools:"
                            if re.search(match_string, id):
                                biotools_id = id.split(":")[1]
                        else:
                            biotools_id = None
                        if biotools_id not in biocontainers_list:
                            biocontainers_list[biotools_id] = container_id

            for biotools_id in unique_biotools_ids:
                if biotools_id in biocontainers_list:
                    #print(biotools_id, self.parent.get_id_from_alt(ToolMatrixDataProvider.ID_BIO_TOOLS, biotools_id))
                    tool_id = self.parent.get_id_from_alt(ToolMatrixDataProvider.ID_BIO_TOOLS, biotools_id)[0]
                    biocontainers_id = biocontainers_list[biotools_id]
                    #biocontainers_url = "https://biocontainers.pro/tools/" + biocontainers_id
                    self.available_data[tool_id] = biocontainers_id

    def _render(self, data):
        return {Dataprovider.FIELD_NAMES.BIOCONTAINERS_LINK: data}


class GadiDataProvider(Dataprovider):

    def __init__(self, key_file):
        super().__init__()
        self.key = open(key_file, "r").readline()
        self.identifier = "GADI"

    def _query_remote(self):
        self.available_data = {}
        #https://stackoverflow.com/a/8685813
        req = get_request("http://130.56.246.237:5000/dump", headers={"Authorization": self.key})
        if req.status_code == 200:
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


class if89DataProvider(Dataprovider):

    def __init__(self, if89_key_file):
        super().__init__()
        self.key = open(if89_key_file, "r").readline()
        self.identifier = "IF89"

    def _query_remote(self):
        self.available_data = {}
        #https://stackoverflow.com/a/8685813
        req = get_request("http://130.56.246.237:5000/dump", headers={"Authorization": self.key})
        
        if req.status_code == 200:
            for line in req.text.split("\n")[:-1]:
                line = line.split(",")
                tool_id = line[0].strip()
                tool_id = tool_id.lower()
                tool_id = tool_id.replace("genomescope2.0", "genomescope")
                tool_id = tool_id.replace("genomescope2", "genomescope")
                tool_id = tool_id.replace("miniconda3", "miniconda")
                tool_id = tool_id.replace("ipa", "pbipa")
                tool_id = tool_id.replace("plink2", "plink")
                tool_id = tool_id.replace("iqtree2", "iq-tree")
                tool_id = tool_id.replace("sratoolkit", "sra-tools")
                tool_id = tool_id.replace("cdhit", "cd-hit")
                tool_id = tool_id.replace("clustal-omega", "clustalo")
                version = line[1]
                if tool_id not in self.available_data:
                    self.available_data[tool_id] = []
                self.available_data[tool_id].append(version)

    def _render(self, data):
        return {Dataprovider.FIELD_NAMES.NCI_IF89_VERSION: data}


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


class ToolDB(DB):
    """represents the database for all known tools"""

    def __init__(self, tool_matrix_file):
        super().__init__()
        data = pd.read_excel(tool_matrix_file, header=2)
        for i in data.toolID:
            self.db[i] = Tool(i)
        del self.db[np.nan]


    @staticmethod
    def convert_tool_to_yaml(tool):
        def translate_publication(val):
           publications = {}
           #if "metadata" in val and not val["metadata"] is None and "title" in val["metadata"]:
           #    publications["title"] = val["metadata"]["title"]
           if "doi" in val and not val["doi"] is None:
               publications["url"] = f"""https://doi.org/{val["doi"]}"""
               if val["metadata"] is None:
                   publications["title"] = val["doi"]
               else:
                   publications["title"] = val["metadata"]["title"]
           if "pmid" in val and not val["pmid"] is None and val["doi"] is None:
               publications["url"] = f"""http://www.ncbi.nlm.nih.gov/pubmed/{val["pmid"]}"""
               if val["metadata"] is None:
                   publications["title"] = val["pmid"]
               else:
                   publications["title"] = val["metadata"]["title"]
           if "pmcid" in val and not val["pmcid"] is None and val["doi"] is None:
               publications["url"] = f"""https://www.ncbi.nlm.nih.gov/pmc/articles/{val["pmcid"]}"""
               if val["metadata"] is None:
                   publications["title"] = val["pmcid"]
               else:
                   publications["title"] = val["metadata"]["title"]
           return publications

        def translate_galaxy(val):
           if not val is None:
               name = val[1]
               description  = val[1] + ": " + val[2]
               version = val[3]
           return {"title": name + " " + version, "url": f"""https://usegalaxy.org.au/{val[0]}""", "description": description}
        def translate_biocommons_resources(link, description):
            return {"title": description, "url": link}
        def get_edam_data(val):
            term = val["data"]["term"]
            formats = []
            for format in val["format"]:
                term = format["term"]
                formats.append(term)
            return { "term": term, "formats": formats}
        def get_terms(val):
            term = val["term"]
            uri = val["uri"]
            return { "term": term, "url": uri}
        if tool.get(Dataprovider.FIELD_NAMES.INCLUSION) == True:
            return {
                # see https://stackoverflow.com/a/9285148
                # see https://stackoverflow.com/a/62014515
                "description": tool.get(Dataprovider.FIELD_NAMES.DESCRIPTION, ""),
                "name": tool[Dataprovider.FIELD_NAMES.NAME],
                "homepage": tool[Dataprovider.FIELD_NAMES.REPOSITORY_URL] if not pd.isna(tool[Dataprovider.FIELD_NAMES.REPOSITORY_URL]) else "",
                "biotools": tool.get(Dataprovider.FIELD_NAMES.BIOTOOLS_ID, ""),
                "id": tool[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER],
                #"edam-topics": [get_terms(i) for i in tool[Dataprovider.FIELD_NAMES.EDAM_TOPICS]] if isinstance(tool[Dataprovider.FIELD_NAMES.EDAM_TOPICS], list) else "",
                "edam-topics": [i["term"] for i in tool[Dataprovider.FIELD_NAMES.EDAM_TOPICS]] if isinstance(tool[Dataprovider.FIELD_NAMES.EDAM_TOPICS], list) else "",
                #"edam-operations": [get_terms(i) for i in tool[Dataprovider.FIELD_NAMES.EDAM_OPERATIONS]] if Dataprovider.FIELD_NAMES.EDAM_OPERATIONS in tool and isinstance(tool[Dataprovider.FIELD_NAMES.EDAM_OPERATIONS], list) else "",
                "edam-operations": [i["term"] for i in tool[Dataprovider.FIELD_NAMES.EDAM_OPERATIONS]] if Dataprovider.FIELD_NAMES.EDAM_OPERATIONS in tool and isinstance(tool[Dataprovider.FIELD_NAMES.EDAM_OPERATIONS], list) else "",
                "edam-inputs": [get_edam_data(i) for i in tool[Dataprovider.FIELD_NAMES.EDAM_DATA_INPUT]] if Dataprovider.FIELD_NAMES.EDAM_DATA_INPUT in tool and isinstance(tool[Dataprovider.FIELD_NAMES.EDAM_DATA_INPUT], list) else "",
                "edam-outputs": [get_edam_data(i) for i in tool[Dataprovider.FIELD_NAMES.EDAM_DATA_OUTPUT]] if Dataprovider.FIELD_NAMES.EDAM_DATA_OUTPUT in tool and isinstance(tool[Dataprovider.FIELD_NAMES.EDAM_DATA_OUTPUT], list) else "",
                "publications": [translate_publication(i) for i in tool[Dataprovider.FIELD_NAMES.PUBLICATIONS]] if Dataprovider.FIELD_NAMES.PUBLICATIONS in tool and isinstance(tool[Dataprovider.FIELD_NAMES.PUBLICATIONS],list) else "",
                "biocontainers": tool.get(Dataprovider.FIELD_NAMES.BIOCONTAINERS_LINK, ""),
                "license": tool.get(Dataprovider.FIELD_NAMES.LICENSE, ""),
                "resources": [translate_biocommons_resources(tool.get(Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_LINK, ""), tool.get(Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_DESCRIPTION, ""))],
                "galaxy": [translate_galaxy(i) for i in tool[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK]] if Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK in tool and isinstance(tool[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK],list) else "",
                "nci-gadi": [i for i in tool[Dataprovider.FIELD_NAMES.NCI_GADI_VERSION]] if Dataprovider.FIELD_NAMES.NCI_GADI_VERSION in tool and isinstance(tool[Dataprovider.FIELD_NAMES.NCI_GADI_VERSION], list) else "",
                "nci-if89": [i for i in tool[Dataprovider.FIELD_NAMES.NCI_IF89_VERSION]] if Dataprovider.FIELD_NAMES.NCI_IF89_VERSION in tool and isinstance(tool[Dataprovider.FIELD_NAMES.NCI_IF89_VERSION], list) else "",
                "pawsey": [i for i in tool[Dataprovider.FIELD_NAMES.PAWSEY_SETONIX_VERSION]] if Dataprovider.FIELD_NAMES.PAWSEY_SETONIX_VERSION in tool and isinstance(tool[Dataprovider.FIELD_NAMES.PAWSEY_SETONIX_VERSION], list) else "",
                "bunya": [i for i in tool[Dataprovider.FIELD_NAMES.QRISCLOUD_VERSION]] if Dataprovider.FIELD_NAMES.QRISCLOUD_VERSION in tool and isinstance(tool[Dataprovider.FIELD_NAMES.QRISCLOUD_VERSION], list) else "",
            }


    def get_formatted_yaml(self):
        tool_list = self.get_data_only()

        tool_list_dictionary = list(map(ToolDB.convert_tool_to_yaml, tool_list))
        # filter null values from tool list (i.e. those annotated with "n" for the "include?" field
        tool_list_dictionary = list(filter(lambda x: x is not None, tool_list_dictionary))
        tool_list_dictionary = list(itertools.filterfalse(lambda x: x['galaxy'] == "" and x['nci-gadi'] == "" and x['nci-if89'] == "" and x['pawsey'] == "" and x['bunya'] == "" and pd.isna(x['resources'][0]['url']), tool_list_dictionary))
        # see https://stackoverflow.com/q/71281303
        # see https://stackoverflow.com/a/6160082
        with open("data/data.yaml", 'w') as file:
            yaml.dump(tool_list_dictionary, file, default_flow_style=False)


### function below is from ToolFinder v1 that used R for table generation

#    def get_formatted_table(self):
#        import urllib
#        tool_table = self.get_data()
#        tool_data = self.get_data_only()
#        formatted_list = []
#        for index, row in tool_table.iterrows():
#            if not row[Dataprovider.FIELD_NAMES.INCLUSION]:
#                continue
#            tool_line = []
#            b = row[Dataprovider.FIELD_NAMES.NAME].replace("_", " ")
#            c = """<p class="name" data-toggle="popover" data-trigger="hover" title="Description" data-content="%s">""" % (row[Dataprovider.FIELD_NAMES.DESCRIPTION])
#            tool_line.append(c + b + """</p>""" if not pd.isna(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) else
#                             """<p class="name" data-toggle="popover" data-trigger="hover" title="Description" data-content="No metadata available.">""" + b + """</p>""")
#            tool_line.append((row[Dataprovider.FIELD_NAMES.DESCRIPTION]) if not pd.isna(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) else "No description available.")
#            tool_line.append("""<a class="homepage" href="%s" ga-product="homepage" ga-id="%s">%s</a>"""%(row[Dataprovider.FIELD_NAMES.REPOSITORY_URL], row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER], row[Dataprovider.FIELD_NAMES.NAME]) if not pd.isna(row[Dataprovider.FIELD_NAMES.REPOSITORY_URL]) else "")
#            if pd.isna(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]):
#                tool_line.append("")
#            else:
#                tool_line.append("""<a class="biotools" href="https://bio.tools/%s" ga-product="biotool" ga-id="%s"><img src="./images/elixir_biotools_transparent.png" style="width:50px;"></a>""" % (
#                row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID], row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER]))
#            tool_line.append(row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER] if not pd.isna(row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER]) else "")
#            if isinstance(row[Dataprovider.FIELD_NAMES.EDAM_TOPICS], list):
#                tool_line.append("".join(["""<p class="tags">%s</p>""" % x["term"] for x in row[Dataprovider.FIELD_NAMES.EDAM_TOPICS]]))
#            else:
#                tool_line.append("")
#            if isinstance(row[Dataprovider.FIELD_NAMES.PUBLICATIONS], list):
#                tool_line.append("<br \>".join(list(map(lambda x:f"""<a class="publication-title" href="https://doi.org/{x["doi"]}" ga-product="publication" ga-id="%s"">{x["metadata"]["title"] if x["metadata"] is not None else "DOI:"+x["doi"]}</a>"""% (row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER]) if x["doi"] is not None else
#                                                        f"""<a class="publication-title" href="http://www.ncbi.nlm.nih.gov/pubmed/{x["pmid"]}" ga-product="publication" ga-id="%s">{x["metadata"]["title"] if x["metadata"] is not None else "PMID:"+x["pmid"]}</a>"""% (row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER]) if x["pmid"] is not None else
#                                                        f"""<a class="publication-title" href="https://www.ncbi.nlm.nih.gov/pmc/articles/{x["pmcid"]}" ga-product="publication" ga-id="%s">{x["metadata"]["title"] if x["metadata"] is not None else "PMCID:"+x["pmcid"]}</a>"""% (row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER]) if x["pmcid"] is not None else
#                                                        "",row[Dataprovider.FIELD_NAMES.PUBLICATIONS]))))
#            else:
#                tool_line.append("")
#            tool_line.append("""<a class="containers" href="https://biocontainers.pro/tools/%s" ga-product="containers" ga-id="%s">%s</a>"""%(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID], row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER], row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) if not pd.isna(row[Dataprovider.FIELD_NAMES.BIOTOOLS_ID]) else "")
#            tool_line.append(row[Dataprovider.FIELD_NAMES.LICENSE] if not pd.isna(row[Dataprovider.FIELD_NAMES.LICENSE]) else "")
#            tool_line.append("""<a href="%s" ga-product="biocommons" ga-id="%s">%s</a>""" %(row[Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_LINK], row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER], row[Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_DESCRIPTION]) if not pd.isna(row[Dataprovider.FIELD_NAMES.BIOCOMMONS_DOCUMENTATION_LINK]) else "")
#            if isinstance(row[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK], list):
#                # see https://stackoverflow.com/a/2906586
#                # see https://stackoverflow.com/questions/5618878/how-to-convert-list-to-string
#                #tool_line.append("<br \>".join(["""<button class="galaxy-link" onclick="window.open('https://usegalaxy.org.au/%s','_blank').focus()">%s</button>""" %d for d in row[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK]]))
#                a = ["""<button class="galaxy-link" onclick="window.open('https://usegalaxy.org.au/%s','_blank').focus()" ga-product="galaxy" ga-id="%s">%s</button>"""% (x[0], row[Dataprovider.FIELD_NAMES.TOOL_IDENTIFIER], x[1] + "-" + x[2]) for x in row[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK]]
#                     #%d for d in row[Dataprovider.FIELD_NAMES.GALAXY_AUSTRALIA_LAUNCH_LINK]]
#                if len(a)>1:
#                    tool_line.append("""<ul class="galaxy-links-holder"><li class="closed galaxy-collapsible" onclick="$(this).parent('.galaxy-links-holder').find('.galaxy-links').toggle({duration:200,start:function(){$(this).parent('.galaxy-links-holder').find('.galaxy-collapsible').toggleClass('closed open')}})" ><span class="galaxy-link-toggle">""" + str(len(a)) + " tool" + ("s" if len(a)>1 else "") + """</span><span class="button"/></li><ul class="galaxy-links" style="display: none;">""" + str("".join(a)) + "</li></ul></ul>")
#                else:
#                    tool_line.append("""<ul class="galaxy-links">""" + str("".join(a)) + "</ul>")
#            else:
#                tool_line.append("")
#            if isinstance(row[Dataprovider.FIELD_NAMES.NCI_GADI_VERSION], list):
#                tool_line.append("".join("""<p class="version">%s</p>""" % x for x in row[Dataprovider.FIELD_NAMES.NCI_GADI_VERSION]))
#            else:
#                tool_line.append("")
#            if isinstance(row[Dataprovider.FIELD_NAMES.NCI_IF89_VERSION], list):
#                tool_line.append("".join("""<p class="version">%s</p>""" % x for x in row[Dataprovider.FIELD_NAMES.NCI_IF89_VERSION]))
#            else:
#                tool_line.append("")
#            if isinstance(row[Dataprovider.FIELD_NAMES.PAWSEY_SETONIX_VERSION], list):
#                tool_line.append("".join("""<p class="version">%s</p>""" % x for x in row[Dataprovider.FIELD_NAMES.PAWSEY_SETONIX_VERSION]))
#            else:
#                tool_line.append("")
#            if isinstance(row[Dataprovider.FIELD_NAMES.QRISCLOUD_VERSION], list):
#                tool_line.append("".join("""<p class="version">%s</p>""" % x for x in row[Dataprovider.FIELD_NAMES.QRISCLOUD_VERSION]))
#            else:
#                tool_line.append("")
#            formatted_list.append(tool_line)
#        # see https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.dropna.html
#        # see https://stackoverflow.com/a/73601776
#        temp_list = pd.DataFrame(formatted_list, columns=["Tool / workflow name","description","homepage","biotools_link","Tool identifier (module name / bio.tools ID / placeholder)","Topic (EDAM, if available)","Publications","BioContainers link","License","BioCommons Documentation","Galaxy Australia","NCI (Gadi)","NCI (if89)","Pawsey (Setonix)","QRIScloud / UQ-RCC (Bunya)"])
#        final_list = temp_list.replace('', pd.NA).dropna(how = 'all', subset = ["BioCommons Documentation","Galaxy Australia","NCI (Gadi)","NCI (if89)","Pawsey (Setonix)","QRIScloud / UQ-RCC (Bunya)"])
#        return final_list
