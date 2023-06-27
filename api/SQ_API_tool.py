import re
import requests
import json
from requests.auth import HTTPBasicAuth
import markdownify

#function to format json better
def jprint(obj):
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)

#function to get issues from json response in SQ
def getIssues(jsonData):
    allIssues = []
    if jsonData and 'issues' in jsonData:
        for issue in jsonData['issues']:
            allIssues.append(issue)
        return allIssues

#The log in credentials for the api user that will be making the calls from SonarQube
#All of the below values should not be stored in plaintext, these are just for the demo
API_KEY_SQ = 'squ_92faf4c6fdc6d834b5c59f2ffa7418a95830e69c'
USER_AGENT_SQ = 'api_user'
USER_PASS_SQ = 'apiTesting'

#simple authentication for sonarqube
basicAuth = HTTPBasicAuth(USER_AGENT_SQ, USER_PASS_SQ)

"""
#this block will close out all re-opened issues to clean up the SQ dashboard 
print("-----Closing Re-Opened SQ Issues")

reOpenedPayload = { 
    'componentKeys': 'zwadhams_Embedded-Systems-Robotics_AYibu6FRayQ69Q6kvVmx',
    'ps': 500, 
    'types': 'BUG,VULNERABILITY',
    'severities': 'BLOCKER,CRITICAL',
    'statuses': 'REOPENED'
}
reOpenedResponse = requests.get("http://localhost:9000/api/issues/search", auth=basicAuth, params=reOpenedPayload)
print("Re-OpenedResponse status code:", reOpenedResponse.status_code)
reOpenedIssues = getIssues(reOpenedResponse.json())

reOpenedKeys = []
for issue in range(len(reOpenedIssues)):
    reOpenedKeys.append(reOpenedIssues[issue].get('key'))
print("-----Found {} Re-Opened issues-----".format(len(reOpenedKeys)))
joinedReOpenedKeys = ','.join(reOpenedKeys)

closePayload = {
    'issues': joinedReOpenedKeys,
    'do_transition': 'resolve' #cannot close re-opened isssues, only resolve 
}
reOpenedClose = requests.post("http://localhost:9000/api/issues/bulk_change", auth=basicAuth, params=closePayload)
print("reopenedClose status code:", reOpenedClose.status_code)

"""
#this block will get the issues we want to create issues in GitLab for 
print("-----Getting data from SonarQube-----")
print("-----Getting bugs and vulnerabilities with severities of blocker or critical -----")

issuesPayload = { #contains all of the parameters for the get request from sonarqube.
    'componentKeys': 'zwadhams_Embedded-Systems-Robotics_AYibu6FRayQ69Q6kvVmx',
    'ps': 1, #the number of issues that will be created
    'types': 'BUG,VULNERABILITY',
    'severities': 'BLOCKER,CRITICAL',
    'statuses': 'OPEN',
    #'assigned': 'false'
}

issuesResponse = requests.get("http://localhost:9000/api/issues/search", auth=basicAuth, params=issuesPayload)
print("issuesResponse status code:", issuesResponse.status_code)

#only stores the data to be worked with if it was successfully gathered, terminates if not 
if issuesResponse and issuesResponse.status_code == 200:
    jsonIssueData = issuesResponse.json() 
else: 
    print("There was an problem with the response. Status code", issuesResponse.status_code, "TERMINATING PROGRAM")
    quit()
print("Total number of issues detected:", jsonIssueData.get('total'))
print("-----Working with issue data to gather relevant info-----")
  
issueData = getIssues(jsonIssueData)

print("-----Working with GitLab API-----")
#This contains the private token to authorize api access, this should not be stored in plaintext outside of demo
gitlabHeaders = {
    'PRIVATE-TOKEN': 'glpat-SQg8v983_MzPFhbK3rBe',
    'Content-Type': 'application/json'
}

for i in range(len(issueData)): #will create an individual issue post in GitLab for each SQ issue found

    snippetPayload = {
        'issueKey': issueData[i].get('key')
    }
    snippetResponse = requests.get("http://localhost:9000/api/sources/issue_snippets", auth=basicAuth, params=snippetPayload)
    print("snippetResponse status code:", snippetResponse.status_code)

    snippetData = snippetResponse.json()
    keyList = list(snippetData.keys())

    #the first key needed to get the code is a long string, this gets it easier and stores it for later use as issueFile
    #the source code is sent and recieved through https by default, this should mitigate some security concerns 

    issueFile = keyList[0]
    numSnippetLines = len(snippetData[issueFile]['sources'])
    mdSource = "<pre>"
    print(issueData[i].get('line'))
    for line in range(numSnippetLines): #highlights the line containing the problem code 
        if snippetData[issueFile]['sources'][line]['line']==issueData[i].get('line'):
            mdSource = mdSource + '<mark>' + '[' + str(snippetData[issueFile]['sources'][line]['line']) + ']' + markdownify.markdownify(snippetData[issueFile]['sources'][line]['code']) + "</mark>  \n"
        else:
            mdSource = mdSource + '[' + str(snippetData[issueFile]['sources'][line]['line']) + ']' + markdownify.markdownify(snippetData[issueFile]['sources'][line]['code']) + "  \n"
    mdSource = mdSource + "</pre>"

    #will get detailed info about the rule that has been violated
    rulesPayload = {
        'key': issueData[i].get('rule')
    }

    ruleInfoResponse = requests.get("http://localhost:9000/api/rules/show", auth=basicAuth, params=rulesPayload)
    print("ruleInfoResponse status code:", ruleInfoResponse.status_code)

    ruleData = ruleInfoResponse.json() if ruleInfoResponse and ruleInfoResponse.status_code == 200 else print("There was an problem with the response. Status code", ruleInfoResponse.status_code)

    #assembles the payload to be sent in the API POST
    gitlabPayload = {
        'id': 46477662, #This is the id of the gitlab repo
        'title': 'SonarQube - {} : {} '.format(issueData[i].get('type').lower(), issueData[i].get('message').lower()),
        'description': "SonarQube has detected an issue and generated an automatic bug or vulnerability report  \n  \n {} text: '{}' at line {} in file {}  \n  \n <h3>Code Snippet</h3>  \n  {}  \n  \n <h2>Rule Description:</h2> {}".format(issueData[i].get('type').lower(), issueData[i].get('message').lower(), issueData[i].get('line'), re.sub("zwadhams_Embedded-Systems-Robotics_AYibu6FRayQ69Q6kvVmx:", "", issueData[i].get('component')), mdSource, ruleData['rule']['mdDesc'])
    }
    #Compresses the payload into json to avoid a 414 post error 
    jsonPayload = json.dumps(gitlabPayload, indent=1)

    print("-----Posting created issue to GitLab-----")
#comment the below lines to stop from posting issues, useful to debug
    issuePost = requests.post("https://gitlab.com/api/v4/projects/46477662/issues",
                           headers=gitlabHeaders, data=jsonPayload)
    print("issuePost status code:", issuePost.status_code)
    if issuePost.status_code == 201:
        print("-----SUCCESS, GitLab issue created successfully-----")

#Assigns all issues to GitLab SQ user to mark that they have been seen and moved into GitLab
print("-----Assigning issues to GitLab user in SonarQube-----")
issueKeys = []
for issue in range(len(issueData)):
    issueKeys.append(issueData[issue].get('key'))

assignPayload = {
    'issues': issueKeys,
    'assign': 'GitLab'
}
assignRequest = requests.post("http://localhost:9000/api/issues/bulk_change", auth=basicAuth, params=assignPayload)
print("assignRequest status code:", assignRequest.status_code)

#TODO-Deal with security hotspots in some way. Mostlikely ignore the SQ workflow and just treat them as normal issues. 

print("SQ/GitLab API Tool Complete")