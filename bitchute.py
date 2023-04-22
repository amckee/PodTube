#!/usr/bin/python3

# basic, standard libs
import logging
import requests

# web grabbing and parsing libs
from bs4 import BeautifulSoup

from feedgen.feed import FeedGenerator

from tornado import web

## setup timezone object, needed for pubdate
import datetime, pytz
from pytz import timezone
tz = timezone('US/Central')

__version__ = 'v2022.12.20.1'

class ChannelHandler(web.RequestHandler):
    def head(self, channel):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    def get(self, channel):
        # make/build RSS feed
        url = "https://bitchute.com/channel/%s/?showall=1" % channel
        logging.debug("Handling Bitchute channel: %s" % url)
        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( channel )
        self.write( feed )
        self.finish()

    def get_html( self, channel ):
        url = "https://bitchute.com/channel/%s/?showall=1" % channel
        logging.info("Bitchute URL: %s" % url)
        r = requests.get( url )
        bs = BeautifulSoup( r.text, "lxml" )
        html = str(bs.find("div", "container"))
        return html

    def generate_rss( self, channel ):
        logging.info("Bitchute URL: %s" % channel)
        bs = BeautifulSoup( self.get_html( channel ) , "lxml" )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        ## gather channel information
        el = bs.find("div", "channel-banner")
        feed.title( el.find("p", "name").text )
        #feed.description( el.find("div", "channel-videos-text").text )
        feed.image( el.find("div", "image-container").find("img")['data-src'] )
        feed.description( "Bitchute user name: %s" % el.find("p", "owner").text )
        feed.id( el.find("a", "spa")['href'] )
        feedurl = "https://bitchute.com" + el.find("a", "spa")['href']
        feed.link( {'href': feedurl, 'rel': 'self'} )
        #feed.author( el.find("p", "owner").text )
        feed.language('en')

        ## loop through videos build feed item dict
        vids = bs.find_all("div", "channel-videos-container")
        vidcount = len( vids )
        itemcounter = 0
        for vid in vids:
            item = feed.add_entry()
            vidtitle = vid.find("div", "channel-videos-title").text
            item.title( vidtitle )
            logging.info( "Found video: %s" % vidtitle )
            item.description( vid.find("div", "channel-videos-text").text )

            ## why does this work fine in youtube.py!?
            vidimage = vid.find("div", "channel-videos-image").find("img")['data-src']
            item.podcast.itunes_image( vidimage )
            item.image = vidimage

            link = vid.find("div", "channel-videos-title").find("a", "spa")['href']

            item.link( 
                href = f'http://{self.request.host}/bitchute{link}',
                title = vid.find("div", "channel-videos-title").text
            )

            viddate = " ".join([vid.find("div", "channel-videos-details").text.strip(), str(itemcounter)])

            date = datetime.datetime.strptime(  viddate, "%b %d, %Y %M" ).astimezone( tz )
            item.pubDate( date )
            item.enclosure(
                url = f'http://{self.request.host}/bitchute{link}',
                type = "video/mp4"
            )

            # span.video-duration
            item.podcast.itunes_duration( vid.find("span", "video-duration").text )

            itemcounter += 1
        return feed.rss_str( pretty=True )

def get_bitchute_url(video):
    r = requests.get("https://bitchute.com/video/%s" % video)
    bs = BeautifulSoup( r.text, "html.parser" )
    vidurl = bs.find("video").find("source")['src']
    return vidurl

class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.info("Video: %s" % video)
        self.redirect( get_bitchute_url(video) )
