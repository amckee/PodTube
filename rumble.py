#!/usr/bin/python3
import logging, requests
import datetime, pytz

from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup
from tornado import web

__version__ = 'v2021.12.15.1'

class ChannelHandler(web.RequestHandler):
    def head(self, channel):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    def get(self, channel):
        url = "https://rumble.com/c/" + channel
        logging.info("Handling Rumble channel: %s" % url)
        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( channel )
        self.write( feed )
        self.finish()

    def get_html( self, channel ):
        url = "https://rumble.com/c/" + channel
        logging.info("Rumble URL: %s" % url)
        r = requests.get( url )
        bs = BeautifulSoup( r.text, "lxml" )
        html = str( bs.find("main") )
        return html

    def generate_rss( self, channel ):
        logging.info("Channel: %s" % channel)
        bs = BeautifulSoup( self.get_html( channel ), "lxml" )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        ## Get Channel Info
        feed.title( bs.find("h1", "listing-header--title").text )
        feed.image( bs.find("img", "listing-header--thumb")['src'] )
        feed.description( "--" )
        feed.id( channel )
        feed.link(
            href = f'https://rumble.com/c/{channel}',
            rel = 'self'
        )
        feed.language('en')

        ## Make item list from video list
        videos = bs.find("div", "main-and-sidebar").find("ol").find_all("li")
        for video in videos:
            item = feed.add_entry()
            item.title( video.find("h3", "video-item--title").text )
            item.description( "--" )
            lnk = video.find("a", "video-item--a")
            vid = lnk['href']
            link = f'http://{self.request.host}/rumble/video' + vid
            item.link(
                href = link,
                title = item.title()
            )

            dateformat = "%Y-%m-%d %H:%M:%S"
            viddatetime = video.find("time", "video-item--meta")['datetime']
            viddate = viddatetime.split('T')[0]
            vidtime = viddatetime.split('T')[1]
            vidtime = vidtime.split('-')[0]
            vidpubdate = viddate + " " + vidtime
            item.podcast.itunes_duration( video.find('span', 'video-item--duration')['data-value'] )

            date = datetime.datetime.strptime( vidpubdate, dateformat ).astimezone( pytz.utc )
            item.pubDate( date )
            item.enclosure(
                url = link,
                type = "video/mp4"
            )
        return feed.rss_str( pretty=True )

def get_rumble_url( video ):
    url = "https://rumble.com/%s" % video
    logging.info( "Getting URL: %s" % url )

    ## first, we need to get the embed url from the data set
    r = requests.get( url )
    bs = BeautifulSoup( r.text, 'lxml' )
    import json
    dat=json.loads(bs.find("script", type="application/ld+json").string)
    vidurl = dat[0]['embedUrl']
    logging.info( "Found embedded URL: %s" % vidurl )

    ## second, we get the url to the mp4 file
    ## tricky stuff that will likely break a lot
    ## but we need to parse out values within a javascript function
    ## and remove escape backslashes
    r = requests.get( vidurl )
    bs = BeautifulSoup( r.text, 'lxml' )
    el = bs.find("script").string
    import re
    lnk = re.search( "https.*\.mp4", bs.find( "script" ).string )
    vidurl = lnk.group().split('"')[0].replace('\\', '')
    logging.info( "Finally got the video URL: %s" % vidurl )
    return vidurl

class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.info("Video: %s" % video)
        self.redirect( get_rumble_url(video) )
