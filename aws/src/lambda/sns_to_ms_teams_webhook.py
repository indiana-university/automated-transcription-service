import json
from urllib.request import urlopen
from urllib.request import Request

def lambda_handler(event, context):
    webhook = os.environ['WEBHOOK_URL']

    if not webhook or webhook == "DISABLED":
        print(f"notify_teams disabled, logging message instead: {title} {content}")
        return 200

    msg = {'text': event['Records'][0]['Sns']['Message']}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(webhook, headers=headers, data=json.dumps(msg).encode('utf-8'))
    return {
        'statusCode': 200,
        'body': "Teams message sent!"
    }
