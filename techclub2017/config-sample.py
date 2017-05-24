#!/usr/bin/env python

#
# this part is for Spark integration responsible for user id and e-mail lookup
# you need to create an "integration" on developer.ciscospark.com
# https://developer.ciscospark.com/apps.html
#
join_client_id = "enter_your_app_client_id_here"
join_secret = "enter_your_app_client_secret_here"

#
# this part is for the other Spark integration responsible for adding a user to a room
#
on_behalf_client_id = "enter_your_app_client_id_here"
on_behalf_secret = "enter_your_app_client_secret_here"

#
# room id list related to event names, you can look it up at https://developer.ciscospark.com/endpoint-rooms-get.html
#
event_rooms = {"event_name": "your_room_id"}
