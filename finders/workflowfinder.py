import markdown

from .common import Dataprovider, DB
import requests
import json
import pandas as pd
import yaml

class WorkflowHubSpaceDataProvider(Dataprovider):

    PROJECT_ID = "WorkflowHub_Project_ID"

    def __init__(self):
        super().__init__()
        self.identifier = "WorkflowHubSpace"

    def _query_remote(self):
        self.available_data = {}
        #https://stackoverflow.com/a/8685813
        req = requests.get("https://workflowhub.eu/programmes/8/workflows.json")
        if req.status_code != 200:
            raise FileNotFoundError(req.url)
        # process request to get the workflow IDs
        space_data = req.json()["data"]
        req = requests.get("https://workflowhub.eu/projects.json")
        if req.status_code != 200:
            raise FileNotFoundError(req.url)
        projects_data = req.json()["data"]
        projectIDs = dict([(x["id"],x["attributes"]["title"]) for x in projects_data])

        # create an array with all the urls we want to request
        url_array = []
        for workflow in space_data:
            id = workflow['id']
            link = workflow['links']['self']
            url = "https://workflowhub.eu%s.json" % link
            url_array.append((id, url))
        for id, url in url_array:
            response = requests.get(url)
            if response.status_code != 200:
                raise FileNotFoundError(response.url)
            workflow_metadata = json.loads(response.text)
            self.available_data[id] = workflow_metadata
        for workflow in self.available_data:
            project_list = [projectIDs[x["id"]] for x in self.available_data[workflow]['data']['relationships']['projects']['data']]
            latest_version = self.available_data[workflow]['data']['attributes']['latest_version']
            all_versions = self.available_data[workflow]['data']['attributes']['versions']
            ### GitHub needs to be extracted from the 'remote' field which appears as part of ['version'][number]['remote'], if this field exists
            for version in all_versions:
                if 'remote' in version and version['version'] == latest_version:
                    remote = version["remote"]
                else:
                    remote = ""
                self.available_data[workflow]['data']['remote'] = remote
            self.available_data[workflow]['data']['projects'] = []
            ### change to build launch link, if it is a Galaxy workflow!
            if self.available_data[workflow]['data']['attributes']['workflow_class']['key'] == "galaxy":
                self.available_data[workflow]['data']['launch_link'] = "https://usegalaxy.org.au/workflows/trs_import?trs_server=workflowhub.eu&trs_id=" + workflow
            else:
                self.available_data[workflow]['data']['launch_link'] = ""
            for project in project_list:
                if project not in self.available_data[workflow]['data']['projects']:
                    self.available_data[workflow]['data']['projects'].append(project)

        # see https://stackoverflow.com/a/70496282 for convert csv to json
        # see https://www.w3schools.com/python/python_json.asp
        # see https://stackoverflow.com/a/70738425
        # see https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_json.html
        link_information = pd.read_csv("./external/deploy_links - deploy_links.csv").set_index('id')
        link_information.to_json('./external/link_information.json')
        # see https://stackoverflow.com/a/58647394 for import json script
        json_file_path = "./external/link_information.json"
        with open(json_file_path, 'r') as j:
            contents = json.loads(j.read())
        guide = contents["guide"]
        for workflow in self.available_data:
            if workflow in guide:
                guide_link = guide[workflow]
                self.available_data[workflow]['data']['guide_link'] = guide_link
            else:
                self.available_data[workflow]['data']['guide_link'] = ""


    def _render(self, data):
        retval = {}
        if len(data["data"]) > 0:
            workflow_attr = data["data"]["attributes"]
            if workflow_attr["title"]:
                retval[Dataprovider.FIELD_NAMES.TITLE] = (workflow_attr["title"]).replace("_", " ")
            if workflow_attr['workflow_class']:
                retval[Dataprovider.FIELD_NAMES.WORKFLOW_CLASS] = workflow_attr['workflow_class']['key']
            if workflow_attr["license"]:
                retval[Dataprovider.FIELD_NAMES.LICENSE] = workflow_attr["license"]
            #if workflow_attr["description"]:
            #    retval[Dataprovider.FIELD_NAMES.DESCRIPTION] = workflow_attr["description"]
            if workflow_attr["updated_at"]:
                retval[Dataprovider.FIELD_NAMES.UPDATED_AT] = workflow_attr["updated_at"].split("T")[0]
            if workflow_attr["tags"]:
                retval[Dataprovider.FIELD_NAMES.TAGS] = workflow_attr["tags"]
            if workflow_attr["doi"]:
                retval[Dataprovider.FIELD_NAMES.DOI] = workflow_attr["doi"]
            if workflow_attr["operation_annotations"]:
                retval[Dataprovider.FIELD_NAMES.EDAM_OPS] = workflow_attr["operation_annotations"]
            if workflow_attr["topic_annotations"]:
                retval[Dataprovider.FIELD_NAMES.EDAM_TOP] = workflow_attr["topic_annotations"]
            if workflow_attr["tools"]:
                retval[Dataprovider.FIELD_NAMES.WORKFLOW_TOOLS] = workflow_attr["tools"]
            workflow_links = data["data"]["links"]
            if workflow_links["self"]:
                retval[Dataprovider.FIELD_NAMES.URL] = workflow_links["self"]
            workflow_data = data["data"]
            if workflow_data["projects"]:
                retval[Dataprovider.FIELD_NAMES.PROJECTS] = workflow_data["projects"]
            if workflow_data["launch_link"]:
                retval[Dataprovider.FIELD_NAMES.LAUNCH_LINK] = workflow_data["launch_link"]
            if workflow_data["guide_link"]:
                retval[Dataprovider.FIELD_NAMES.GUIDE_LINK] = workflow_data["guide_link"]
            if workflow_data["remote"]:
                retval[Dataprovider.FIELD_NAMES.REMOTE_LINK] = workflow_data["remote"]

        return retval


class Workflow:
    """
    Class representing a workflow.
    """

    def __init__(self, uid):
        self.ID = uid
        self.data = {}

    """Add data to a workflow for a provider"""

    def add_data(self, provider):
        self.data[provider.identifier] = provider.get_information(self.ID)

    """retrieve data for a provider"""

    def get_data(self, provider):
        return self.data[provider.identifier]

    """Workflows are keyed by ID"""

    def __eq__(self, other):
        if isinstance(other, Workflow):
            return self.ID == other.ID
        else:
            return False


class WorkflowDB(DB):
    """represents the database for all known workflows"""

    def __init__(self):
        super().__init__()
        self.alternateids = {}
        req = requests.get("https://workflowhub.eu/programmes/8/workflows.json")
        if req.status_code != 200:
            raise FileNotFoundError(req.url)
        # process request to get the workflow IDs required
        space_data = json.loads(req.text)["data"]
        space_workflow_ids = []
        for workflow in space_data:
            id = workflow["id"]
            space_workflow_ids.append(id)
        for i in space_workflow_ids:
            self.db[i] = Workflow(i)


    @staticmethod
    def convert_workflow_to_yaml(workflow):
        def translate_doi(val):
            if "doi" in val and not val["doi"] is None:
                return {"""https://doi.org/{val["doi"]}"""}
        return {
            # see https://stackoverflow.com/a/9285148
            # see https://stackoverflow.com/a/62014515
            "title": workflow.get(Dataprovider.FIELD_NAMES.TITLE, ""),
            "class": workflow.get(Dataprovider.FIELD_NAMES.WORKFLOW_CLASS, ""),
            "url": workflow.get(Dataprovider.FIELD_NAMES.URL, ""),
            "remote_link": workflow.get(Dataprovider.FIELD_NAMES.REMOTE_LINK, ""),
            "edam_top": [i["label"] for i in workflow[
                Dataprovider.FIELD_NAMES.EDAM_TOP]] if Dataprovider.FIELD_NAMES.EDAM_TOP in workflow and isinstance(
                workflow[Dataprovider.FIELD_NAMES.EDAM_TOP], list) else "",
            "edam_ops": [i["label"] for i in workflow[
                Dataprovider.FIELD_NAMES.EDAM_OPS]] if Dataprovider.FIELD_NAMES.EDAM_OPS in workflow and isinstance(
                workflow[Dataprovider.FIELD_NAMES.EDAM_OPS], list) else "",
            "license": workflow.get(Dataprovider.FIELD_NAMES.LICENSE, ""),
            "updated_at": workflow.get(Dataprovider.FIELD_NAMES.UPDATED_AT, ""),
            "doi": workflow.get(Dataprovider.FIELD_NAMES.DOI, ""),
            "projects": [i for i in workflow[Dataprovider.FIELD_NAMES.PROJECTS]] if isinstance(workflow[Dataprovider.FIELD_NAMES.PROJECTS], list) else "",
            "guide_link": workflow.get(Dataprovider.FIELD_NAMES.GUIDE_LINK, ""),
            "launch_link": workflow.get(Dataprovider.FIELD_NAMES.LAUNCH_LINK, ""),
            "tools": workflow.get(Dataprovider.FIELD_NAMES.WORKFLOW_TOOLS, "")
        }


    def get_formatted_yaml(self):
        workflow_list = self.get_data_only()
        workflow_list_dictionary = list(map(WorkflowDB.convert_workflow_to_yaml, workflow_list))
        # see https://stackoverflow.com/q/71281303
        # see https://stackoverflow.com/a/6160082
        with open("data/data_workflows.yaml", 'w') as file:
            yaml.dump(workflow_list_dictionary, file, default_flow_style=False)


    def get_formatted_table(self):
        workflow_table = self.get_data()
        formatted_list = []
        for index, row in workflow_table.iterrows():
            workflow_line = []
            #see https://www.w3schools.com/html/html_images.asp
            if pd.isna(row[Dataprovider.FIELD_NAMES.REMOTE_LINK]):
                workflow_line.append("""<p class="title"><b>%s</b></p>
                <a href="https://workflowhub.eu%s" ga-product="workflowhub" ga-id="%s"><img src="/images/workflowhub_logo.png" style="width:150px;"></a>""" % (
                row[Dataprovider.FIELD_NAMES.TITLE], row[Dataprovider.FIELD_NAMES.URL], row[Dataprovider.FIELD_NAMES.URL]))
            else:
                workflow_line.append("""<p class="title"><b>%s</b></p><a href="%s" ga-product="github" ga-id="%s"><img src="/images/GitHub-Mark-64px.png" style="width:50px;"></a>
            <a href="https://workflowhub.eu%s" ga-product="workflowhub" ga-id="%s"><img src="/images/workflowhub_logo.png" style="width:150px;"></a>""" % (
                    row[Dataprovider.FIELD_NAMES.TITLE],row[Dataprovider.FIELD_NAMES.REMOTE_LINK],row[Dataprovider.FIELD_NAMES.URL],row[Dataprovider.FIELD_NAMES.URL],row[Dataprovider.FIELD_NAMES.URL]))
            if isinstance(row[Dataprovider.FIELD_NAMES.EDAM_TOP], list):
                workflow_line.append("".join(["""<p class="tags">%s</p>""" % x["label"] for x in row[Dataprovider.FIELD_NAMES.EDAM_TOP]]))
            else:
                workflow_line.append("")
            if isinstance(row[Dataprovider.FIELD_NAMES.EDAM_OPS], list):
                workflow_line.append("".join(["""<p class="tags">%s</p>""" % x["label"] for x in row[Dataprovider.FIELD_NAMES.EDAM_OPS]]))
            else:
                workflow_line.append("")
            #workflow_line.append("""<span class="description-text">%s</span>""" % (markdown.markdown(row[Dataprovider.FIELD_NAMES.DESCRIPTION])) if not pd.isna(row[Dataprovider.FIELD_NAMES.DESCRIPTION]) else "")
            workflow_line.append(row[Dataprovider.FIELD_NAMES.LICENSE])
            workflow_line.append(row[Dataprovider.FIELD_NAMES.UPDATED_AT])
            workflow_line.append("""<a href="https://doi.org/%s" ga-product="doi" ga-id="%s">%s</a>""" % (row[Dataprovider.FIELD_NAMES.DOI], row[Dataprovider.FIELD_NAMES.DOI],
            row[Dataprovider.FIELD_NAMES.DOI]) if not pd.isna(row[Dataprovider.FIELD_NAMES.DOI]) else "")
            workflow_line.append("<br \>".join(row[Dataprovider.FIELD_NAMES.PROJECTS]))
            workflow_line.append("""<a href="%s" ga-product="guide" ga-id="%s">See user guide</a>""" % (row[Dataprovider.FIELD_NAMES.GUIDE_LINK], row[Dataprovider.FIELD_NAMES.GUIDE_LINK]) if not pd.isna(row[Dataprovider.FIELD_NAMES.GUIDE_LINK]) else "")
            workflow_line.append("""<a href="%s" ga-product="launch" ga-id="%s">Open workflow on Galaxy Australia</a>""" % (row[Dataprovider.FIELD_NAMES.LAUNCH_LINK], row[Dataprovider.FIELD_NAMES.LAUNCH_LINK]) if not pd.isna(row[Dataprovider.FIELD_NAMES.LAUNCH_LINK]) else "")
            formatted_list.append(workflow_line)
        return pd.DataFrame(formatted_list, columns=["title", "EDAM topics", "EDAM operations","license",
                                                     "updated_at","DOI","projects","guide","open"])