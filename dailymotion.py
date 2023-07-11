#!/usr/bin/python3
import logging, requests
import datetime, pytz
import json

from feedgen.feed import FeedGenerator
from tornado import web

__version__ = 'v2022.03.23.2'

class ChannelHandler(web.RequestHandler):
    def head(self, channel):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    def get(self, channel):
        logging.info( "Got channel: %s" % channel )

        url = "https://dailymotion.com/user/%s/videos?sort=recent&limit=30&flags=no_live" % channel
        logging.info( "Handling Daily Motion URL: %s" % url )
        
        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( channel )
        self.write( feed )
        self.finish()

    def get_html( self, channel ):
        url = "https://dailymotion.com/%s/videos" % channel
        logging.info("Daily Motion URL: %s" % url)
        r = requests.get( url )
        bs = BeautifulSoup( r.text, "lxml" )
        html = str( bs.find("main") )
        return html

    def generate_rss( self, channel ):
        logging.info("Daily Motion Channel: %s" % channel)

        ## first we need channel information
        url = f'https://api.dailymotion.com/user/{channel}?fields=description%2Cavatar_360_url%2Cid%2Curl%2Cusername'
        r = requests.get( url )
        j = json.loads( r.text )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        ## Get Channel Info
        feed.title( j['username'] )
        feed.image( j['avatar_360_url'] )
        feed.description( j['description'] )
        feed.id( channel )
        feed.link(
            href = f'https://dailymotion.com/{channel}',
            rel = 'self'
        )
        feed.language('en')

        ## now get the recent videos
        url = f'https://api.dailymotion.com/user/{channel}/videos?sort=recent&limit=30&fields=description%2Cduration%2Cid%2Cthumbnail_360_url%2Curl%2Ctitle&flags=no_live'
        r = requests.get( url )
        videos = json.loads(r.text)

        for video in videos['list']:
            item = feed.add_entry()
            item.title( video['title'] )
            item.description( video['description'] )
            item.link(
                href = video['url'],
                title = video['title']
            )

            item.podcast.itunes_duration( video['duration'] )

            item.enclosure(
                url = video['url'],
                type = "video/mp4"
            )
        return feed.rss_str( pretty=True )

def get_video_url( video ):
    url = "https://dailymotion.com/%s" % video
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
        logging.info("DailyMotion Video: %s" % video)
        self.redirect( get_video_url(video) )
