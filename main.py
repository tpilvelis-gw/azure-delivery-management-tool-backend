from typing import Optional
from fastapi import FastAPI
from jira import JIRA
import yaml

from fastapi.middleware.cors import CORSMiddleware

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import pprint

app = FastAPI()

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:80"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def hello_world():
    return {"Hello": "World"}

def get_work_item(user_story_id, connection):
    client = connection.clients.get_work_item_tracking_client()
    work_item = client.get_work_item(user_story_id, expand="Relations")
    return work_item

def get_user_story_children_ids(work_item):

    child_ids = [
        x.url.split("/")[-1] 
        for x in work_item.relations 
            if x.attributes['name'] == "Child" 
    ]
    
    return child_ids

def get_azure_devops_connection():
    personal_access_token = 'and6ey5t35ucjfgpneeollyyezfn7bgxxenqi6sjzzqcxbnqvcrq'
    organization_url = 'https://dev.azure.com/glasswall'
    credentials = BasicAuthentication('', personal_access_token)
    connection = Connection(base_url=organization_url, creds=credentials)
    return connection

def get_jira_connection():
    options = {"server": "https://glasswall.atlassian.net"}
    API_KEY = "iCegsRUWSh8xbOxO5qoG00C1"
    user = "tpilvelis@glasswallsolutions.com"
    jira = JIRA(options, basic_auth=(user, API_KEY))
    return jira

def get_work_item_title(work_item):
    return work_item.fields['System.Title']

@app.get("/user_story/{user_story_id}")
def read_item(user_story_id: int):

    connection = get_azure_devops_connection()

    work_item = get_work_item(user_story_id, connection)
    work_item_name = get_work_item_title(work_item)
    child_ids = sorted(get_user_story_children_ids(work_item))

    tasks = []
    for child_id in child_ids:
        work_item = get_work_item(child_id, connection)
        tasks.append({
            "name": work_item.fields["System.Title"],
            "estimate": work_item.fields["Microsoft.VSTS.Scheduling.StoryPoints"],
            "is_done": 0 if work_item.fields["System.State"] == "New" else 50 if work_item.fields["System.State"] == "Active" else 100 #100 Assumes Closed
        })
        


    return {
        "user_story_id": user_story_id,
        "user_story_name": work_item_name,
        "tasks" : tasks
    }

@app.get("/sync")
def sync_devops_to_jira():
    jira_conn = get_jira_connection()
    ado_conn = get_azure_devops_connection()

    data = None
    with open("config.yml", 'r') as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            return {
                "statusCode" : 400,
                "body" : str(exc)
            }
    print(data)

    data_to_sync = data['ToSync']

    for program in data_to_sync['PROGRAM']:
        print(program['Name'])
        issues = jira_conn.search_issues(f"project = PROGRAM AND text ~ \"{program['Name']}\"")
        if len(issues):
            print("PROGRAM Found...")

        for project in program['PROJECT']:
            print(project['Name']) 

            for feature in project['FEATURE']:
                print(feature['Name'])

                for story in feature['STORY']:
                    print(str(story))



    print(".")