import logging
from tornado import web

class ChannelHandler(web.RequestHandler):
    def head(self, channel):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    def get(self, channel):
        logging.info("In rumble channel handler")

class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.info("Not yet implemented.")
        self.redirect( f'http://{self.request.host}')