"""
This handles converting Bitchute channels into podcast-friendly RSS feeds.
"""

#!/usr/bin/python3

# basic, standard libs
import datetime
import logging
import requests

# Needed to bypass CloudFlare bot blocks
import cloudscraper

from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from tornado import web

## setup timezone object, needed for pubdate
import pytz
from pytz import timezone
tz = timezone('UTC')
bitchuteurl = 'https://old.bitchute.com'

__version__ = 'v2024.06.28.1'

class ChannelHandler(web.RequestHandler):
    """
    Set the response headers for the specified channel.

    :param channel: The channel for which the headers are being set.
    :return: None
    """

    def head(self):
        """
        Set the headers for the HTTP response.

        Args:
            None

        Returns:
            None
        """
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    def get(self, channel):
        """
        A method to get the HTML and generate an RSS feed for a specified channel.

        Parameters:
            channel (str): The name of the Bitchute channel for which to generate the RSS feed.

        Returns:
            None
        """
        # make/build RSS feed
        self.set_header('Content-type', 'application/rss+xml')
        feed = self.generate_rss( channel )
        self.write( feed )
        self.finish()

    def get_html( self, channel ):
        """
        Fetches the HTML content of the given Bitchute channel.

        Args:
            channel (str): The channel identifier.

        Returns:
            str: The HTML content of the channel's page.
        """
        url = f"{bitchuteurl}/channel/{channel}/?showall=1"
        logging.info( "Requesting Bitchute URL: %s" % url )


        logging.info( "Getting url: %s" % url )
        scraper = cloudscraper.create_scraper(browser="chrome")

        r = scraper.get( url )

        if r.status_code == 403:
            logging.error( "CloudFlare blocked: %s" % url)
            self.set_status(403)
        else:
            logging.info( "Cloudscraper returned status code: %s" % r.status_code )
        return r.text

    def generate_rss( self, channel ):
        """
        Generates an RSS feed for the provided Bitchute channel.

        Args:
            channel (str): The Bitchute channel URL.

        Returns:
            str: The RSS feed in string format.
        """
        logging.info( "Bitchute URL: %s" % channel )
        html = self.get_html( channel )
        if self.get_status() == 403:
            return "Request responded: 403 (likely a CloudFlare block)\r\n\r\n\r\n" + html.get_text().replace('\n\n\n\n\n\n\n', '\n')

        soup = BeautifulSoup( html, "lxml" )
        feed = FeedGenerator()

        soup = soup.find("div", "container-fluid")
        feed.load_extension('podcast')

        ## gather channel information
        element = soup.find("div", "channel-banner")
        if element:
            feed.title( element.find("p", "name").text )
        else:
            logging.error("Failed to pull channel title. Using provided channel instead")
            feed.title( channel )

        element = soup.find("div", "image-container")
        if element:
            feed.image( element.find("img")['data-src'] )
        else:
            logging.error("Failed to pull channel image.")

        element = soup.find("p", "name")
        if element:
            feed.description( f"Bitchute user name: {element.text}" )
        else:
            logging.error("Failed to pull channel user name. Using provided channel instead")
            feed.description( f"Bitchute user name: {channel}" )

        element = soup.find("a", "spa")
        if element:
            feed.id( element['href'] )
            feed.link( {'href': element['href'], 'rel': 'self'} )
        else:
            logging.error("Failed to pull channel ID. Using provided channel instead")
            feed.id( channel )

        feed.language('en')

        ## loop through videos build feed item dict
        videos = soup.find_all("div", "channel-videos-container")
        if videos:
            itemcounter = 0
            for video in videos:
                item = feed.add_entry()

                element = video.find("div", "channel-videos-title")
                if element:
                    item.title( element.text )
                else:
                    logging.error("Failed to pull video title")
                    item.title( channel )

                element = video.find("div", "channel-videos-text")
                if element:
                    item.description( element.text )
                else:
                    logging.error("Failed to pull video description")
                    item.description( channel )

                element = video.find("div", "channel-videos-image")
                if element:
                    item.podcast.itunes_image( element.find("img")['data-src'] )
                    item.image = element.find("img")['data-src']
                else:
                    logging.error("Failed to pull video image")

                element = video.find("div", "channel-videos-title")
                if element:
                    link = element.find("a", "spa")['href']
                    link = f'http://{self.request.host}/bitchute{link}'
                else:
                    logging.error("Failed to pull video link")
                    link = None

                element = video.find("div", "channel-videos-title")
                if element:
                    title = element.text
                else:
                    logging.error("Failed to pull video title")
                    title = None

                item.link(
                    href = link,
                    title = title
                )

                element = video.find("div", "channel-videos-details")
                if element:
                    viddate = " ".join([element.text.strip(), str(itemcounter)])
                    date = datetime.datetime.strptime(  viddate, "%b %d, %Y %M" ).astimezone( tz )
                    item.pubDate( date )
                else:
                    logging.error("Failed to pull video date")

                item.enclosure(
                    url = link,
                    type = "video/mp4"
                )

                element = video.find("span", "video-duration")
                if element:
                    item.podcast.itunes_duration( element.text )
                else:
                    logging.error("Failed to pull video duration")
                itemcounter += 1

        return feed.rss_str( pretty=True )

def get_bitchute_url(video_id):
    """
    Function to retrieve the Bitchute video URL for a given video ID.

    Parameters:
    - video_id: str, the ID of the video

    Returns:
    - str, the URL of the video source
    """
    url = f"{bitchuteurl}/video/{video_id}"
    logging.info( "Requesting Bitchute URL: %s" % url )
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    video_element = soup.find("video").find("source")
    video_url = video_element['src']
    return video_url

class VideoHandler(web.RequestHandler):
    def get(self, video):
        """
        Get the Bitchute video and redirect to the Bitchute URL.

        Args:
            video: The Bitchute video to retrieve.

        Returns:
            None
        """
        logging.info("Bitchute Video: %s" % video)
        self.redirect( get_bitchute_url(video) )
