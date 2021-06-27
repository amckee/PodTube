#!/usr/bin/python3

# basic, standard libs
import logging
from argparse import ArgumentParser
import requests
import os,sys
import time

# web grabbing and parsing libs
from bs4 import BeautifulSoup

from feedgen.feed import FeedGenerator

from tornado import web

## setup timezone object, needed for pubdate
import datetime, pytz
tz = pytz.utc

debug = False

class ChannelHandler(web.RequestHandler):
    def head(self, channel):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')
    
    def get(self, channel):
        # make/build RSS feed
        url = "https://bitchute.com/channel/%s" % channel
        logging.info("Handling Bitchute Channel: %s" % url)
        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( channel )
        self.write( feed )
        self.finish()

    def set_options(self):
        opts = Options()
        opts.set_preference( "browser.tabs.closeWindowWithLastTab", "true" )
        opts.headless = True
        opts.service_log_path = os.devnull
        return opts

    def get_html( self, channel ):
        url = "https://bitchute.com/channel/%s" % channel
        logging.error("URL: %s" % url)
        html = ""
        if debug:
            # Load html from sample file. Avoids repeated requests while debugging.
            with open("bitchute_sample.mhtml") as f:
                html = f.read()
        else:
            # Load the URL and grab the html after javascript gets a chance to do its thing
            r = requests.get( url )
            html = r.text
        return html

    def generate_rss( self, channel ):
        bs = BeautifulSoup( self.get_html( channel ) , "html.parser" )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        ## gather channel information
        el = bs.find("div", "channel-banner")
        feed.title( el.find("p", "name").text )
        #feed.description( el.find("div", "channel-videos-text").text )
        feed.image( el.find("div", "image-container").find("img")['src'] )
        feed.description( "Bitchute user name: %s" % el.find("p", "owner").text )
        feed.id( el.find("a", "spa")['href'] )
        feedurl = "https://bitchute.com/" + el.find("a", "spa")['href']
        feed.link( {'href': feedurl, 'rel': 'self'} )
        #feed.author( el.find("p", "owner").text )
        feed.language('en')

        ## loop through videos build feed item dict
        for vid in bs.find_all("div", "channel-videos-container"):
            item = feed.add_entry()
            item.title( vid.find("div", "channel-videos-title").text )
            item.description( vid.find("div", "channel-videos-text").text )
            link = vid.find("div", "channel-videos-title").find("a", "spa").href
            slink = link.split('/')
            item.link( link )
            date = datetime.datetime.strptime( vid.find("div", "channel-videos-details").text.strip(), "%b %d, %Y" ).astimezone( tz )
            item.pubDate( date )
            item.enclosure(
                url = "http://%s/bitchute/video/%s" % ( self.request.host, link ),
                type="video/mp4"
            )

        return feed.rss_str( pretty=True )
