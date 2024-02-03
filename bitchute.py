#!/usr/bin/python3

# basic, standard libs
import logging, requests

# Needed to bypass CloudFlare
import cloudscraper

# web grabbing and parsing libs
from bs4 import BeautifulSoup

from feedgen.feed import FeedGenerator

from tornado import web

## setup timezone object, needed for pubdate
import datetime, pytz
from pytz import timezone
tz = timezone('US/Central')

__version__ = 'v2024.02.02.1'

class ChannelHandler(web.RequestHandler):
    def head(self, channel):
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    def get(self, channel):
        # make/build RSS feed
        url = "https://bitchute.com/channel/%s/?showall=1" % channel
        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( channel )
        self.write( feed )
        self.finish()

    def get_html( self, channel ):
        url = "https://bitchute.com/channel/%s/?showall=1" % channel
        logging.info("Requesting Bitchute URL: %s" % url)

        # CloudFlare now blocking requests
        heads = { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' }

        logging.info("Getting url: %s" % url)
        scraper = cloudscraper.create_scraper(browser="chrome")
        r = scraper.get( url )
        #r = httpx.get( url, headers=heads, follow_redirects=True )
        #r = requests.get( url, headers=heads )

        if r.status_code == 403:
            logging.error("CloudFlare blocked: %s" % url)
            self.set_status(403)
        return r.text

    def generate_rss( self, channel ):
        logging.info("Bitchute URL: %s" % channel)
        html = self.get_html( channel )
        if self.get_status() == 403:
            return "Request responded: 403 (likely a CloudFlare block)\r\n\r\n\r\n" + BeautifulSoup(html, 'lxml').get_text().replace('\n\n\n\n\n\n\n', '\n')

        bs = BeautifulSoup( html, "lxml" )
        feed = FeedGenerator()

        bs = bs.find("div", "container-fluid")
        feed.load_extension('podcast')

        ## gather channel information
        channelbanner = bs.find("div", "channel-banner")
        if channelbanner:
            feed.title( channelbanner.find("p", "name").text )
        else:
            logging.error("Failed to pull channel title. Using provided channel instead")
            feed.title( channel )

        channelimage = bs.find("div", "image-container")
        if channelimage:
            feed.image( channelimage.find("img")['data-src'] )
        else:
            logging.error("Failed to pull channel image.")

        channeluser = bs.find("p", "name")
        if channeluser:
            feed.description( "Bitchute user name: %s" % channeluser.text )
        else:
            logging.error("Failed to pull channel user name. Using provided channel instead")
            feed.description( "Bitchute user name: %s" % channel )

        channelid = bs.find("a", "spa")
        if channelid:
            feed.id( channelid['href'] )
            feed.link( {'href': channelid['href'], 'rel': 'self'} )
        else:
            logging.error("Failed to pull channel ID. Using provided channel instead")
            feed.id( channel )

        feed.language('en')

        ## loop through videos build feed item dict
        videos = bs.find_all("div", "channel-videos-container")
        if videos:
            vidcount = len( videos )
            itemcounter = 0
            for video in videos:
                item = feed.add_entry()

                videotitle = video.find("div", "channel-videos-title")
                if videotitle:
                    item.title( videotitle.text )
                else:
                    logging.error("Failed to pull video title")
                    item.title( channel )

                videodescription = video.find("div", "channel-videos-text")
                if videodescription:
                    item.description( videodescription.text )
                else:
                    logging.error("Failed to pull video description")
                    item.description( channel )

                videoimage = video.find("div", "channel-videos-image")
                if videoimage:
                    item.podcast.itunes_image( videoimage.find("img")['data-src'] )
                    item.image = videoimage
                else:
                    logging.error("Failed to pull video image")

                videolink = video.find("div", "channel-videos-title")
                if videolink:
                    link = videolink.find("a", "spa")['href']
                    link = f'http://{self.request.host}/bitchute{link}'
                else:
                    logging.error("Failed to pull video link")
                    link = None

                videotitle = video.find("div", "channel-videos-title")
                if videotitle:
                    title = videotitle.text
                else:
                    logging.error("Failed to pull video title")
                    title = None

                item.link(
                    href = link,
                    title = title
                )

                videodate = video.find("div", "channel-videos-details")
                if videodate:
                    viddate = " ".join([videodate.text.strip(), str(itemcounter)])
                    date = datetime.datetime.strptime(  viddate, "%b %d, %Y %M" ).astimezone( tz )
                    item.pubDate( date )
                else:
                    logging.error("Failed to pull video date")

                item.enclosure(
                    url = f'http://{self.request.host}/bitchute{link}',
                    type = "video/mp4"
                )

                videoduration = video.find("span", "video-duration")
                if videoduration:
                    item.podcast.itunes_duration( videoduration.text )
                else:
                    logging.error("Failed to pull video duration")
                itemcounter += 1

        return feed.rss_str( pretty=True )

def get_bitchute_url(video_id):
    url = f"https://bitchute.com/video/{video_id}"
    logging.info("Requesting Bitchute URL: %s" % url)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    video_source = soup.find("video").find("source")['src']
    return video_source

class VideoHandler(web.RequestHandler):
    def get(self, video):
        logging.info("Bitchute Video: %s" % video)
        self.redirect( get_bitchute_url(video) )
