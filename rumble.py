#!/usr/bin/python3
import logging, requests
import datetime, pytz
import dateutil

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
        channel_title = bs.find("div", "channel-header--title")
        if channel_title:
            channel_title = channel_title.find("h1").text
            if channel_title:
                feed.title( channel_title )
            else:
                logging.error("Failed to pull channel title. Using provided channel instead")
                feed.title( channel )
        else:
            logging.error("Failed to pull channel title. Using provided channel instead")
            feed.title( channel )

        thumb = bs.find("img", "channel-header--img")
        if thumb:
            feed.image( thumb['src'] )
        else:
            logging.error("Channel thumbnail not found")

        feed.description( "--" )
        feed.id( channel )
        feed.link(
            href = f'https://rumble.com/c/{channel}',
            rel = 'self'
        )
        feed.language('en')

        ## Assemble RSS items list
        videos = bs.find("ol", "thumbnail__grid")
        if videos:
            videos = videos.find_all("div", "videostream")
        else:
            logging.info("Failed to find video list")

        if videos:
            for video in videos:
                ## Check for and skip live videos and upcomming videos
                if video.find("span", "video-item--live") \
                    or video.find("span", "video-item--upcoming") \
                    or video.find("div", "videostream__status--live") \
                    or video.find("div", "videostream__footer--live"):
                    vidTitle = video.find("h3", "thumbnail__title")
                    logging.info("Skipping live/upcoming video: %s" % vidTitle.text.strip())
                    continue

                ## Check for and skip premium videos
                el = video.find("span", "text-link-green")
                if el and el.text == "Premium only":
                    vidTitle = video.find("h3", "thumbnail__title")
                    logging.info("Skipping premium video: %s" % vidTitle.text.strip())

                ## Gather channel information
                item = feed.add_entry()

                ## Gather video information
                vidtitle = video.find("h3", "thumbnail__title")
                if vidtitle:
                    item.title( vidtitle.text.strip() )
                else:
                    logging.info("Failed to pull video thumbnail.")

                viddesc = video.find("div", "videostream__description")
                if viddesc:
                    item.description( viddesc.text.strip() )
                # else:
                #     logging.info("Failed to pull video description.")

                vid = video.find("a", "videostream__link")
                if vid:
                    vid = vid['href']
                else:
                    logging.info("Failed to pull URL to video.")

                link = f'http://{self.request.host}/rumble/video' + vid
                item.link(
                    href = link,
                    title = item.title()
                )

                vidduration = video.find('div', 'videostream__status--duration')
                if vidduration:
                    item.podcast.itunes_duration( vidduration.text.strip() )
                else:
                    logging.info("Failed to pull video duration.")

                viddatetime = video.find("time", "videostream__time")
                if viddatetime:
                    date = dateutil.parser.parse( viddatetime['datetime'] )
                    item.pubDate( date )
                else:
                    logging.info("Failed to pull video date.")

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

        url = "https://rumble.com/user/%s/videos" % user
        logging.info( "Handling Rumble URL: %s" % url )

        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( user )
        self.write( feed )
        self.finish()

    def get_html( self, user ):
        url = "https://rumble.com/user/%s/videos" % user
        logging.info("Rumble URL: %s" % url)
        r = requests.get( url, headers=headers )
        if r.status_code == 404:
            logging.error( "Rumble returned 404: Not found" )
            return None
        bs = BeautifulSoup( r.text, 'lxml' )
        html = str( bs.find("main") )
        return html

    def generate_rss( self, user ):
        logging.debug("User: %s" % user)
        html = self.get_html( user )
        if html is None:
            logging.error("Rumble returned 404: Not found")
            self.set_status( 404 )
            return None
        bs = BeautifulSoup( html, 'lxml' )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        ## Get User/Channel Info
        chantitle = bs.find("div", "channel-header--title")
        if chantitle:
            feed.title( chantitle.find("h1").text )
        else:
            logging.info("Failed to pull user channel title.")
            feed.title( user )

        chanheader = bs.find("img", "channel-header--img")
        if chanheader:
            feed.image( chanheader['src'] )
        else:
            logging.info("Failed to pull user channel thumbnail.")

        feed.description( "--" )
        feed.id( user )
        feed.link(
            href = f'https://rumble.com/user/%s' % user,
            rel = 'self'
        )
        feed.language('en')

        ## Assemble RSS items list
        videos = bs.find("ol", "thumbnail__grid")
        if videos:
            videos = videos.find_all("div", "videostream")
        else:
            logging.info("Failed to find video list")

        if videos:
            for video in videos:
                ## Filter out live and upcoming videos
                if video.find("span", "video-item--upcoming"):
                    logging.info("Found upcoming video, skipping")
                    continue
                if video.find("span", "video-item--live"):
                    logging.info("Found live video, skipping")
                    continue

                item = feed.add_entry()

                ## Gather channel information
                vidtitle = video.find("h3", "thumbnail__title")
                if vidtitle:
                    item.title( vidtitle.text )
                else:
                    logging.info("Failed to get video title")
                    item.title( 'N/A' )

                viddescription = video.find("div", "videostream__description")
                if viddescription:
                    item.description( viddescription.text )
                else:
                    logging.info("Failed to get video description")
                    item.description( 'N/A' )

                lnk = video.find("a", "videostream__link")
                if lnk:
                    vid = lnk['href']
                    link = f'http://{self.request.host}/rumble/video' + vid
                    icon = video.find("img", "thumbnail__image")['src']
                    item.podcast.itunes_image( icon )
                    item.link(
                        href = link,
                        title = item.title()
                    )
                else:
                    item.link(
                        href = "N/A",
                        title = item.title()
                    )

                vidduration = video.find('div', 'videostream__status--duration')
                if vidduration:
                    item.podcast.itunes_duration( vidduration.text.strip() )
                else:
                    logging.info("Failed to get video duration")
                    item.podcast.itunes_duration( 'N/A' )

                viddatetime = video.find("time", "videostream__time")
                if viddatetime:
                    viddatetime = viddatetime['datetime']
                    date = dateutil.parser.parse( viddatetime )
                    item.pubDate( date )
                else:
                    logging.info("Failed to get video date")
                    item.pubDate( datetime.datetime.now() )
                item.enclosure(
                    url = link,
                    type = "video/mp4"
                )
            else:
                logging.error("Failed to find video list")
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

        ## Get Channel Info
        feedtitle = bs.find("h1", "header__heading")
        if feedtitle:
            feed.title( "Rumble: %s" % feedtitle.text.strip() )
        else:
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
        videos = bs.find("ol", "thumbnail__grid")
        if videos:
            videos = videos.find_all("div", "videostream")
        else:
            logging.error("Failed to find video list")
            return

        videos = bs.find("ol", "thumbnail__grid")
        if videos:
            videos = videos.find_all("div", "videostream")
        else:
            logging.error("Failed to find video list")
            return

        if videos:
            for video in videos:
                item = feed.add_entry()

                vidtitle = video.find("h3", "thumbnail__title")
                if vidtitle:
                    item.title( vidtitle.text.strip() )
                else:
                    logging.info("Failed to get video title")
                    item.title( 'N/A' )

                viddescription = video.find("span", "channel__name")
                if viddescription:
                    item.description( viddescription.text.strip() )
                else:
                    logging.info("Failed to get video description/user name")
                    item.description( 'N/A' )


                lnk = video.find("a", "videostream__link")
                if lnk:
                    vid = lnk['href']
                else:
                    logging.info("Failed to get video link")
                    vid = None

                link = f'http://{self.request.host}/rumble/video' + vid

                icon = video.find( "img", "thumbnail__image" )
                if icon:
                    item.podcast.itunes_image( icon['src'] )
                else:
                    logging.info("Failed to get video icon")
                    item.podcast.itunes_image( None )

                item.link(
                    href = link,
                    title = item.title()
                )

                item.enclosure(
                    url = link,
                    type = "video/mp4"
                )

                viddatetime = video.find("time", "videostream__time")
                if viddatetime:
                    item.pubDate = viddatetime['datetime']
                else:
                    logging.info("Failed to get video date")
                    item.pubDate = None

                vidduration = video.find("div", "videostream__status--duration")
                if vidduration:
                    item.podcast.itunes_duration( vidduration.text.strip() )
                else:
                    logging.info("Failed to get video duration")
                    item.podcast.itunes_duration( None )

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
        regexSearch = re.search( r';[b|f|h|v|m|y]\.f\["%s"\]=.*:[a|d|f|u]\(\)\}' % embedVidID, el ).group().replace( r';y.f["%s"]=' % embedVidID, '').replace( r';m.f["%s"]=' % embedVidID, '').replace( r';b.f["%s"]=' % embedVidID, '' ).replace( r';f.f["%s"]=' % embedVidID, '' ).replace( r';h.f["%s"]=' % embedVidID, '' ).replace( r';v.f["%s"]=' % embedVidID, '').replace( r',loaded:f()', '' ).replace( r',loaded:d()', '' ).replace( r',loaded:a()', '' ).replace( r',loaded:u()', '')
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
            ## First try to get video
            try:
                # Resort to default bitrate video. 240p first, 360p second, anything at all third
                for res in ('240', '360', '480'):
                    if res in vidInfo[0]:
                        vid = vidInfo[0].get(res)
                        if vid is not None:
                            logging.info("Grabbing %sp video" % res)
                            vidurl = vid['url']
                            break
                    else:
                        logging.info("%s not found in video JSON" % res)
            except Exception as e:
                logging.error( "Failed to get video: %s - %s" % (video, e) )
                logging.info( "Will try to get audio track")
                if vidInfo['u']['audio'] is not None:
                    vidurl = vidInfo['u']['audio']['url']
                else:
                    logging.error( "Failed to find audio track: %s" % video)

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
