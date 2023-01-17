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
        
        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( channel )
        self.write( feed )
        self.finish()

    def get_html( self, channel ):
        url = "https://www.banned.video/channel/%s" % channel
        logging.info("Banned.video URL: %s" % url)

        rhead = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'}

        r = requests.get( url, headers=rheads )
        bs = BeautifulSoup( r.text, "lxml" )
        html = str( bs.find("css-513p9t") )
        return html

    def generate_rss( self, channel ):
        logging.info("Channel: %s" % channel)
        bs = BeautifulSoup( self.get_html( channel ), "lxml" )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        ## Get Channel Info
        channelHeader = bs.find("div", "css-1cl7rjq")
        try:
            feed.title( channelHeader.find("h1").text )
        except:
            logging.info("Failed to pull channel title. Using provided channel instead")
            feed.title( channel )

        try:
            thumb = channelHeader.find("img")['src']
            if thumb is not None:
                feed.image( thumb )
        except:
            logging.info("Channel thumbnail not found")
        feed.description( channelHeader.find("p").text )
        feed.id( channel )
        feed.link(
            href = f'https://www.banned.video/channel/{channel}',
            rel = 'self'
        )
        feed.language('en')

        ## Make item list from video list
        videos = bs.find("div", "css-16zzmgd").find_all("div", "css-19uxrib")
        for video in videos:
            item = feed.add_entry()

            item.title( video.find("div", "thumbnail-wrapper*").text )
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


class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.info("Video: %s" % video)
        self.redirect( video )
