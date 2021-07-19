import logging
import requests
import os,sys
import time
import datetime, pytz

from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from tornado import web

class ChannelHandler(web.RequestHandler):
    @gen.coroutine
    def head(self, channel):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    @gen.coroutine
    def get(self, channel):
        # make/build RSS feed
        url = "https://bitchute.com/channel/%s/?showall=1" % channel
        logging.info("Handling Bitchute Channel: %s" % url)
        self.set_header('Content-type', 'application/rss+xml')
        logging.info("Bitchute Channel: %s" % url)
        feed = self.generate_rss( channel )
        self.write( feed )
        self.finish()

    @gen.coroutine
    def get_html( self, channel ):
        url = "https://bitchute.com/channel/%s/?showall=1" % channel
        logging.info("URL: %s" % url)
        r = requests.get( url )
        bs = BeautifulSoup( r.text, "lxml" )
        html = str(bs.find("div", "container"))
        return html

    @gen.coroutine
    def generate_rss( self, channel ):
        logging.info("Channel: %s" % channel)
        bs = BeautifulSoup( self.get_html( channel ) , "lxml" )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        ## gather channel information
        el = bs.find("div", "channel-banner")
        feed.title( el.find("p", "name").text )
        feed.image( el.find("div", "image-container").find("img")['data-src'] )
        feed.description( "Bitchute user name: %s" % el.find("p", "owner").text )
        feed.id( el.find("a", "spa")['href'] )
        feedurl = "https://bitchute.com" + el.find("a", "spa")['href']
        feed.link({
            'href': feedurl, 
            'rel': 'self'
        })
        feed.language('en')

        ## loop through videos build feed item dict
        for vid in bs.find_all("div", "channel-videos-container"):
            item = feed.add_entry()
            item.title( vid.find("div", "channel-videos-title").text )
            item.description( vid.find("div", "channel-videos-text").text )

            ## why does this work fine in youtube.py!?
            #item.podcast.itunes_image( vid.find("div", "channel-videos-image").find("img")['src'] )
            
            link = vid.find("div", "channel-videos-title").find("a", "spa")['href']

            item.link( 
                href = f'http://{self.request.host}/bitchute{link}',
                title = vid.find("div", "channel-videos-title").text  
            )
            date = datetime.datetime.strptime( vid.find("div", "channel-videos-details").text.strip(), "%b %d, %Y" ).astimezone( pytz.utc )
            item.pubDate( date )
            item.enclosure( 
                url = f'http://{self.request.host}/bitchute{link}',
                type = "video/mp4"
            )
        return feed.rss_str( pretty=True )

def get_bitchute_url(video):
    r = requests.get("https://bitchute.com/video/%s" % video)
    bs = BeautifulSoup( r.text, "html.parser" )
    return bs.find("video").find("source")['src']

class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.info("Video: %s" % video)
        self.redirect(get_bitchute_url(video))