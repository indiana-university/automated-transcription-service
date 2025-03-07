import json
import os
from urllib.request import urlopen
from urllib.request import Request
 
def lambda_handler(event, context):
    webhook = os.environ['WEBHOOK_URL']
    title = event['Records'][0]['Sns']['Subject']
    content = event['Records'][0]['Sns']['Message']
 
    if not webhook or webhook == "DISABLED":
        print(f"notify_teams disabled, logging message instead: {title} {content}")

    if not title:
        title = "ATS notification"

    message = {"summary": title, "sections": [{"activityTitle": title, "activitySubtitle": content}]}
    request_data = json.dumps(message).encode("utf-8")
    req = Request(url=webhook, headers={"Content-Type": "application/json"}, data=request_data, method='POST')

    try:
        response = urlopen(req)
        if response.status != 200:
            print(f"Failed to notify Teams. Response: {response.status}")
        return response.status
    except Exception as e:
        print(e)

 