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
    personal_access_token = 'znhcqwauwvg4xhjodfdsotv5xwkg6facls3m7nl7xysqf7djlveq'
    organization_url = 'https://dev.azure.com/glasswall'
    credentials = BasicAuthentication('', personal_access_token)
    connection = Connection(base_url=organization_url, creds=credentials)
    return connection

def get_jira_connection():
    options = {"server": "https://glasswall.atlassian.net"}
    API_KEY = "CoEUZ5nleiplWH9ON8MW27E8"
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
    
def get_jira_formatted_name(work_item_name):
    ILLEGAL_ITEM=" - "
    LEGAL_REPLACEMENT="\\-"
    jira_formated_name_list = []
    if ILLEGAL_ITEM in work_item_name:
        splited_list = work_item_name.split(ILLEGAL_ITEM)
        for splitted_item in splited_list:
            jira_formated_name_list.append(splitted_item + LEGAL_REPLACEMENT)
        jira_formated_name_list[-1] = jira_formated_name_list[-1].replace(LEGAL_REPLACEMENT, "")
        jira_formated_name_str = "".join(jira_formated_name_list)
        return jira_formated_name_str
    return work_item_name

def create_jira_issue_and_link(key, issue_type, parent_issue, issue_name, jira_connection):
    print(f"-- Create - Creating {key} Issue...")

    new_issue = jira_connection.create_issue(project=key, summary=issue_name, issuetype={"name": issue_type})

    parent_key = jira_connection.issue(parent_issue.key).key
    child_key = jira_connection.issue(new_issue).key

    jira_connection.create_issue_link(type=issue_type, inwardIssue=child_key, outwardIssue=parent_key)

    print(f"-- Create - Created New Issue {new_issue.key}")

@app.get("/sync")
def sync_devops_to_jira():
    to_create=True
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
    #print(data)

    data_to_sync = data['ToSync']

    for program in data_to_sync['PROGRAM']:
        print("Interogating - PROGRAM " + program['Name'])
        program_issues = jira_conn.search_issues(f"project = PROGRAM AND text ~ \"{program['Name']}\"")
        if len(program_issues) == 1:
            print("PROGRAM Found...")


            for project in program['PROJECT']:
                print("Interogating - PROJECT " + project['Name'])
                project_issues = jira_conn.search_issues(f"project = PROJECT AND text ~ \"{project['Name']}\"")
                if len(project_issues) == 1:
                    print("PROJECT Found...")


                    for feature in project['FEATURE']:
                        print("Interogating - FEATURE " + feature['Name'])
                        features_issues = jira_conn.search_issues(f"project = FEATURE AND text ~ \"{feature['Name']}\"")
                        if len(features_issues) == 1:
                            print("FEATURE Found...")


                            for story in feature['STORY']:
                                print("Interogating - STORY " + str(story))
                                print(f"Read - ADO Story No {str(story)}")
                                user_story_id = story #Reassigning for naming

                                work_item = get_work_item(user_story_id, ado_conn)
                                work_item_name = get_work_item_title(work_item)
                                work_item_name = get_jira_formatted_name(work_item_name)

                                query = f"project = STORY AND text ~ \"{work_item_name}\""
                                story_issues = jira_conn.search_issues(query)

                                if len(story_issues) == 1:
                                    print("STORY Found...")
                                    # Do Tasks



                                elif len(story_issues) > 1:
                                    print(f"Too Many STORY jira issues could not find definitive, Skipping...")
                                else:
                                    if to_create:
                                        create_jira_issue_and_link("STORY", "Story", features_issues[0], work_item_name, jira_conn)
                                    else:
                                        print(f"-- Searching, no jira issues found, Skipping...")

                        elif len(features_issues) > 1:
                            print(f"-- Find - Too Many FEATURE jira issues could not find definitive, Skipping...")
                        else:
                            if to_create:
                                create_jira_issue_and_link("FEATURE", "Feature", project_issues[0], feature['Name'], jira_conn)
                            else:
                                print(f"-- Searching, no jira issues found, Skipping...")

                elif len(project_issues) > 1:
                    print(f"-- Find - Too Many PROJECT jira issues could not find definitive, Skipping...")
                else:
                    if to_create:
                        create_jira_issue_and_link("PROJECT", "Project", program_issues[0], project['Name'], jira_conn)
                    else:
                        print(f"-- Searching, no jira issues found, Skipping...")
                    

        elif len(program_issues) > 1:
            print(f"Find - Too Many PROGRAM jira issues could not find definitive, Skipping...")
        else:
            # These will already be pre-defined so no need to Create
            print(f"Searching, no jira issues found, Skipping...")


    print(".")


