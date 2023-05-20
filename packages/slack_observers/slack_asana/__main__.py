import json
import os
import time
from slack_bolt import App
import asana
import sqlalchemy as sqla
import sys
import urllib.parse
import logging
import dotenv

# logging.basicConfig(level=logging.DEBUG)

# Create custom error for connectivity errors ------------------------------------------------

class DBConnectionError(Exception):
    def __init__(self, message="Connection with server timed out"):
        self.message = message
        super().__init__(self.message)


# Function to connect to DataBase ----------------------------------------------------------

def conect(host_server=os.environ['DB_HOST'], port=os.environ['DB_PORT'], db_name=os.environ['DB_NAME']):
    try:
        conn = sqla.create_engine(
            f"mysql+pymysql://{os.environ['DB_USER']}:{urllib.parse.quote_plus(os.environ['DB_PASS'])}@{host_server}:{port}/{db_name}")
        
        return conn

    except Exception as e:
        print(f'\n {e} \n {sys.exc_info()[0]} \n {sys.exc_info()[2].tb_lineno} \n')

# -------------------------------------------------------------


def main(request):
    time.sleep(1)
    s_app = App(token=os.environ['SLACK_BOT_TOKEN'], signing_secret=os.environ['SLACK_SIGN'])  # Slack_bolt app
    a_client = asana.Client.basic_auth(os.environ['ASANA_TOKEN'])  # Asana Client

    stage = 'start'

    try:
        try:
            channel_id = request['channel_id']  # Channel source
        
        except KeyError:
            channel_id = 'C04T1BMPPFV'

        s_app.client.chat_postMessage(channel=channel_id, text="Asana Task creation request received")

        if request['text'] == "hi":
            s_app.client.chat_postMessage(channel=channel_id, text="<@channel> Hello")

        # Task starter
        else:
            struct = request['text'].split('_')
            s_app.client.chat_postMessage(channel=channel_id, text=f"Attempting to create {struct[0]} for {str(struct[1].split('.')[1]).strip()}")

            if len(struct) != 2:
                s_app.client.chat_postMessage(channel=channel_id, text="Task does not comply with project creation structure")
                return {"status_code":500, "message":"Task does not comply with structure"}
            
            else:
                # Get ASANA workspaces and select the superstaff.com.co workspace
                workspaces = a_client.workspaces.find_all({"opt_fields": "is_organization, name"})
                workspace = next(
                    workspace for workspace in workspaces if workspace['name'] == os.environ['ASANA_ORG'])
                stage = 'workspace created'
                # Get ASANA teams in workspace
                teams = a_client.teams.find_by_organization(workspace['gid'])
                stage = 'teams consulted'
                # Get client name and task list                
                conn = conect()
                que1 = sqla.text(f'SELECT short_name, tasks FROM clients WHERE id = {struct[1].split(".")[0]}')

                # Execute querys
                conection = conn.connect()
                result1 = conection.execute(que1)
                resultfull1 = result1.fetchall()
                sel_client = [x for x in resultfull1][0]
                stage = 'queries runned'
                
                # Define project structure
                project = {
                    'name': f'{struct[0].strip().title()} {"" if len(struct[1].split(".")) == 1 else " - " + str(sel_client[0]).strip()} {"" if len(struct[1].split(".")) == 1 else " - " + str(struct[1].split(".")[1]).strip()}',
                    'workspace': workspace['gid']}

                # Get departments to generate task on (From DB)
                to_do_tasks = json.loads(sel_client[1])[struct[0].strip()]

                for dep_involved in to_do_tasks.keys():

                    team = next(team for team in teams if team['name'] == dep_involved)

                    project['team'] = team['gid']
                    # Check projects in team
                    projects_a = a_client.projects.get_projects_for_team(team['gid'])

                    # Check if project would be duplicate
                    if len([p for p in projects_a if p['name'] == project['name']]) > 0:
                        s_app.client.chat_postMessage(channel=channel_id, text=f"PROJECT ALREADY EXISTS IN {dep_involved}")

                    else:
                        # Create project
                        proj_created = a_client.projects.create(project)
                        stage = 'project created in asana'
                        # Join members to project
                                            
                        time.sleep(.5)

                        # Try to get elements in sub departments of main department involved
                        try:
                            for t in to_do_tasks[dep_involved]:
                                task = a_client.tasks.create_in_workspace(workspace['gid'],
                                                                        {'projects': [proj_created['gid']],
                                                                        'name': f'{t}'})

                            s_app.client.chat_postMessage(channel=channel_id, text=f"Task Created {dep_involved}")

                        # If client does not exist, project is already created but manual tasks will be needed
                        except KeyError:
                            s_app.client.chat_postMessage(channel=channel_id, text=f"Client not exists, please create task manually")
    except Exception as e:
        s_app.client.chat_postMessage(channel=channel_id, text=f'Failed after {stage}')
        print(f'\n {e} \n {sys.exc_info()[0]} \n {sys.exc_info()[2].tb_lineno} \n')
        return {"status_code":500, "message":"Fail"}
    
    return {"status_code":200, "message":"Task created successfully"}
#