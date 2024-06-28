"""
This handles converting Bitchute channels into podcast-friendly RSS feeds.
"""

#!/usr/bin/python3

# basic, standard libs
import datetime
import logging
import requests

# Needed to bypass CloudFlare bot blocks
#import cloudscraper

#from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from tornado import web

## setup timezone object, needed for pubdate
# from pytz import timezone
# tz = timezone('UTC')
bitchuteurl = 'https://api.bitchute.com'

__version__ = 'v2024.06.28.2'

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
        url = f"{bitchuteurl}/channel/{channel}"
        logging.info( "Requesting Bitchute URL: %s" % url )


        logging.info( "Getting url: %s" % url )
        scraper = cloudscraper.create_scraper(browser="chrome")

        r = scraper.get( url )

        if r.status_code == 403:
            logging.error( "CloudFlare blocked: %s" % url)
            self.set_status(403)
        else:
            logging.info( "Cloudscraper returned status code: %s" % r.status_code )
            self.set_status(r.status_code)
        return r.text

    def add_channel_info( self, feed, channel ):
        """
        Fetches the channel information from the Bitchute API.

        Args:
            channel (str): The channel identifier.

        Returns:
            dict: The channel information.
        """
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://www.bitchute.com',
            'priority': 'u=1, i',
            'referer': 'https://www.bitchute.com/',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        }

        json_data = {
            'channel_id': channel,
        }

        response = requests.post('https://api.bitchute.com/api/beta/channel',
                                    headers=headers,
                                    json=json_data,
                                    timeout=10)
        channel = response.json()

        feed.title( channel['channel_name'] )
        feed.description( channel['description'] )
        feed.id( channel['channel_id'] )
        feed.language( 'en' )
        feed.image( channel['thumbnail_url'] )
        feed.link(
            href = f'https://www.bitchute.com/{channel['channel_url']}',
            rel = 'self'
        )

        return feed

    def add_videos( self, feed, channel ):
        """
        Fetches the list of video identifiers from the Bitchute API.

        Args:
            channel (str): The channel identifier.

        Returns:
            list: The list of video identifiers.
        """
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://www.bitchute.com',
            'priority': 'u=1, i',
            'referer': 'https://www.bitchute.com/',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        }

        json_data = {
            "channel_id": channel,
            'offset': 0,
            'limit': 20,
        }

        videos = requests.post("https://api.bitchute.com/api/beta/channel/videos", headers=headers, json=json_data, timeout=10)
        if videos.status_code == 200:
            videos = videos.json()

            for video in videos['videos']:
                item = feed.add_entry()
                item.title( video['video_name'] )
                item.description( video['description'] )
                item.pubDate( video['date_published'] )
                item.podcast.itunes_duration( video['duration'] )
                item.link(
                    href = f"https://www.bitchute.com{video['video_url']}",
                    title = video['video_name']
                )
                item.enclosure(
                    url = f"https://www.bitchute.com{video['video_url']}",
                    length = video['duration'],
                    type = 'video/mp4'
                )
        else:
            logging.error( "Bitchute returned status code: %s" % videos.status_code )
            self.set_status(videos.status_code)

        return feed

    def generate_rss( self, channel ):
        """
        Generates an RSS feed for the provided Bitchute channel.

        Args:
            channel (str): The Bitchute channel URL.

        Returns:
            str: The RSS feed in string format.
        """
        logging.info( "Bitchute URL: %s" % channel )

        feed = FeedGenerator()
        feed.load_extension('podcast')

        self.add_channel_info( feed, channel )
        self.add_videos( feed, channel )

        return feed.rss_str(pretty=False)

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
