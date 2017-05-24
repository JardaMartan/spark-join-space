# Spark "Join a room" example
Imagine you organize an event and you want all the walk-by attendees to join a Spark space related to the event. Spark space membership is "invitation only" but you do not want to ask each attendee to give you their e-mail address and enter it manually in your Spark client. An ideal way would be to publish a URL or QR code for join.

This Spark integration does two things:
1. Get a person's information (Spark id and e-mail) by asking the person to login to Spark. If the person doesn't have a Spark account, Spark onboarding process is executed. This is to avoid fake e-mail addresses - we let Spark to check the person's identity.
2. Add the person to a Spark space on user's (typically the space creator) behalf

From the attendee perspective it works like this:
1. scan a QR code or enter a URL manually
2. login to Spark in a web browser or create Spark account if needed
3. confirm `people_read` privileges
4. redirect to the Spark space the attendee has been just added to

## How it works
The application has 4 main URLs and needs to have two Spark integration registrations - one for getting the permissions to add attendess to the Spark space and another for getting the attendee's identity.s The URLs are:
1. `http://<your_sever>/owner-auth-redirect/<event_name>`
2. `http://<your_sever>/owner-auth`
3. `http://<your_sever>/join-redirect/<event_name>`
4. `http://<your_sever>/join`
URLs 2 and 4 are used as "Redirect URI" in the Spark integrations.

The Spark space owner should first open `/owner-auth-redirect/<event_name>` URL. This redirects him to Spark authentication page where he is asked to login and confirm the application permissions. Then Spark redirects him to `/owner-auth` URL with additional parameters `code` and `status`. `status` is used to determine the event name. `code` with `secret` (locally stored in `flask_bot.py` in `on_behalf_secret` variable) is then used to generate access and refresh tokens. The tokens are then displayed in the web browser (of course in real life you should not share the tokens with anyone). After this process the application is ready to add attendees to the space associated with `<event_name>`. If needed, someone else can open the `/owner-auth-redirect/<event_name>` URL to change the identity of the user who subscribes the attendees. You just need to make sure that the user is also a member of the space, otherwise he would not be able to add other people there. `/token-renew` URL can be used to renew the existing access token using refresh token (no Spark authentication is required).

An attendee should be directed to `/join-redirect/<event_name>`. This redirects him to Spark authentication page where he is asked to login (or create a Spark account) and confirm the application permissions (`spark:people_read`). After that Spark redirects the attendee to `/join` with parameters `code` and `status`. `status` is used to dtermine which room the attendee would like to join. `code` with `secret` (locally stored in `flask_bot.py` in `join_secret` variable) is then used to get the attendee identity. The application then uses the attendee's Spark id to add him to the space associated with the `<event_name>`. The association is done on behalf of the user whose access token has been last generated using `/owner-auth-redirect/<event_name>`.

At the moment the `<event_name>` has to be manually entered in `flask_bot.py` in the associative array `event_rooms`. Of course for the real life use you should create a web page which would do the event name creation and room association to the event.
Additionally there are following URLs:
1. `http://<your_sever>/webhook/<event_name>` - a skeleton which can be used to read and write messages in the space
2. `http://<your_sever>/token-renew` - an example of access token renewal using refresh token. Access token is valid for 2 weeks so if you do not want to visit the `/owner-auth` URL every 2 weeks, you need to implement an automated renewal process. Of course the real-life renewal should be scheduled in the application instead of being manual.

## How to run the application
### Start the ZEO data store
[ZODB](http://zodb.org) is used for data storage (access and refresh token). In order to achieve parallel access the application needs to access the storage via network uzing [ZEO](http://www.zodb.org/en/latest/articles/ZODB2.html). Before running the application script, start ZEO (for example under `screen`) using `runzeo -f join_space.fs -a 127.0.0.1:5090`.

### Create Spark Integration
Login to [Spark Developer Site](http://developer.ciscospark.com) and under [My Apps](https://developer.ciscospark.com/apps.html) create two new integrations. For example **Access Token Pass** and **Join Space**. **Access Token Pass** will be used for passing the identity of the user who will subscrine attendees to a space. **Join Space** will be used by attendees to join a space. Set following parameters:


| Application | Redirect URI(s) | Scopes  |
| --- | --- | --- |
| Access Token Pass | `http://<your_server>:5000/owner-auth` | spark:people\_read spark:rooms\_read spark:memberships_write |
| Join Space | `http://<your_server>:5000/join` | spark:people\_read |


Copy the **Client ID** and **Client Secret** from both applications. You will need to paste them to `flask_bot.py`. **Client Secret** gets displayed only when you create the application but you can re-generate it later as well. Just don't forget that by re-generating you invalidate the previous secret.

512x512 icon is a mandatory parameter, you may try using this one: http://logok.org/wp-content/uploads/2014/05/Cisco-logo-1024x768.png.

### Create config.py
Get the room id to which you want to subscribe the attendees using https://developer.ciscospark.com/endpoint-rooms-get.html. Copy the `config-sample.py` to `config.py` and open it for editing. Paste the **Client ID** and **Client Secret** from **Join Space** to `join_client_id` and `join_client_secret` variables. Paste the **Client ID** and **Client Secret** from **Access Token Pass** to `on_behalf_client_id` and `on_behalf_client_secret` variables. Modify the `event_rooms` variable: add there a list of your event names and related room ids.

### Start the application script
The application is written in python version 3.x for [Flask](http://flask.pocoo.org) WSGI framework. You can either run it directly by `python3 flask_bot.py` or using [Tornado](http://flask.pocoo.org/snippets/78/) by running `cyclone.py` script. The application listens on HTTP port 5000. The application needs to run on a public IPv4 address. You either need to host it on some publicly accessible server or using some tunnelling technique like [ngrok](http://ngrok.com).

### Test it
Open `http://<your_server>:5000/owner-auth-redirect/tc2017` (`tc2017` is the my testing event name, use your own name a room id as set in previous step). After passing through the authentication process you should get a web page with access and refresh tokens and their expiration times.

In another browser open `http://<your_server>:5000/join-redirect/tc2017`. Enter an attendee's Spark credentials (or try creating a new Spark registration). After passing through the authentication you should be redirected in the web browser to the Spark space which you've just joined. In case of failure you will be redirected to http://www.cisco.com.
