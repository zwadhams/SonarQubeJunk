import requests
import json
from requests.auth import HTTPBasicAuth

#function to format json better
def jprint(obj):
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)

#The log in credentials for the api user that will be making the calls
API_KEY = 'squ_92faf4c6fdc6d834b5c59f2ffa7418a95830e69c'
USER_AGENT = 'api_user'
USER_PASS = 'apiTesting'

#simple authentication for sonarqube
basicAuth = HTTPBasicAuth(USER_AGENT, USER_PASS)

issuesPayload = {
    'componentKeys': 'zwadhams_Embedded-Systems-Robotics_AYibu6FRayQ69Q6kvVmx',
    'ps': 2, 
    'types': 'BUG,VULNERABILITY',
    'severities': 'BLOCKER,CRITICAL',   
}

print("-----Getting data from sonarqube server runnning in docker:-----")

print("-----Getting issues with a severity of ??????-----")
issuesResponse = requests.get("http://localhost:9000/api/issues/search", auth=basicAuth, params=issuesPayload)
print("issuesResponse status code:", issuesResponse.status_code)
jprint(issuesResponse.json()) #uses the jprint function defined above to make the output nice

#only stores the data to be worked with if 
jsonIssueData = issuesResponse.json() if issuesResponse and issuesResponse.status_code == 200 else print("There was an issue with the response. Status code", issuesResponse.status_code)
print("-----Working with issue data to gather relevant info-----")

""" example parsing of json
if json_data and 'hoststatuslist' in json_data:
    if 'hoststatus' in json_data['hoststatuslist']:
        for hoststatus in json_data['hoststatuslist']['hoststatus']:
            host_name = hoststatus.get('name')
            status_text = hoststatus.get('status_text')
"""

def getIssues(jsonData):
    allIssues = []
    if jsonData and 'issues' in jsonData:
        for issue in jsonData['issues']:
            allIssues.append(issue)
        return allIssues
  
issueData = getIssues(jsonIssueData)
print(issueData)
