import requests
import requests_api as req
import json
import sys
import time

# COMMENTED SECTION BELOW FOR DEBUGGING

# import logging

# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
# try:
#    import http.client as http_client
# except ImportError:
    # Python 2
#    import httplib as http_client
# http_client.HTTPConnection.debuglevel = 1

# You must initialize logging, otherwise you'll not see debug output.
# logging.basicConfig() 
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger('requests.packages.urllib3')
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

maxRequest = 4
requestDelay = 0.5

# Helpers
def _url(path):
    return 'https://api.ciscospark.com/v1' + path

def findroomidbyname (at, roomname):
    room_dict = get_rooms(at)    
    for room in room_dict['items']:
#        print (room['title'])
        if (room['title'] == roomname):roomid = room['id']    
    return roomid

# GET Requests
def get_people(at, email='', displayname='', max_return=10):
    headers = {'Authorization':at}
    payload = {'max':max_return}
    if (email != ''):
        payload['email'] = email
    if (displayname != ''):
        payload['displayName'] = displayname
#    print (payload)
    resp = req.get(_url('/people'), params=payload, headers=headers)
    return resp

def get_persondetails(at, personId):
    headers = {'Authorization':at}
    resp = req.get(_url('/people/{:s}/'.format(personId)), headers=headers)
    return resp

def get_me(at):
    headers = {'Authorization':at}
    resp = req.get(_url('/people/me'), headers=headers)
    return resp

def get_rooms(at, max_return=0):
    headers = {'Authorization':at}
    payload = {}
    if (max_return > 0):
        payload['max'] = max_return
    resp = req.get(_url('/rooms'), params=payload, headers=headers)
    return resp

def get_room(at, roomId):
    headers = {'Authorization':at}
    payload = {'showSipAddress':'true'}
    resp = req.get(_url('/rooms/{:s}'.format(roomId)), params=payload, headers=headers)
    return resp

def get_memberships(at, roomId='', personId='', personEmail='', max_return=0):
    headers = {'Authorization':at}
    payload = {}
    if (roomId != ''):
        payload['roomId'] = roomId
    if (personId != ''):
        payload['personId'] = personId
    if (personEmail != ''):
        payload['personEmail'] = personEmail
    if (max_return > 0):
        payload['max'] = max_return
    resp = req.get(_url('/memberships'), params=payload, headers=headers)
    return resp

def get_membership(at, membershipId):
    headers = {'Authorization':at}
    resp = req.get(_url('/memberships/{:s}'.format(membershipId)), headers=headers)
    return resp

def get_messages(at, roomId):
    headers = {'Authorization':at, 'content-type':'application/json'}
    payload = {'roomId':roomId}
    resp = req.get(_url('/messages'), params=payload, headers=headers)
    return resp

def get_message(at, messageId):
    headers = {'Authorization':at}
    resp = req.get(_url('/messages/{:s}'.format(messageId)), headers=headers)
    return resp

def get_webhooks(at, max_return=0):
    headers = {'Authorization':at}
    payload = {}
    if (max_return > 0):
        payload['max'] = max_return
    resp = req.get(_url('/webhooks'), params=payload, headers=headers)
    return resp

def get_webhook(at, webhookId):
    headers = {'Authorization':at}
    resp = req.get(_url('/webhooks/{:s}'.format(webhookId)), headers=headers)
    return resp

# POST requests
def post_createroom(at, title):
    headers = {'Authorization':at, 'content-type':'application/json'}
    payload = {'title':title}
    resp = req.post(url=_url('/rooms'), json=payload, headers=headers)
    return resp

def post_message(at, roomId, text, toPersonId='', toPersonEmail=''):
    headers = {'Authorization':at, 'content-type':'application/json'}
    payload = {'roomId':roomId, 'text':text}
    if (toPersonId != ''):
        payload['toPersonId'] = toPersonId
    if (toPersonEmail != ''):
        payload['toPersonEmail'] = toPersonEmail
    resp = req.post(url=_url('/messages'), json=payload, headers=headers)
    return resp

def post_rich_text(at, roomId, text, toPersonId='', toPersonEmail=''):
    headers = {'Authorization':at, 'content-type':'application/json'}
    payload = {'roomId':roomId, 'markdown':text}
    if (toPersonId != ''):
        payload['toPersonId'] = toPersonId
    if (toPersonEmail != ''):
        payload['toPersonEmail'] = toPersonEmail
    resp = req.post(url=_url('/messages'), json=payload, headers=headers)
    return resp

def post_file(at, roomId, files, text='', toPersonId='', toPersonEmail=''):
    headers = {'Authorization':at, 'content-type':'application/json'}
    payload = {'roomId':roomId, 'files':files}
    if (text != ''):
        payload['text'] = text
    if (toPersonId != ''):
        payload['toPersonId'] = toPersonId
    if (toPersonEmail != ''):
        payload['toPersonEmail'] = toPersonEmail
    resp = req.post(url=_url('/messages'), json=payload, headers=headers)
    return resp

def post_membership(at, roomId, personId=None, personEmail=None, isModerator=False):
    headers = {'Authorization':at, 'content-type':'application/json'}
    payload = {'roomId':roomId, 'isModerator':isModerator}
    if personId is not None and personId != '':
        payload['personId'] = personId
    if personEmail is not None and personEmail != '':
        payload['personEmail'] = personEmail
#     print("Membership request: {}".format(payload))
    resp = req.post(url=_url('/memberships'), json=payload, headers=headers)
    return resp

def post_webhook(at, name, targetUrl, resource, event, webhook_filter):
    headers = {'Authorization':at, 'content-type':'application/json'}
    payload = {'name':name, 'targetUrl':targetUrl, 'resource':resource, 'event':event, 'filter':webhook_filter}
    resp = req.post(url=_url('/webhooks'), json=payload, headers=headers)
    return resp

def post_access_token(client_id, client_secret, code, redirect_uri):
    payload = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': redirect_uri}
    resp = req.post(url=_url('/access_token'), data=payload)

    return resp

def post_refresh_token(client_id, client_secret, refresh_token):
    payload = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token}
    resp = req.post(url=_url('/access_token'), data=payload)

    return resp

# PUTS
def put_room(at, roomId, title='title'):
    headers = {'Authorization':at, 'content-type':'application/json'}
    payload = {'title': title}
    resp = req.put(url=_url('/rooms/{:s}'.format(roomId)), json=payload, headers=headers)
    return resp

def put_membership(at, membershipId, isModerator):
    headers = {'Authorization':at, 'content-type':'application/json'}
    payload = {'isModerator':isModerator}
    resp = req.put(url=_url('/memberships/{:s}'.format(membershipId)), json=payload, headers=headers)
    return resp

def put_webhook(at, webhookId, name, targetUrl):
    headers = {'Authorization':at, 'content-type':'application/json'}
    payload = {'name':name, 'targetUrl':targetUrl}
    resp = req.put(url=_url('/webhooks/{:s}'.format(webhookId)), json=payload, headers=headers)
    return resp

# DELETES

def del_room(at, roomId):
    headers = {'Authorization':at, 'content-type':'application/json'}
    resp = req.delete(url=_url('/rooms/{:s}'.format(roomId)), headers=headers)
    return resp

def del_membership(at, membershipId):
    headers = {'Authorization':at, 'content-type':'application/json'}
    resp = req.delete(url=_url('/memberships/{:s}'.format(membershipId)), headers=headers)
    return resp


def del_message(at, messageId):
    headers = {'Authorization':at, 'content-type':'application/json'}
    resp = req.delete(url=_url('/messages/{:s}'.format(messageId)), headers=headers)
    return resp


def del_webhook(at, webhookId):
    headers = {'Authorization':at, 'content-type':'application/json'}
    resp = req.delete(url=_url('/webhooks/{:s}'.format(webhookId)), headers=headers)
    return resp
