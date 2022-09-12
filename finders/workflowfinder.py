import markdown

from .common import Dataprovider, DB
import requests
import json
import pandas as pd

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
            self.available_data[workflow]['data']['projects'] = []
            for project in project_list:
                if project not in self.available_data[workflow]['data']['projects']:
                    self.available_data[workflow]['data']['projects'].append(project)

        # see https://stackoverflow.com/a/70496282 for convert csv to json
        # see https://www.w3schools.com/python/python_json.asp
        # see https://stackoverflow.com/a/70738425
        # see https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_json.html
        link_information = pd.read_csv("./external/deploy_links.csv").set_index('id')
        link_information.to_json('./external/link_information.json')
        # see https://stackoverflow.com/a/58647394 for import json script
        json_file_path = "./external/link_information.json"
        with open(json_file_path, 'r') as j:
            contents = json.loads(j.read())
        launch_links = contents["launch_link"]
        guide = contents["guide"]
        github = contents["github"]
        for workflow in self.available_data:
            launch_link = launch_links[workflow]
            guide_link = guide[workflow]
            github_link = github[workflow]
            self.available_data[workflow]['data']['launch_link'] = launch_link
            self.available_data[workflow]['data']['guide_link'] = guide_link
            self.available_data[workflow]['data']['github_link'] = github_link


    def _render(self, data):
        retval = {}
        if len(data["data"]) > 0:
            workflow_attr = data["data"]["attributes"]
            if workflow_attr["title"]:
                retval[Dataprovider.FIELD_NAMES.TITLE] = (workflow_attr["title"]).replace("_", " ")
            if workflow_attr["license"]:
                retval[Dataprovider.FIELD_NAMES.LICENSE] = workflow_attr["license"]
            #if workflow_attr["description"]:
            #    retval[Dataprovider.FIELD_NAMES.DESCRIPTION] = workflow_attr["description"]
            if workflow_attr["updated_at"]:
                retval[Dataprovider.FIELD_NAMES.UPDATED_AT] = workflow_attr["updated_at"]
            if workflow_attr["tags"]:
                retval[Dataprovider.FIELD_NAMES.TAGS] = workflow_attr["tags"]
            if workflow_attr["doi"]:
                retval[Dataprovider.FIELD_NAMES.DOI] = workflow_attr["doi"]
            if workflow_attr["edam_operations"]:
                retval[Dataprovider.FIELD_NAMES.EDAM_OPS] = workflow_attr["edam_operations"]
            if workflow_attr["edam_topics"]:
                retval[Dataprovider.FIELD_NAMES.EDAM_TOP] = workflow_attr["edam_topics"]
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
            if workflow_data["github_link"]:
                retval[Dataprovider.FIELD_NAMES.GITHUB_LINK] = workflow_data["github_link"]

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

    def get_formatted_table(self):
        workflow_table = self.get_data()
        formatted_list = []
        for index, row in workflow_table.iterrows():
            workflow_line = []
            #see https://www.w3schools.com/html/html_images.asp
            if pd.isna(row[Dataprovider.FIELD_NAMES.GITHUB_LINK]):
                workflow_line.append("""<p class="title"><b>%s</b></p>
                <a href="https://workflowhub.eu%s" ga-product="workflowhub" ga-id="%s"><img src="/images/workflowhub_logo.png" style="width:150px;"></a>""" % (
                row[Dataprovider.FIELD_NAMES.TITLE], row[Dataprovider.FIELD_NAMES.URL], row[Dataprovider.FIELD_NAMES.URL]))
            else:
                workflow_line.append("""<p class="title"><b>%s</b></p><a href="%s" ga-product="github" ga-id="%s"><img src="/images/GitHub-Mark-64px.png" style="width:50px;"></a>
            <a href="https://workflowhub.eu%s" ga-product="workflowhub" ga-id="%s"><img src="/images/workflowhub_logo.png" style="width:150px;"></a>""" % (
                    row[Dataprovider.FIELD_NAMES.TITLE],row[Dataprovider.FIELD_NAMES.GITHUB_LINK],row[Dataprovider.FIELD_NAMES.URL],row[Dataprovider.FIELD_NAMES.URL],row[Dataprovider.FIELD_NAMES.URL]))
            if isinstance(row[Dataprovider.FIELD_NAMES.EDAM_TOP], list):
                workflow_line.append("<br \>".join([
                    """<button class="edam-button" onclick="window.open('%s','_blank').focus()" ga-product="edam-topics" ga-id="%s">%s</button>""" % (x["identifier"], x["label"], x["label"]) for x in row[Dataprovider.FIELD_NAMES.EDAM_TOP]]))
            else:
                workflow_line.append("")
            if isinstance(row[Dataprovider.FIELD_NAMES.EDAM_OPS], list):
                workflow_line.append("<br \>".join(["""<button class="edam-button" onclick="window.open('%s','_blank').focus()" ga-product="edam-ops" ga-id="%s">%s</a>""" % (x["identifier"], x["label"], x["label"]) for x in row[Dataprovider.FIELD_NAMES.EDAM_OPS]]))
            else:
                workflow_line.append("")
            if isinstance(row[Dataprovider.FIELD_NAMES.TAGS], list):
                workflow_line.append("".join(["""<p class="tags">%s</p>""" % x for x in row[Dataprovider.FIELD_NAMES.TAGS]]))
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
        return pd.DataFrame(formatted_list, columns=["title", "EDAM topics", "EDAM operations", "tags","license",
                                                     "updated_at","DOI","projects","guide","open"])