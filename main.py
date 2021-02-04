from typing import Optional
from fastapi import FastAPI
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
    personal_access_token = '<personal_access_token>'
    organization_url = '<organization_url>'
    credentials = BasicAuthentication('', personal_access_token)
    connection = Connection(base_url=organization_url, creds=credentials)
    return connection

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
