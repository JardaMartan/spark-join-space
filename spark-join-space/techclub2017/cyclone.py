from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from tornado.web import FallbackHandler, RequestHandler, Application
from tornado.log import enable_pretty_logging
from tornado import autoreload
 
from flask_bot import app, Token_data

class MainHandler(RequestHandler):
    def get(self):
        self.write("This message comes from Tornado ^_^")

tr = WSGIContainer(app)

application = Application([
(r"/tornado", MainHandler),
(r".*", FallbackHandler, dict(fallback=tr)),
])

if __name__ == "__main__":
    enable_pretty_logging()
    application.listen(5000)
    IOLoop.instance().start()