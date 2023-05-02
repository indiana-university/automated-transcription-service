import json
from urllib.request import urlopen
from urllib.request import Request

def notify_teams(webhook, title, content, color="000000") -> int:
    """
    Sends a message to a Teams channel
    webhook: URL for Teams webhook
    title: title of message
    content: message content
    color: color of line to include in message
    RED     0000FF
    YELLOW  FFFF00
    GREEN   00FF00
    """
    if not webhook or webhook == "DISABLED":
        print(f"notify_teams disabled, logging message instead: {title} {content}")
        return 200

    message = {"themeColor": color, "summary": title, "sections": [{"activityTitle": title, "activitySubtitle": content}]}
    request_data = json.dumps(message).encode("utf-8")
    req = Request(url=webhook, headers={"Content-Type": "application/json"}, data=request_data, method='POST')
    try:
        response = urlopen(req)
        if response.status != 200:
            print(f"Failed to notify Teams. Response: {response.status}")
        return response.status
    except Exception as e:
        print(e)
