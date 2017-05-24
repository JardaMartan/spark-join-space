# -*- coding: utf-8 -*-
import os, sys
# import Flask
from flask import Flask, request, redirect, url_for, render_template, g

from flask_table import Table, Col

# from urlparse import urlparse
from urllib.parse import urlparse, quote
# import urllib
import transaction
import ZODB, ZODB.FileStorage
from ZODB.POSException import ConflictError, StorageTransactionError
from ZEO import ClientStorage
from persistent import Persistent
import BTrees.OOBTree
import base64

# import  custom-made modules
import requests
import spark_client

from datetime import datetime, timedelta

import config as cfg

# disable warnings about using certificate verification
requests.packages.urllib3.disable_warnings()

# Connection to ZEO server
addr = "127.0.0.1", 5090

ideal_result = 50

# Create an instance of Flask
app = Flask(__name__, static_url_path="/static")
app.config["DEBUG"] = True

#
# access & refresh token object for ZODB storage
#
class Token_data(Persistent):
    
    def __init__(self, access_token, at_expires, refresh_token, rt_expires):
        self.access_token = access_token
        self.at_expires_on = datetime.now() + timedelta(seconds=at_expires)
        self.refresh_token = refresh_token
        self.rt_expires_on = datetime.now() + timedelta(seconds=rt_expires)
        
    def row(self):
        return dict(access_token = self.access_token, at_expires_on = self.at_expires_on.strftime("%Y-%m-%d %H:%M:%S"), refresh_token = self.refresh_token, rt_expires_on = self.rt_expires_on.strftime("%Y-%m-%d %H:%M:%S"))

#
# HTML table for token display
#        
class TokenTable(Table):
    access_token = Col(u"Access Token")
    at_expires_on = Col(u"AT Expires")
    refresh_token = Col(u"Refresh Token")
    rt_expires_on = Col(u"RT Expires")

def connect_db():
    storage = ClientStorage.ClientStorage(addr)
    
    # local ZODB storage
    #     storage = ZODB.FileStorage.FileStorage("spark-admin-net.fs")
    db = ZODB.DB(storage)
    zodb_connection = db.open()
    
#     init_database(zodb_connection.root)
    
    return zodb_connection.root, db

def get_db():
    db = getattr(g, '_database', None)
    zodb_root = getattr(g, '_zodb_root', None)
    if (db is None) or (zodb_root is None):
        zodb_root, db = g._zodb_root, g._database = connect_db()
        
    return zodb_root, db

@app.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

#
# init ZODB
#
def init_database(db_root, event_name):
    if not hasattr(db_root, event_name):
        app.logger.debug("Creating new top-level DB for event \"{}\"".format(event_name))
        setattr(db_root, event_name, BTrees.OOBTree.BTree())
    if not getattr(db_root, event_name).has_key("me"):
        app.logger.debug("Creating new \"me\" entry DB")
        getattr(db_root, event_name)["me"] = BTrees.OOBTree.BTree()
    if not getattr(db_root, event_name).has_key("tokens"):
        app.logger.debug("Creating new \"tokens\" entry DB")
        getattr(db_root, event_name)["tokens"] = BTrees.OOBTree.BTree()
    transaction.commit()
    
#
# get database for the event
#
def get_event_db(event_name):
    zodb_root, db = get_db()
    init_database(zodb_root, event_name)
    
    return getattr(zodb_root, event_name)

#
# get information about myself (the user) and store it in db if needed
#
def get_me(event_name):
    event_db = get_event_db(event_name)
    if event_db["me"] is None:
        event_db["me"] = spark_client.get_me(auth_token(event_name))
        transaction.commit()
    
    return event_db["me"]

#
# update information about myself in the db
#
def set_me(event_name, access_token):
    event_db = get_event_db(event_name)
    auth = "Bearer " + access_token
    event_db["me"] = spark_client.get_me(auth)
    transaction.commit()

#
# renew access token using refresh token
# can be used in automated process
#
def renew_auth_token(event_name):
    token_db = get_event_db(event_name)["tokens"]
    owner_token_data = token_db[0]
    app.logger.debug("Original Access token: {}, expires: {}, Refresh token: {}, expires: {}".format(owner_token_data.access_token, owner_token_data.at_expires_on, owner_token_data.refresh_token, owner_token_data.rt_expires_on))        

#     app.logger.debug("data: {}".format(owner_token_data.row()))

    access_info = spark_client.post_refresh_token(cfg.on_behalf_client_id, cfg.on_behalf_secret, owner_token_data.refresh_token)
    app.logger.debug("Access info: {}".format(access_info))
    
    if access_info["status_code"] != 200:
        return None

    owner_token_data = Token_data(access_info["access_token"], access_info["expires_in"], access_info["refresh_token"], access_info["refresh_token_expires_in"])
    app.logger.debug("New Access token: {}, expires: {}, Refresh token: {}, expires: {}".format(owner_token_data.access_token, owner_token_data.at_expires_on, owner_token_data.refresh_token, owner_token_data.rt_expires_on))        
# open the database
    token_db[0] = owner_token_data
    transaction.commit()
    
    return owner_token_data

#
# generate authentication string
#
def auth_token(event_name):
    with app.app_context():
        token_db = get_event_db(event_name)["tokens"]
        owner_token_data = token_db[0]
        
        return "Bearer " + owner_token_data.access_token

#
# sample webhook code for handling Spark space events (e.g. new message)
#    
@app.route("/webhook/<event_name>", methods=["POST"])
def webhook(event_name):
    # Get the json data
    msg_data = request.json
    app.logger.info("received: {}".format(msg_data))
    person_id = msg_data["data"]["personId"]

# ignore message from myself
    spark_me = get_me(event_name)
    if (person_id == spark_me["id"]):
        app.logger.info("Received my own message, ignoring...")
        return "" 
    
    room_id = msg_data["data"]["roomId"]
    
    msg_detail = spark_client.get_message(auth_token(event_name), msg_data["data"]["id"])
    if msg_detail["status_code"] == 200:
        app.logger.info(u"Message detail: {}".format(msg_detail))
    else:
        app.logger.error(u"Failed to fetch message: {}".format(msg_detail))
        return ""

    sender_email = msg_detail["personEmail"].lower()
    
    if "text" in msg_detail:
        message = u""

        msg_text = msg_detail["text"].encode("utf-8").strip().lower()
#     app.logger.info("person id: {0} sent text: {1}".format(personId, msg_text))
    
        result = []
    
        if len(message) > 0:
            spark_client.post_rich_text(auth_token(event_name), room_id, message)
            app.logger.info("Message send result: {}".format(result))

    return ""

#
# generate redirect to Spark authentication to gather the on_behalf user data
#
@app.route("/owner-auth-redirect/<event_name>")
def owner_auth_redirect(event_name):
    if event_name not in cfg.event_rooms.keys():
        return u"Unknown event \"{}\"".format(event_name)
    
    myUrlParts = urlparse(request.url)
    full_redirect_uri = myUrlParts.scheme + "://" + myUrlParts.netloc + url_for("owner_auth")
    
    app.logger.debug("redirect URL: {}".format(full_redirect_uri))

    redirect_uri = quote(full_redirect_uri, safe="")
    scope = ["spark:people_read", "spark:rooms_read", "spark:memberships_write", "spark:kms"]
    scope_uri = quote(" ".join(scope), safe="")
    owner_url = "https://api.ciscospark.com/v1/authorize?client_id={}&response_type=code&redirect_uri={}&scope={}&state={}".format(cfg.on_behalf_client_id, redirect_uri, scope_uri, event_name)

    return redirect(owner_url)

#
# get the on_behalf user data - generate access and refresh tokens
# "state" contains event name passed from /owner-auth-redirect
#
@app.route("/owner-auth")
def owner_auth():
    input_code = request.args.get("code")
    event_name = request.args.get("state")
    app.logger.debug("Owner state (event name): {}, code: {}".format(event_name, input_code))
    myUrlParts = urlparse(request.url)
    full_redirect_uri = myUrlParts.scheme + "://" + myUrlParts.netloc + url_for("owner_auth")
    app.logger.debug("Redirect URI: {}".format(full_redirect_uri))
    
    access_info = spark_client.post_access_token(cfg.on_behalf_client_id, cfg.on_behalf_secret, input_code, full_redirect_uri)
    app.logger.debug("Access info: {}".format(access_info))
    
    if access_info["status_code"] != 200:
        return "Failed"

    set_me(event_name, access_info["access_token"]) # update "me" information

    owner_token_data = Token_data(access_info["access_token"], access_info["expires_in"], access_info["refresh_token"], access_info["refresh_token_expires_in"])
    app.logger.debug("Access token: {}, expires: {}, Refresh token: {}, expires: {}".format(owner_token_data.access_token, owner_token_data.at_expires_on, owner_token_data.refresh_token, owner_token_data.rt_expires_on))        
# open the database
    token_db = get_event_db(event_name)["tokens"]
    token_db[0] = owner_token_data
    transaction.commit()
    
    token_data_dict = [owner_token_data.row()]
    table = TokenTable(token_data_dict)
    context = {"body": u"" + table.__html__()}

    return (render_template("token-info.html", **context))

#
# renew access (and refresh if needed) token using refresh token
#
@app.route("/token-renew/<event_name>")
def token_renew(event_name):
    token_db = get_event_db(event_name)["tokens"]
    owner_token_data = token_db[0]
    token_data_dict = [owner_token_data.row()]
    
    owner_token_data = renew_auth_token(event_name)
    token_data_dict.append(owner_token_data.row())

    table = TokenTable(token_data_dict)
    context = {"body": u"" + table.__html__()}

    return (render_template("token-info.html", **context))

#
# generate a redirect to Spark authentication to gather the attendee data
#
@app.route("/join-redirect/<event_name>", methods=["GET"])
def join_redirect(event_name):
    if event_name not in cfg.event_rooms.keys():
        return u"Unknown event \"{}\"".format(event_name)

    myUrlParts = urlparse(request.url)
    full_redirect_uri = myUrlParts.scheme + "://" + myUrlParts.netloc + url_for("join")
    
    app.logger.debug("redirect URL: {}".format(full_redirect_uri))

    redirect_uri = quote(full_redirect_uri, safe="")
    scope = ["spark:people_read", "spark:kms"]
    scope_uri = quote(" ".join(scope), safe="")
    join_url = "https://api.ciscospark.com/v1/authorize?client_id={}&response_type=code&redirect_uri={}&scope={}&state={}".format(cfg.join_client_id, redirect_uri, scope_uri, event_name)

    return redirect(join_url)

#
# get the attendee information and subscribe him to the event space
#
@app.route("/join", methods=["GET"])
def join():
    input_code = request.args.get("code")
    event_name = request.args.get("state")
    app.logger.debug("Join request, event name derived from \"state\": {}, code: {}".format(event_name, input_code))
    if event_name not in cfg.event_rooms.keys():
        return u"Unknown event \"{}\"".format(event_name)

    myUrlParts = urlparse(request.url)
    full_redirect_uri = myUrlParts.scheme + "://" + myUrlParts.netloc + url_for("join")
    app.logger.debug("Redirect URI: {}".format(full_redirect_uri))
    
    access_info = spark_client.post_access_token(cfg.join_client_id, cfg.join_secret, input_code, full_redirect_uri)
    app.logger.debug("Access info: {}".format(access_info))
    
    if access_info["status_code"] == 200:
        user_at = access_info["access_token"]
        app.logger.debug("Got access token: {}".format(user_at))
        user_info = spark_client.get_me("Bearer " + user_at)
        if user_info["status_code"] == 200:
            room_id = cfg.event_rooms[event_name]
            app.logger.info(u"Request to join the room {} from: {}, user id: {}".format(room_id, user_info, user_info["id"]))
            join_resp = spark_client.post_membership(auth_token(event_name), room_id, personId=user_info["id"])
            app.logger.debug("Join room response: {}".format(join_resp))
            if join_resp["status_code"] in [200, 409]:  # 409 = already in the room (Conflict)
                app.logger.info(u"{} joined the room.".format(user_info["displayName"]))
                room_url = "https://web.ciscospark.com/#/rooms/" + base64.b64decode(room_id).decode().split("/")[-1]  # a room URL (calculated from room_id)
                return redirect(room_url)
#                 return redirect(base64.b64decode(room_id))
        else:
            app.logger.debug("Got user info: {}".format(user_info))

    return redirect("http://www.cisco.com")

# run the application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
