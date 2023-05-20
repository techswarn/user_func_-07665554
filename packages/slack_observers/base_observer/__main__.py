import os
import logging
import dotenv
from flask import Flask, jsonify, request
import requests
import threading
import time


app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/", methods=['GET', 'POST'])
def main():
    return {"statusCode": 200, "headers": {"Contect-Type": "application/json"}, "text": "Hi"}

@app.route("/atask", methods=['POST'])
def atask():
    
    form_data = request.json()
    
    app.logger.info(form_data)
    
    try:
        team_id = form_data['team_id']
        api_app_id = form_data['api_app_id']
        
        if team_id != os.environ['SLACK_TEAM_ID'] or api_app_id != os.environ['SLACK_API_APP_ID']:
            return {"statusCode": 405, "headers": {"Contect-Type": "text/plain"}, "body": "Unauthorized"}
        
        thread = threading.Thread(target=lambda: request.post('https://superstaff-observers-ov3sv.ondigitalocean.app/slack_observers/slack_asana', json=form_data))
        thread.start()
        time.sleep(1)
        return {"statusCode": 200, "headers": {"Contect-Type": "text/plain"}, "body": "Passed to handler"}
    
    
    except KeyError:
        return {"statusCode": 402, "headers": {"Contect-Type": "text/plain"}, "body": "Bad Request"}