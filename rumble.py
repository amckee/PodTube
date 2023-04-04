#!/usr/bin/python3
import logging, requests
import datetime, pytz

from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup
from tornado import web

__version__ = 'v2023.01.17.2'

class ChannelHandler(web.RequestHandler):
    def head(self, channel):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    def get(self, channel):
        logging.info( "Got channel: %s" % channel )

        url = "https://rumble.com/c/%s" % channel
        logging.info( "Handling Rumble URL: %s" % url )
        
        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( channel )
        self.write( feed )
        self.finish()

    def get_html( self, channel ):
        url = "https://rumble.com/c/%s" % channel
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
        try:
            feed.title( bs.find("div", "listing-header--title").find("h1").text )
        except:
            logging.info("Failed to pull channel title. Using provided channel instead")
            feed.title( channel )

        try:
            thumb = bs.find("img", "listing-header--thumb")['src']
            if thumb is not None:
                feed.image( thumb )
        except:
            logging.info("Channel thumbnail not found")
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
            try:
                video.find("span", "video-item--upcoming")
                logging.info("Found upcoming video, skipping")
            except:
                pass
            try:
                video.find("span", "video-item--live")
                logging.info("Found live video, skipping")
            except:
                pass
            try:
                vidduration = video.find('span', 'video-item--duration')['data-value']
            except TypeError:
                logging.warning("Failed to get duration; likely a live video, skipping")
                continue

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

            item.podcast.itunes_duration( vidduration )

            date = datetime.datetime.strptime( vidpubdate, dateformat ).astimezone( pytz.utc )
            item.pubDate( date )
            item.enclosure(
                url = link,
                type = "video/mp4"
            )
        return feed.rss_str( pretty=True )

class UserHandler(web.RequestHandler):
    def head(self, user):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')
    
    def get(self, user):
        logging.info( "Got user: %s" % user )

        url = "https://rumble.com/user/%s" % user
        logging.info( "Handling Rumble URL: %s" % url )

        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( user )
        self.write( feed )
        self.finish()
    
    def get_html( self, user ):
        url = "https://rumble.com/user/%s" % user
        logging.info("Rumble URL: %s" % url)
        r = requests.get( url )
        bs = BeautifulSoup( r.text, 'lxml' )
        html = str( bs.find("main") )
        return html
    
    def generate_rss( self, user ):
        logging.info("User: %s" % user)
        bs = BeautifulSoup( self.get_html( user ), 'lxml' )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        ## Get User/Channel Info
        try:
            feed.title( bs.find("div", "listing-header--title").find("h1").text )
        except:
            logging.info("Failed to pull channel title. Using provided channel instead")
            feed.title( channel )

        feed.image( bs.find("img", "listing-header--thumb")['src'] )
        feed.description( "--" )
        feed.id( user )
        feed.link(
            href = f'https://rumble.com/user/%s' % user,
            rel = 'self'
        )
        feed.language('en')

        ## Assemble RSS items list
        videos = bs.find("div", "main-and-sidebar").find("ol").find_all("li")
        for video in videos:
            item = feed.add_entry()
            item.title( video.find("h3", "video-item--title").text )
            item.description( video.find("a", {'rel': "author"}).text )

            lnk = video.find("a", "video-item--a")
            vid = lnk['href']
            link = f'http://{self.request.host}/rumble/video' + vid
            icon = video.find("img", "video-item--img")['src']
            item.podcast.itunes_image( icon )
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

class CategoryHandler(web.RequestHandler):
    def head(self, category):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')
    
    def get(self, category):
        logging.info( "Got category: %s" % category )

        url = "https://rumble.com/category/%s" % category
        logging.info( "Handling Rumble URL: %s" % category )

        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( category )
        self.write( feed )
        self.finish()
    
    def get_html(self, category):
        url = "https://rumble.com/category/%s" % category
        logging.info("Rumble URL: %s" % url)
        r = requests.get( url )
        bs = BeautifulSoup( r.text, 'lxml' )
        html = str( bs.find("main") )
        return html
    
    def generate_rss( self, category ):
        logging.info( "Category: %s" % category )
        bs = BeautifulSoup( self.get_html( category ), 'lxml' )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        try:
            feed.title( "Rumble: %s" % bs.find("div", "listing-header--title").text )
        except:
            logging.info( "Failed to pull category name" )
            feed.title( category )
        
        feed.description( "New videos from Rumble's %s category page" % category )
        feed.id( category )
        feed.link(
            href = f'https://rumble.com/category/%s' % category,
            rel = 'self'
        )
        feed.language('en')

        ## Assemble RSS items list
        videos = bs.find("div", "main-and-sidebar").find("ol").find_all("li")
        for video in videos:
            ## Check for and skip live videos and upcomming videos
            if video.find("span", "video-item--live") or video.find("span", "video-item--upcoming"):  ##['data-value'] == "LIVE":
                continue

            item = feed.add_entry()
            item.title( video.find("h3", "video-item--title").text )
            item.description( video.find("div", "ellipsis-1").text )
            
            lnk = video.find("a", "video-item--a")
            vid = lnk['href']
            link = f'http://{self.request.host}/rumble/video' + vid
            icon = video.find( "img", "video-item--img" )['src']
            item.podcast.itunes_image( icon )
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
            date = datetime.datetime.strptime( vidpubdate, dateformat ).astimezone( pytz.utc )
            item.pubDate( date )

            item.podcast.itunes_duration( video.find('span', 'video-item--duration')['data-value'] )

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
    for section in lnk.string.split('":"'):
        mtch = re.match( r'^(https.+\.mp4).+$', section )
        if mtch is not None:
            lnk = mtch.group().split('"')[0].replace('\\', '')
            break

    if type(lnk) is str:
        vidurl = lnk
    else:
        vidurl = lnk.group().split('"')[0].replace('\\', '')

    logging.info( "Finally got the video URL: %s" % vidurl )
    return vidurl

class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.info("Video: %s" % video)
        self.redirect( get_rumble_url(video) )
