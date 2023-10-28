#!/usr/bin/python3
import logging, requests
import datetime, pytz

from feedgen.feed import FeedGenerator
from bs4 import BeautifulSoup
from tornado import web

headers = { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.104 Safari/537.36' }

class ChannelHandler(web.RequestHandler):

    def head(self, channel):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    def get(self, channel):
        logging.debug( "Got channel: %s" % channel )

        url = "https://rumble.com/c/%s" % channel
        logging.info( "Handling Rumble URL: %s" % url )
        
        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( channel )
        self.write( feed )
        self.finish()

    def get_html( self, channel ):
        url = "https://rumble.com/c/%s" % channel
        logging.info("Rumble URL: %s" % url)
        r = requests.get( url, headers=headers )
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
            feed.title( bs.find("div", "channel-header--title").find("h1").text )
        except:
            logging.error("Failed to pull channel title. Using provided channel instead")
            feed.title( channel )

        try:
            thumb = bs.find("img", "channel-header--thumb")['src']
            if thumb is not None:
                feed.image( thumb )
        except:
            logging.error("Channel thumbnail not found")
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
            if video.find("span", "video-item--upcoming") is not None:
                logging.info("Found upcoming video, skipping")
                continue
            if video.find("span", "video-item--live") is not None:
                logging.info("Found live video, skipping")
                continue

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
        logging.debug( "Got user: %s" % user )

        url = "https://rumble.com/user/%s" % user
        logging.info( "Handling Rumble URL: %s" % url )

        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( user )
        self.write( feed )
        self.finish()
    
    def get_html( self, user ):
        url = "https://rumble.com/user/%s" % user
        logging.info("Rumble URL: %s" % url)
        r = requests.get( url, headers=headers )
        bs = BeautifulSoup( r.text, 'lxml' )
        html = str( bs.find("main") )
        return html
    
    def generate_rss( self, user ):
        logging.debug("User: %s" % user)
        bs = BeautifulSoup( self.get_html( user ), 'lxml' )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        ## Get User/Channel Info
        try:
            feed.title( bs.find("div", "listing-header--title").find("h1").text )
        except:
            logging.info("Failed to pull user title.")
            feed.title( channel )

        try:
            feed.image( bs.find("img", "listing-header--thumb")['src'] )
        except:
            logging.info("Failed to pull user thumbnail.")

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
        url = "https://rumble.com/category/%s/recorded" % category
        logging.info("Rumble URL: %s" % url)
        r = requests.get( url, headers=headers )
        bs = BeautifulSoup( r.text, 'lxml' )
        html = str( bs.find("main") )
        return html

    def generate_rss( self, category ):
        logging.info( "Category: %s" % category )
        bs = BeautifulSoup( self.get_html( category ), 'lxml' )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        try:
            feed.title( "Rumble: %s" % bs.find("h1", "header__heading").text.strip() )
        except:
            logging.error( "Failed to pull category name" )
            feed.title( category )
        
        feed.description( "New videos from Rumble's %s category page" % category )
        feed.id( category )
        feed.link(
            href = f'https://rumble.com/category/%s' % category,
            rel = 'self'
        )
        feed.language('en')

        ## Assemble RSS items list
        videos = bs.find("ol", "recordedstreams").find_all("div", "videostream")
        for video in videos:
            ## Check for and skip live videos and upcomming videos.
            ## Disabled to test if this is needed.
            #if video.find("span", "video-item--live") or video.find("span", "video-item--upcoming"):  ##['data-value'] == "LIVE":
            #    continue

            item = feed.add_entry()
            item.title( video.find("h3", "videostream__title").text.strip() )
            item.description( video.find("span", "channel__name").text.strip() )

            lnk = video.find("a", "videostream__link")
            vid = lnk['href']
            link = f'http://{self.request.host}/rumble/video' + vid
            icon = video.find( "img", "videostream__image" )['src']
            item.podcast.itunes_image( icon )
            item.link(
                href = link,
                title = item.title()
            )

            ## No longer given, leaving this code here in case in comes back in the future
            # dateformat = "%Y-%m-%d %H:%M:%S"
            # viddatetime = video.find("time", "video-item--meta")['datetime']
            # viddate = viddatetime.split('T')[0]
            # vidtime = viddatetime.split('T')[1]
            # vidtime = vidtime.split('-')[0]
            # vidpubdate = viddate + " " + vidtime
            # date = datetime.datetime.strptime( vidpubdate, dateformat ).astimezone( pytz.utc )
            # item.pubDate( date )

            # item.podcast.itunes_duration( video.find('span', 'video-item--duration')['data-value'] )

            item.enclosure(
                url = link,
                type = "video/mp4"
            )
        return feed.rss_str( pretty=True )

def get_rumble_url( video, bitrate=None ):
    url = "https://rumble.com/%s" % video
    logging.debug( "Getting URL: %s" % url )

    ## first, we need to get the embed url from the data set
    headers = { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.104 Safari/537.36' }
    r = requests.get( url, headers=headers )

    # Check for errors from Rumble directly
    if r.status_code == 410:
        logging.error( "Rumble returned 410: Not found" )
        return url
    elif r.status_code == 403:
        logging.error( "Rumble returned 403: Forbidden" )
        return url

    bs = BeautifulSoup( r.text, 'lxml' )

    import json
    dat=json.loads(bs.find("script", type="application/ld+json").string)

    vidurl = dat[0]['embedUrl']
    logging.info( "Found embedded URL: %s" % vidurl )

    embedVidID = vidurl.rstrip('/').split('/')[-1]

    ## second, we get the url to the mp4 file
    ## tricky stuff that will likely break a lot
    ## but we need to parse out values within a javascript function
    ## and remove escape backslashes
    r = requests.get( vidurl, headers=headers )
    bs = BeautifulSoup( r.text, 'lxml' )
    el = bs.find("script").string

    import re
    vidurl = None
    preparsedvids = None

    # Using regex, grab the entire json data set from the javascript function.
    # Note: Expect this to break as Rumble makes more changes.
    regexSearch = None
    try:
        regexSearch = re.search( r';[b|f|h|v]\.f\["%s"\]=.*:[a|d]\(\)\}' % embedVidID, el ).group().replace( r';b.f["%s"]=' % embedVidID, '' ).replace( r';f.f["%s"]=' % embedVidID, '' ).replace( r';h.f["%s"]=' % embedVidID, '' ).replace( r';v.f["%s"]=' % embedVidID, '').replace( r',loaded:d()', '' ).replace( r',loaded:a()', '' )
    except:
        pass

    # try: #again
    #     regexSearch = re.search( )
    vidInfo = None

    if regexSearch is not None:
        vidInfo = json.loads( regexSearch )
        logging.debug("Successfully parsed JSON data")
        for thing in ('ua', 'u'):
            if thing in vidInfo:
                if 'mp4' in vidInfo[thing]:
                    if '360' in vidInfo[thing]['mp4']:
                        logging.info('Found 360p video')
                        vidurl = vidInfo[thing]['mp4']['360']['url']
                    elif '480' in vidInfo[thing]['mp4']:
                        logging.info('Found 480p video')
                        vidurl = vidInfo[thing]['mp4']['480']['url']

        # if vidurl is None:
        #     if 'u' in vidInfo:
        #         if 'mp4' in vidInfo['u']:
        #             if 'url' in vidInfo['u']['mp4']:
        #                 logging.info('Found generic mp4')
        #                 vidurl = vidInfo['u']['mp4']['url']

    ## Fallback method, in case the above code failed to find anything
    if vidurl is None:
        logging.info("Using fallback Rumble 'geturl' method")
        if bitrate is not None:
            # find the requested bitrate video
            for vid in vidInfo[0]:
                ## handle bitrate requests
                if vid == bitrate:
                    vidurl = vid['url']
                    break
        else:
            # find a default bitrate video. 240p first, 360p second, anything at all third
            for res in ('240', '360', '480'):
                if res in vidInfo[0]:
                    vid = vidInfo[0].get(res)
                    if vid is not None:
                        logging.info("Grabbing %sp video" % res)
                        vidurl = vid['url']
                        break
                else:
                    logging.info("%s not found in video JSON" % res)
                
            if vidurl is None:
                for vid in vidInfo[0]:
                    if vidInfo[0][vid]['url'] is not None:
                        logging.info("Grabbing %sp format" % vid)
                        vidurl = vidInfo[0][vid]['url']
                        break

    if vidurl is None:
        logging.error( "Failed to get video: %s" % video)
    else:
        logging.info( "Got the video URL: %s" % vidurl )

    return vidurl

class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.debug("Rumble Video: %s" % video)
        bitrate = None
        if bitrate is not None:
            logging.info("Requesting bitrate: %s" % bitrate)
        vid = get_rumble_url(video, bitrate)
        self.redirect( vid )
