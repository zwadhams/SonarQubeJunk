import re
import json
import requests
from requests.auth import HTTPBasicAuth
import markdownify

# ----- HELPER FUNCTIONS -----

# Formats JSON in a readable manner
def jprint(obj):
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)

# Gets issues from JSON response in SQ
def getIssues(jsonData):
    allIssues = []
    if jsonData and 'issues' in jsonData:
        for issue in jsonData['issues']:
            allIssues.append(issue)
        return allIssues

# Gets hotspots from JSON response in SQ
def getHotspots(jsonData):
    allHotspots = []
    if jsonData and 'hotspots' in jsonData:
        for hotspot in jsonData['hotspots']:
            allHotspots.append(hotspot)
        return allHotspots

# Gets detailed info about the rule that an issue has violated
def getRuleInfo(issueKey):
    rulesPayload = {'key': issueKey}
    ruleInfoResponse = requests.get("http://localhost:9000/api/rules/show", auth=basicAuth, params=rulesPayload)
    ruleData = ruleInfoResponse.json() if ruleInfoResponse and ruleInfoResponse.status_code == 200 else print(
        "There was a problem with the response. Status code", ruleInfoResponse.status_code)
    return ruleData['rule']['mdDesc']

# Gets the source code surrounding the problem line and highlights the line
def getSourceSnippets(issueKey, issueLine):
    snippetPayload = {'issueKey': issueKey}
    snippetResponse = requests.get("http://localhost:9000/api/sources/issue_snippets", auth=basicAuth, params=snippetPayload)
    snippetData = snippetResponse.json()
    keyList = list(snippetData.keys())

    # The first key needed to get the code is a long string, this gets it easier and stores it for later use as issueFile
    # The source code is sent and received through HTTPS by default, which should mitigate some security concerns
    issueFile = keyList[0]
    numSnippetLines = len(snippetData[issueFile]['sources'])
    mdSource = "<pre>"
    for line in range(numSnippetLines):  # Highlights the line containing the problem code
        if snippetData[issueFile]['sources'][line]['line'] == issueLine:
            mdSource = mdSource + '<mark>' + '[' + str(snippetData[issueFile]['sources'][line]['line']) + ']' + markdownify.markdownify(
                snippetData[issueFile]['sources'][line]['code']) + "</mark>  \n"
        else:
            mdSource = mdSource + '[' + str(snippetData[issueFile]['sources'][line]['line']) + ']' + markdownify.markdownify(
                snippetData[issueFile]['sources'][line]['code']) + "  \n"
    mdSource = mdSource + "</pre>"
    return mdSource

# ----- END HELPER FUNCTIONS -----

# The login credentials for the API user that will be making the calls from SonarQube
# All of the below values should not be stored in plaintext, these are just for the demo
API_KEY_SQ = 'squ_92faf4c6fdc6d834b5c59f2ffa7418a95830e69c'
USER_AGENT_SQ = 'api_user'
USER_PASS_SQ = 'apiTesting'

# Simple authentication for SonarQube
basicAuth = HTTPBasicAuth(USER_AGENT_SQ, USER_PASS_SQ)

# This block will get the issues we want to create issues in GitLab for
print("-----Getting data from SonarQube-----")
print("-----Getting bugs and vulnerabilities with severities of blocker, critical, or major -----")

issuesPayload = {  # Contains all of the parameters for the GET request from SonarQube.
    'componentKeys': 'zwadhams_Embedded-Systems-Robotics_AYibu6FRayQ69Q6kvVmx',
    'ps': 500,  # The number of issues that will be created, set to 500 max upon deployment
    'types': 'BUG,VULNERABILITY',
    'severities': 'BLOCKER,CRITICAL,MAJOR',
    'statuses': 'OPEN,REOPENED',
    'assigned': 'false'
}

issuesResponse = requests.get("http://localhost:9000/api/issues/search", auth=basicAuth, params=issuesPayload)

# Only stores the data to be worked with if it was successfully gathered, terminates if not
if issuesResponse and issuesResponse.status_code == 200:
    jsonIssueData = issuesResponse.json()
else:
    print("There was a problem with the response. Status code", issuesResponse.status_code, "TERMINATING PROGRAM")
    quit()
print("Total number of issues detected:", jsonIssueData.get('total'))
print("-----Working with issue data to gather relevant info-----")

issueData = getIssues(jsonIssueData)

print("-----Posting Issues to GitLab-----")
# This contains the private token to authorize API access, this should not be stored in plaintext outside of the demo
gitlabHeaders = {
    'PRIVATE-TOKEN': 'glpat-SQg8v983_MzPFhbK3rBe',
    'Content-Type': 'application/json'
}

for i in range(len(issueData)):  # Will create an individual issue post in GitLab for each SQ issue found
    # For labeling purposes
    labels = 'app: sonarqube,State: Dev To Do,'
    if issueData[i].get('type') == 'BUG':
        labels = labels + 'type: bug,'
        if issueData[i].get('severity') == 'BLOCKER':
            labels = labels + 'priority: critical'
        elif issueData[i].get('severity') == 'CRITICAL':
            labels = labels + 'priority: high'
        elif issueData[i].get('severity') == 'MAJOR':
            labels = labels + 'priority: medium'

    elif issueData[i].get('type') == 'VULNERABILITY':
        labels = labels + 'type: vulnerability,'
        if issueData[i].get('severity') == 'BLOCKER':
            labels = labels + 'priority: critical'
        elif issueData[i].get('severity') == 'CRITICAL':
            labels = labels + 'priority: high'
        elif issueData[i].get('severity') == 'MAJOR':
            labels = labels + 'priority: medium'

    # Assembles the payload to be sent in the API POST
    gitlabIssuePayload = {
        'id': 46477662,  # This is the ID of the GitLab repo
        'title': 'SonarQube - {} : {} '.format(issueData[i].get('type').upper(), issueData[i].get('message').lower()),
        'labels': labels,
        'description': "SonarQube has detected an issue and generated an automatic bug or vulnerability report  \n  \n {} text: '{}' at line {} in file {}  \n  \n <h3>Code Snippet</h3>  \n  {}  \n  \n <h2>Rule Description:</h2> {}".format(
            issueData[i].get('type').lower(), issueData[i].get('message').lower(), issueData[i].get('line'),
            re.sub("zwadhams_Embedded-Systems-Robotics_AYibu6FRayQ69Q6kvVmx:", "", issueData[i].get('component')),
            getSourceSnippets(issueData[i].get('key'), issueData[i].get('line')), getRuleInfo(issueData[i].get('rule')))
    }
    # Compresses the payload into JSON to avoid a 414 POST error
    jsonIssuePayload = json.dumps(gitlabIssuePayload, indent=1)

    # Comment the below lines to stop from posting issues, useful for debugging
    issuePost = requests.post("https://gitlab.com/api/v4/projects/46477662/issues",
                              headers=gitlabHeaders, data=jsonIssuePayload)

# Gets security hotspots
print("-----Getting security hotspots-----")
hotspotPayload = {
    'projectKey': 'zwadhams_Embedded-Systems-Robotics_AYibu6FRayQ69Q6kvVmx',
    'ps': 500,  # Number of issues to create
    'status': 'TO_REVIEW'
}
hotspotResponse = requests.get("http://localhost:9000/api/hotspots/search", auth=basicAuth, params=hotspotPayload)
hotspotData = getHotspots(hotspotResponse.json())
print("Total number of security hotspots detected:", len(hotspotData))

for hotspot in range(len(hotspotData)):
    gitlabHotspotPayload = {
        'id': 46477662,  # This is the ID of the GitLab repo
        'title': 'SonarQube - SECURITY HOTSPOT : {} '.format(hotspotData[hotspot].get('message').lower()),
        'labels': 'app: sonarqube,State: Dev To Do,type: security hotspot,priority: minor',
        'description': "SonarQube has detected a security hotspot and has generated a report  \n  \n Hotspot text: '{}' at line {} in file {}  \n  \n <h3>Code Snippet</h3>  \n  {}  \n  \n <h2>Rule Description:</h2> {}".format(
            hotspotData[hotspot].get('message').lower(), hotspotData[hotspot].get('line'),
            re.sub("zwadhams_Embedded-Systems-Robotics_AYibu6FRayQ69Q6kvVmx:", "", hotspotData[hotspot].get('component')),
            getSourceSnippets(hotspotData[hotspot].get('key'), hotspotData[hotspot].get('line')),
            getRuleInfo(hotspotData[hotspot].get('ruleKey')))
    }
    jsonHotspotPayload = json.dumps(gitlabHotspotPayload, indent=1)
    hotspotPost = requests.post("https://gitlab.com/api/v4/projects/46477662/issues",
                                headers=gitlabHeaders, data=jsonHotspotPayload)

# Assigns all issues to GitLab SQ user to mark that they have been seen and moved into GitLab
print("-----Assigning issues to GitLab user in SonarQube-----")
# Bugs and vulnerabilities
issueKeys = []
for issue in range(len(issueData)):
    issueKeys.append(issueData[issue].get('key'))
formattedKeys = str.join(",", issueKeys)  # Must be formatted as a string for the API to accept them

assignPayload = {
    'issues': formattedKeys,
    'assign': 'GitLab'
}
assignRequest = requests.post("http://localhost:9000/api/issues/bulk_change", auth=basicAuth, params=assignPayload)

# Hotspots also need to be set to Reviewed status
for hotspot in range(len(hotspotData)):
    hotspotAssignPayload = {
        'hotspot': hotspotData[hotspot].get('key'),
        'assignee': 'GitLab'
    }
    hotspotAssignRequest = requests.post("http://localhost:9000/api/hotspots/assign", auth=basicAuth,
                                         params=hotspotAssignPayload)
    hotspotReviewPayload = {
        'hotspot': hotspotData[hotspot].get('key'),
        'status': 'REVIEWED',
        'resolution': 'ACKNOWLEDGED',
        'comment': 'This hotspot has been moved to a GitLab issue'
    }
    hotspotReviewRequest = requests.post("http://localhost:9000/api/hotspots/change_status", auth=basicAuth,
                                         params=hotspotReviewPayload)

print("-----All hotspots assigned-----")
print("*****SQ/GitLab API Tool Complete*****")
