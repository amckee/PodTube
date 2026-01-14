"""
This file contains the implementation of handlers and functions related to interacting with YouTube
content. It includes classes such as VideoHandler, AudioHandler, ClearCacheHandler, and UserHandler,
which handle different types of requests related to YouTube content.
"""
from configparser import ConfigParser

import datetime
import logging
import os
import time
import glob
from pathlib import Path
from feedgen.feed import FeedGenerator
import requests
import psutil
from pytubefix import YouTube, exceptions
from tornado import gen, httputil, ioloop, iostream, process, web
from tornado.locks import Semaphore
import utils
import gc

key = None
cleanup_period = None
convert_video_period = None
audio_expiration_time = None
start_cleanup_size_threshold = None
stop_cleanup_size_threshold = None
autoload_newest_audio = None

video_links = {}
playlist_feed = {}
channel_feed = {}
channel_name_to_id = {}

__version__ = 'v2024.11.11.1'

conversion_queue = {}
converting_lock = Semaphore(2)

def get_env_or_config_option(conf: ConfigParser,
                                 env_name: str,
                                 config_name: str,
                                 default_value = None):
    """
    Get the value of a configuration option from the given ConfigParser object, either
    from the environment variables or from the configuration file.

    Args:
        conf (ConfigParser): The ConfigParser object containing the configuration options.
        env_name (str): The name of the environment variable to check for the configuration option.
        config_name (str): The name of the configuration option in the configuration file.
        default_value: The default value to return if the configuration option is not found.

    Returns:
        The value of the configuration option, or the default value if the option is not found.
    """
    return utils.get_env_or_config_option(conf, env_name,
                                          config_name, "youtube",
                                          default_value=default_value)

def init(conf: ConfigParser):
    """
    Initializes the configuration settings for the system.

    Args:
        conf (ConfigParser): The configuration parser object.

    Returns:
        None
    """
    global key, cleanup_period, convert_video_period, audio_expiration_time, start_cleanup_size_threshold, stop_cleanup_size_threshold
    key                          = str(get_env_or_config_option(conf, "YT_API_KEY"                     , "api_key"                     , default_value=None))
    cleanup_period               = int(get_env_or_config_option(conf, "YT_CLEANUP_PERIOD"              , "cleanup_period"              , default_value=600000)) # 10 minutes
    convert_video_period         = int(get_env_or_config_option(conf, "YT_CONVERT_VIDEO_PERIOD"        , "convert_video_period"        , default_value=1000)) # 1 second
    audio_expiration_time        = int(get_env_or_config_option(conf, "YT_AUDIO_EXPIRATION_TIME"       , "audio_expiration_time"       , default_value=259200000)) # 3 days
    start_cleanup_size_threshold = int(get_env_or_config_option(conf, "YT_START_CLEANUP_SIZE_THRESHOLD", "start_cleanup_size_threshold", default_value=536870912)) # 0.5GiB
    stop_cleanup_size_threshold  = int(get_env_or_config_option(conf, "YT_STOP_CLEANUP_SIZE_THRESHOLD" , "stop_cleanup_size_threshold" , default_value=16106127360)) # 15GiB
    poToken                      = str(get_env_or_config_option(conf, "YT_TOKEN"                    , "po_token"                    , default_value=None))
    autoload_newest_audio        = get_env_or_config_option(conf, "YT_AUTOLOAD_NEWEST_AUDIO"       , "autoload_newest_audio"       , default_value=True)
    autoload_newest_audio = utils.convert_to_bool(autoload_newest_audio)

    ioloop.PeriodicCallback(
        callback=cleanup,
        callback_time=cleanup_period
    ).start()
    ioloop.PeriodicCallback(
        callback=convert_videos,
        callback_time=convert_video_period
    ).start()

def set_key( new_key=None ):
    """
    Sets the value of the global variable `key` to the provided `new_key`.

    :param new_key: A string representing the new value for the `key` variable.
    :type new_key: str

    :return: None
    """
    global key
    key = new_key

def cleanup():
    """
    Clean up expired video links, playlist feeds, channel feeds, and channel name map.
    Delete audio files older than a certain time or when the disk space is low.
    Logs the items cleaned from each category.
    """
    # Globals
    global video_links, playlist_feed, channel_name_to_id, channel_feed, audio_expiration_time, start_cleanup_size_threshold, stop_cleanup_size_threshold
    current_time = datetime.datetime.now()
    # Video Links
    video_links_length = len(video_links)
    video_links = {
        video:
            info
            for video, info in video_links.items()
            if info['expire'] > current_time
    }
    video_links_length -= len(video_links)
    if video_links_length:
        logging.info( 'YouTube: Cleaned %s items from video list', video_links_length )
    # Playlist Feeds
    playlist_feed_length = len(playlist_feed)
    playlist_feed = {
        playlist:
            info
            for playlist, info in playlist_feed.items()
            if info['expire'] > current_time
    }
    playlist_feed_length -= len(playlist_feed)
    if playlist_feed_length:
        logging.info(
            'YouTube: Cleaned %s items from playlist feeds',
            playlist_feed_length
        )
    # Channel Feeds
    channel_feed_length = len(channel_feed)
    channel_feed = {
        channel:
            info
            for channel, info in channel_feed.items()
            if info['expire'] > current_time
    }
    channel_feed_length -= len(channel_feed)
    if channel_feed_length:
        logging.info(
            'YouTube: Cleaned %s items from channel feeds',
            channel_feed_length
        )
    # Channel Feeds
    channel_name_to_id_length = len(channel_name_to_id)
    channel_name_to_id = {
        channel:
            info
            for channel, info in channel_name_to_id.items()
            if info['expire'] > current_time
    }
    channel_name_to_id_length -= len(channel_name_to_id)
    if channel_name_to_id_length:
        logging.info(
            'YouTube: Cleaned %s items from channel name map',
            channel_name_to_id_length
        )
    # Space Check
    expired_time = time.time() - (audio_expiration_time / 1000)
    size_clean = False
    for f in sorted(glob.glob('./audio/*mp3'), key=lambda a_file: os.path.getctime(a_file)):
        size = psutil.disk_usage('./audio')
        ctime = os.path.getctime(f)
        size_clean = size_clean or size.free < start_cleanup_size_threshold
        time_clean = ctime <= expired_time
        if time_clean or size_clean:
            try:
                os.remove(f)
                logging.info( 'YouTube: Deleted %s', f )
            except Exception as ex:
                logging.error( 'YouTube: Error remove file %s: %s', f, ex )
            if not time_clean and size_clean and size.free > stop_cleanup_size_threshold:
                break
        else:
            break

@gen.coroutine
def convert_videos():
    """
    Asynchronous function to convert videos.
    This function checks the conversion queue for pending videos, selects the next video to convert,
    and then initiates the conversion process.
    If an error occurs during the conversion, it handles the error and cleans up any temp files.
    """
    global conversion_queue
    global converting_lock
    if len(conversion_queue) == 0:
        return
    try:
        remaining = [
            key
            for key in conversion_queue.keys()
            if not conversion_queue[key]['status']
        ]
        video = sorted(
            remaining,
            key=lambda v: conversion_queue[v]['added']
        )[0]
        conversion_queue[video]['status'] = True
    except Exception:
        return
    with (yield converting_lock.acquire()):
        logging.info( 'YouTube: Converting: %s', video )
        audio_file = './audio/{}.mp3'.format(video)
        try:
            yutubeUrl = get_youtube_url(video)
            ffmpeg_process = process.Subprocess([
                'ffmpeg',
                '-loglevel', 'panic',
                '-y',
                '-i', yutubeUrl,
                '-f', 'mp3', audio_file + '.temp'
            ])
            yield ffmpeg_process.wait_for_exit()
            os.rename(audio_file + '.temp', audio_file)
            logging.info( 'YouTube: Successfully converted: %s', video )
        except Exception as ex:
            logging.error( 'YouTube: Error converting file: %s', ex )
            if isinstance(ex, (exceptions.LiveStreamError, exceptions.VideoUnavailable)):
                if video not in video_links:
                    video_links[video] = {
                        'url': None,
                        'expire': datetime.datetime.now() + datetime.timedelta(hours=6)
                    }
                video_links[video]['unavailable'] = True
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except Exception as ex2:
                logging.error( 'YouTube: Error remove broken file: %s', ex2 )
        finally:
            del conversion_queue[video]
            try:
                if os.path.exists(audio_file + '.temp'):
                    os.remove(audio_file + '.temp')
            except Exception as ex2:
                logging.error( 'YouTube: Error remove temp file: %s', ex2 )

def get_youtube_url(video):
    """
    Function to get the YouTube URL for a given video.

    Args:
    - video: The video ID for which the URL is needed.

    Returns:
    - The YouTube URL for the given video.
    """
    if video in video_links and video_links[video]['expire'] > datetime.datetime.now():
        return video_links[video]['url']
    yturl = f"https://www.youtube.com/watch?v={video}"
    logging.debug( 'YouTube: Full URL: %s', yturl )

    yt = None

    try:
        yt = YouTube(yturl, use_oauth=True, allow_oauth_cache=True)
    except Exception as e:
        logging.error( 'YouTube: Error returned by Youtube: %s', e )
        return e

    try:
        logging.debug( 'YouTube: Stream count: %s', len(yt.streams) )
        try:
            vid = yt.streams.get_highest_resolution().url
            logging.debug( 'YouTube: Highest resultion URL: %s', vid )
        except Exception as e:
            logging.error( 'YouTube: Failed to get video URL: %s', e )
            return e
    except Exception as e:
        logging.error( 'YouTube: Failed to get stream count: %s', e )
        return e

    parts = {
        part.split('=')[0]: part.split('=')[1]
        for part in vid.split('?')[-1].split('&')
    }
    link = {
        'url': vid,
        'expire': datetime.datetime.fromtimestamp(int(parts['expire']))
    }

    yt = None
    del yt

    video_links[video] = link
    return link['url']

class ChannelHandler(web.RequestHandler):
    """
    Handles HTTP requests for YouTube channel pages and video listings.
    
    This request handler processes channel URLs, extracts video information,
    and renders channel pages with video listings. It supports both video
    and audio handler paths for different media formats.
    """
    def initialize(self, video_handler_path: str, audio_handler_path: str):
        """
        Initializes the object with the given video and audio handler paths.

        :param video_handler_path: A string representing the path to the video handler.
        :param audio_handler_path: A string representing the path to the audio handler.
        """
        self.video_handler_path = video_handler_path
        self.audio_handler_path = audio_handler_path

    @gen.coroutine
    def head(self):
        """
        Coroutine function to set header values for the specified channel.

        Args:
            self: The instance of the class.
            channel: The channel for which the header values are being set.

        Returns:
            None
        """
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    @gen.coroutine
    def get(self, channel):
        """
        A coroutine function that retrieves videos from a specified YouTube channel and generates an RSS feed.
        Parameters:
            - self: the class instance
            - channel: the channel from which to retrieve videos
        Return types:
            - None
        """
        global key
        maxPages = self.get_argument('max', None)
        if maxPages:
            logging.info( 'YouTube: Will grab videos from a maximum of %s pages', maxPages )

        channel = channel.split('/')
        if len(channel) < 2:
            channel.append('video')
        channel_name = ['/'.join(channel)]
        self.set_header('Content-type', 'application/rss+xml')
        if channel_name[0] in channel_feed and channel_feed[channel_name[0]]['expire'] > datetime.datetime.now():
            self.write(channel_feed[channel_name[0]]['feed'])
            self.finish()
            return
        fg = None
        video = None
        calls = 0
        payload = {
            'part': 'snippet,contentDetails',
            'maxResults': 1,
            'fields': 'items',
            'order': 'date',
            'id': channel[0],
            'key': key
        }
        request = requests.get(
             'https://www.googleapis.com/youtube/v3/channels',
             params=payload,
             timeout=10
        )
        calls += 1
        if request.status_code != 200:
            payload = {
                'part': 'snippet,contentDetails',
                'maxResults': 1,
                'fields': 'items',
                'order': 'date',
                'forUsername': channel[0],
                'key': key
            }
            request = requests.get(
                'https://www.googleapis.com/youtube/v3/channels',
                params=payload,
                timeout=10
            )
            calls += 1
        if request.status_code == 200:
            logging.debug( 'YouTube: Downloaded Channel Information' )
        else:
            logging.error( 'YouTube: Error Downloading Channel: %s', request.reason )
            self.send_error(reason='Error Downloading Channel')
            return
        response = request.json()
        channel_data = response['items'][0]
        if channel[0] != channel_data['id']:
            channel[0] = channel_data['id']
            channel_name.append('/'.join(channel))
        #get upload playlist
        channel_upload_list = channel_data['contentDetails']['relatedPlaylists']['uploads']
        channel_data = channel_data['snippet']

        fg = FeedGenerator()
        fg.load_extension('podcast')
        fg.generator(
            'PodTube (python-feedgen)',
            __version__,
            'https://github.com/amckee/PodTube'
        )
        if 'title' not in channel_data:
            logging.info( 'YouTube: Channel title not found' )
            channel_data['title'] = channel[0]
        logging.info(
            'YouTube: Channel: %s (%s)',
            channel[0],
            channel_data['title']
        )
        icon = max(
            channel_data['thumbnails'],
            key=lambda x: channel_data['thumbnails'][x]['width']
        )
        fg.title(channel_data['title'])
        fg.id(f'{self.request.protocol}://{self.request.host}{self.request.uri}')
        fg.description(channel_data['description'] or ' ')
        fg.author(
            name='Podtube',
            email='armware+podtube@gmail.com',
            uri='https://github.com/amckee/PodTube')
        fg.podcast.itunes_author(channel_data['title'])
        fg.image(channel_data['thumbnails'][icon]['url'])
        fg.link(
            href=f'https://www.youtube.com/channel/{channel[0]}',
            rel='self'
        )
        fg.language('en-US')
        fg.podcast.itunes_image(channel_data['thumbnails'][icon]['url'])
        fg.podcast.itunes_explicit('no')
        fg.podcast.itunes_owner(
            name='Podtube',
            email='armware+podtube@gmail.com'
        )
        fg.podcast.itunes_summary(channel_data['description'] or ' ')
        fg.podcast.itunes_category(cat='Technology')
        fg.updated(str(datetime.datetime.utcnow()) + 'Z')

        response = {'nextPageToken': ''}
        pageCount = itemCount = 0
        while 'nextPageToken' in response.keys():
            pageCount += 1
            if maxPages and (pageCount > int(maxPages)):
                logging.info( 'YouTube: Reached maximum number of pages. Stopping here.' )
                break
            next_page = response['nextPageToken']
            payload = {
                'part': 'snippet,contentDetails',
                'maxResults': 50,
                'playlistId': channel_upload_list,
                'key': key,
                'pageToken': next_page
            }
            request = requests.get(
                'https://www.googleapis.com/youtube/v3/playlistItems',
                params=payload,
                timeout=10
            )
            calls += 1
            response = request.json()
            if request.status_code == 200:
                logging.debug( 'YouTube: Downloaded Channel Information' )
            else:
                logging.error( 'YouTube: Error Downloading Channel: %s', request.reason )
                self.send_error(reason='Error Downloading Channel')
                return
            for item in response['items']:
                snippet = item['snippet']
                if 'private' in snippet['title'].lower():
                    continue
                current_video = item['contentDetails']['videoId']

                try:
                    chan=snippet['channelTitle']
                except KeyError:
                    snippet['channelTitle'] = snippet['channelId']
                    logging.error( 'YouTube: Channel title not found' )

                logging.debug(
                    'YouTube: ChannelVideo: %s (%s)',
                    current_video,
                    snippet['title']
                )
                fe = fg.add_entry()
                itemCount += 1
                fe.title(snippet['title'])
                fe.id(current_video)
                icon = max(
                    snippet['thumbnails'],
                    key=lambda x: snippet['thumbnails'][x]['width'])
                fe.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
                fe.updated(snippet['publishedAt'])
                if channel[1] == 'video':
                    fe.enclosure(
                        url=f'{self.request.protocol}://{self.request.host}{self.video_handler_path}{current_video}',
                        type="video/mp4"
                    )
                elif channel[1] == 'audio':
                    fe.enclosure(
                        url=f'{self.request.protocol}://{self.request.host}{self.audio_handler_path}{current_video}',
                        type="audio/mpeg"
                    )
                fe.author(name=snippet['channelTitle'])
                fe.podcast.itunes_author(snippet['channelTitle'])
                fe.pubDate(snippet['publishedAt'])
                fe.link(
                    href=f'https://www.youtube.com/watch?v={current_video}',
                    title=snippet['title']
                )
                fe.podcast.itunes_summary(snippet['description'])
                fe.description(snippet['description'])
                if not video or video['expire'] < fe.pubDate():
                    video = {'video': fe.id(), 'expire': fe.pubDate()}
        feed = {
            'feed': fg.rss_str(),
            'expire': datetime.datetime.now() + datetime.timedelta(hours=calls)
        }
        for chan in channel_name:
            channel_feed[chan] = feed

        logging.info( "Got %s videos from %s pages" % (itemCount, pageCount) )

        self.write(feed['feed'])
        self.finish()

        global autoload_newest_audio
        if not autoload_newest_audio:
            return
        video = video['video']
        mp3_file = 'audio/{}.mp3'.format(video)
        if channel[1] == 'audio' and not os.path.exists(mp3_file) and video not in conversion_queue.keys():
            conversion_queue[video] = {
                'status': False,
                'added': datetime.datetime.now()
            }

    def data_received(self, chunk):
        pass

class PlaylistHandler(web.RequestHandler):
    """
    Handles HTTP requests for YouTube playlist processing.
    
    This request handler manages playlist downloads and conversions,
    providing endpoints to process YouTube playlists and convert
    their content to audio or video formats.
    """

    def initialize(self, video_handler_path: str, audio_handler_path: str):
        """
        Initialize the class with the provided video and audio handler paths.

        Args:
            video_handler_path (str): The path to the video handler.
            audio_handler_path (str): The path to the audio handler.
        """
        self.video_handler_path = video_handler_path
        self.audio_handler_path = audio_handler_path

    def data_received(self, chunk):
        pass

    @gen.coroutine
    def head(self, playlist):
        """
        A coroutine function that sets the header for the given playlist.

        Args:
            self: The instance of the class.
            playlist: The playlist for which the header is being set.

        Returns:
            None
        """
        self.set_header('Content-type', 'application/rss+xml')
        self.set_header('Accept-Ranges', 'bytes')

    @gen.coroutine
    def get(self, playlist):
        """
        A coroutine function to fetch a playlist and generate an RSS feed.
        """
        global key
        playlist = playlist.split('/')
        if len(playlist) < 2:
            playlist.append('video')
        playlist_name = '/'.join(playlist)
        self.set_header('Content-type', 'application/rss+xml')
        if playlist_name in playlist_feed and playlist_feed[playlist_name]['expire'] > datetime.datetime.now():
            self.write(playlist_feed[playlist_name]['feed'])
            self.finish()
            return
        calls = 0
        payload = {
            'part': 'snippet',
            'id': playlist[0],
            'key': key
        }
        request = requests.get(
            'https://www.googleapis.com/youtube/v3/playlists',
            params=payload,
            timeout=10
        )
        calls += 1
        if request.status_code == 200:
            logging.debug( 'YouTube: Downloaded Playlist Information' )
        else:
            logging.error( 'YouTube: Error Downloading Playlist: %s', request.reason )
            self.send_error(reason='Error Downloading Playlist')
            return
        response = request.json()
        fg = FeedGenerator()
        fg.load_extension('podcast')
        fg.generator(
            'PodTube (python-feedgen)',
            __version__,
            'https://github.com/amckee/PodTube'
        )
        snippet = response['items'][0]['snippet']
        icon = max(
            snippet['thumbnails'],
            key=lambda x: snippet['thumbnails'][x]['width']
        )
        logging.info(
            'YouTube: Playlist: %s (%s)',
            playlist[0],
            snippet['title']
        )
        fg.title(snippet['title'])
        fg.id(f'{self.request.protocol}://{self.request.host}{self.request.uri}')
        fg.description(snippet['description'] or ' ')
        fg.author(
            name='Podtube',
            email='armware+podtube@gmail.com',
            uri='https://github.com/amckee/PodTube'
        )
        fg.podcast.itunes_author(snippet['channelTitle'])
        fg.image(snippet['thumbnails'][icon]['url'])
        fg.link(
            href=f'https://www.youtube.com/playlist/?list={playlist}',
            rel='self'
        )
        fg.language('en-US')
        fg.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
        fg.podcast.itunes_explicit('no')
        fg.podcast.itunes_owner(
            name='Podtube',
            email='armware+podtube@gmail.com'
        )
        fg.podcast.itunes_summary(snippet['description'])
        fg.podcast.itunes_category(cat='Technology')
        fg.updated(str(datetime.datetime.utcnow()) + 'Z')
        video = None
        response = {'nextPageToken': ''}
        while 'nextPageToken' in response.keys():
            payload = {
                'part': 'snippet',
                'maxResults': 50,
                'playlistId': playlist[0],
                'key': key,
                'pageToken': response['nextPageToken']
            }
            request = requests.get(
                'https://www.googleapis.com/youtube/v3/playlistItems',
                params=payload,
                timeout=10
            )
            calls += 1
            response = request.json()
            if request.status_code == 200:
                logging.debug( 'YouTube: Downloaded Playlist Information' )
            else:
                logging.error( 'YouTube: Error Downloading Playlist: %s', request.reason )
                self.send_error(reason='Error Downloading Playlist Items')
                return
            for item in response['items']:
                snippet = item['snippet']
                current_video = snippet['resourceId']['videoId']
                if 'Private' in snippet['title']:
                    continue
                logging.debug(
                    'YouTube: PlaylistVideo: %s (%s)',
                    current_video,
                    snippet['title']
                )
                fe = fg.add_entry()
                fe.title(snippet['title'])
                fe.id(current_video)
                icon = max(
                    snippet['thumbnails'],
                    key=lambda x: snippet['thumbnails'][x]['width']
                )
                fe.podcast.itunes_image(snippet['thumbnails'][icon]['url'])
                fe.updated(snippet['publishedAt'])
                final_url = None
                if playlist[1] == 'video':
                    final_url = f'{self.request.protocol}://{self.request.host}{self.video_handler_path}{current_video}'
                    fe.enclosure(
                        url=final_url,
                        type="video/mp4"
                    )
                elif playlist[1] == 'audio':
                    final_url = f'{self.request.protocol}://{self.request.host}{self.audio_handler_path}{current_video}'
                    fe.enclosure(
                        url=final_url,
                        type="audio/mpeg"
                    )
                logging.debug( 'YouTube: Final URL created for enclosure: %s', final_url )
                fe.author(name=snippet['channelTitle'])
                fe.podcast.itunes_author(snippet['channelTitle'])
                fe.pubDate(snippet['publishedAt'])
                fe.link(
                    href=f'https://www.youtube.com/watch?v={current_video}',
                    title=snippet['title']
                )
                fe.podcast.itunes_summary(snippet['description'])
                fe.description(snippet['description'])
                if not video or video['expire'] < fe.pubDate():
                    video = {'video': fe.id(), 'expire': fe.pubDate()}
        feed = {
            'feed': fg.rss_str(),
            'expire': datetime.datetime.now() + datetime.timedelta(hours=calls)
        }
        playlist_feed[playlist_name] = feed
        self.write(feed['feed'])
        self.finish()
        global autoload_newest_audio
        if not autoload_newest_audio:
            return
        video = video['video']
        mp3_file = 'audio/{}.mp3'.format(video)
        if playlist[1] == 'audio' and not os.path.exists(mp3_file) and video not in conversion_queue.keys():
            conversion_queue[video] = {
                'status': False,
                'added': datetime.datetime.now()
            }

class VideoHandler(web.RequestHandler):
    """
    Handles HTTP requests for YouTube video processing.
    
    This request handler manages video downloads and conversions,
    providing endpoints to process YouTube videos and convert
    their content to audio or video formats.
    """

    def get(self, video):
        """
        Get the video URL from YouTube using the provided video ID,
        and handle the redirection or error response accordingly.

        Parameters:
            video (str): The ID of the video to retrieve from YouTube.

        Returns:
            None
        """
        logging.info( 'YouTube: Getting Video: %s', video )

        # This can cause OOMs on lower spec'd servers.
        # As such, run a garbage collection before
        # running this function.
        gc.collect()

        yt_url = get_youtube_url( video )
        if isinstance(yt_url, str):
            logging.debug( 'YouTube: Got video URL: %s', yt_url )
            self.redirect( yt_url )
        elif yt_url is None:
            error_msg = f"Video not found: {video}<br/>Check with <a href=https://github.com/JuanBindez/pytubefix/issues>PytubeFix project</a> for possible fixes or updates"
            self.write(error_msg)
        else:
            logging.error( "Unknown failure to get video." )
            error_msg = f"Error returned by Youtube: {yt_url}<br/>https://www.youtube.com/watch?v={video}"
            self.write(error_msg)
            # logging.error( "Unknown failure to get video. Falling back to yt-dlp method" )
            # try:
            #     yt_url = self.ytdlp_get_url( video )
            # except Exception as e:
            #     logging.error( 'YouTube: Error getting video URL: %s', e )
            # if isinstance(yt_url, str):
            #     logging.info("YouTube: yt-dlp ftw!")
            #     self.redirect( yt_url )
            # else:
            #     logging.error( 'YouTube: Error returned by yt-dlp: %s', yt_url )
            #     # self.write( f"Error returned by Youtube: {yt_url.code} - {yt_url.msg}" )
            #     self.write( "Error returned by Youtube: " + str(yt_url) )
            #     self.write( f"<br/>https://www.youtube.com/watch?v={video}" ) #this helps with debugging

    # def ytdlp_get_url( self, videoid ):
    #     # https://codepal.ai/code-generator/query/OOhjOSAi/retrieve-video-url-using-yt-dlp-python
    #     import yt_dlp
    #     URL = "https://www.youtube.com/watch?v=" + videoid

    #     opts = {
    #         'format': 'best',
    #         'quiet': True,
    #         'noplaylist': True,
    #         'cookies-from-browser': 'firefox',
    #         'cookies': '/opt/cookies.txt',
    #     }

    #     with yt_dlp.YoutubeDL( opts ) as ydl:
    #         info = ydl.extract_info( URL, download=False )
    #         return info.get('url', None)

    #     return None

    def data_received(self, chunk):
        pass

class AudioHandler(web.RequestHandler):
    """
    Handles HTTP requests for YouTube audio processing.
    
    This request handler manages audio downloads and conversions,
    providing endpoints to process YouTube videos and convert
    their content to audio formats.
    """

    def initialize(self):
        """
        Initialize the object.
        """
        self.disconnected = False

    @gen.coroutine
    def head(self, audio):
        """
        Coroutine function to set headers for audio file response.

        Args:
            self: The instance of the class.
            audio: The audio file to be served.

        Returns:
            None
        """
        self.set_header('Accept-Ranges', 'bytes')
        self.set_header("Content-Type", "audio/mpeg")

    @gen.coroutine
    def get(self, audio):
        """
        A coroutine function that handles the GET request for audio files. It checks if the requested audio is available and, if so, streams the audio content to the client. If the audio is not available or an error occurs during the conversion, appropriate status codes are set and returned.
        """
        logging.info( 'YouTube: Audio: %s (%s)', audio, self.request.remote_ip )
        if audio in video_links and 'unavailable' in video_links[audio] and video_links[audio]['unavailable'] == True:
            # logging.info('Audio: %s is not available (%s)', audio, self.request.remote_ip)
            self.set_status(422) # Unprocessable Content. E.g. the video is a live stream
            return
        mp3_file = './audio/{}.mp3'.format(audio)
        if not os.path.exists(mp3_file):
            if audio not in conversion_queue.keys():
                conversion_queue[audio] = {
                    'status': False,
                    'added': datetime.datetime.now()
                }
            while audio in conversion_queue:
                yield gen.sleep(0.5)
                if self.disconnected:
                    # logging.info('User was disconnected while requested audio: %s (%s)', audio, self.request.remote_ip)
                    self.set_status(408)
                    return
        if audio in video_links and 'unavailable' in video_links[audio] and video_links[audio]['unavailable'] == True:
            # logging.info('Audio: %s is not available (%s)', audio, self.request.remote_ip)
            self.set_status(422) # Unprocessable Content. E.g. the video is a live stream
            return
        if not os.path.exists(mp3_file):
            self.set_status(404) # An error occurred during the conversion and the file was not created
            return
        request_range = None
        range_header = self.request.headers.get("Range")
        if range_header:
            # As per RFC 2616 14.16, if an invalid Range header is specified,
            # the request will be treated as if the header didn't exist.
            request_range = httputil._parse_request_range(range_header)

        size = os.stat(mp3_file).st_size
        if request_range:
            start, end = request_range
            if (start is not None and start >= size) or end == 0:
                # As per RFC 2616 14.35.1, a range is not satisfiable only: if
                # the first requested byte is equal to or greater than the
                # content, or when a suffix with length 0 is specified
                self.set_status(416)  # Range Not Satisfiable
                self.set_header("Content-Type", "audio/mpeg")
                self.set_header("Content-Range", "bytes */%s" % (size,))
                return
            if start is not None and start < 0:
                start += size
            if end is not None and end > size:
                # Clients sometimes blindly use a large range to limit their
                # download size; cap the endpoint at the actual file size.
                end = size
            # Note: only return HTTP 206 if less than the entire range has been
            # requested. Not only is this semantically correct, but Chrome
            # refuses to play audio if it gets an HTTP 206 in response to
            # ``Range: bytes=0-``.
            if size != (end or size) - (start or 0):
                self.set_status(206)  # Partial Content
                self.set_header(
                    "Content-Range",
                    httputil._get_content_range(start, end, size)
                )
        else:
            start = end = None
        if start is not None and end is not None:
            content_length = end - start
        elif end is not None:
            content_length = end
        elif start is not None:
            content_length = size - start
        else:
            content_length = size
        self.set_header("Accept-Ranges", "bytes")
        self.set_header("Content-Length", content_length)
        self.set_header('Content-Type', 'audio/mpeg')
        content = self.get_content(mp3_file, start, end)
        if isinstance(content, bytes):
            content = [content]
        for chunk in content:
            try:
                self.write(chunk)
                yield self.flush()
            except iostream.StreamClosedError:
                return

    @classmethod
    def get_content(cls, abspath, start=None, end=None):
        """Retrieve the content of the requested resource which is located
        at the given absolute path.

        This class method may be overridden by subclasses.  Note that its
        signature is different from other overridable class methods
        (no ``settings`` argument); this is deliberate to ensure that
        ``abspath`` is able to stand on its own as a cache key.

        This method should either return a byte string or an iterator
        of byte strings.  The latter is preferred for large files
        as it helps reduce memory fragmentation.

        .. versionadded:: 3.1
        """
        Path(abspath).touch(exist_ok=True)
        with open(abspath, "rb") as audio_file:
            if start is not None:
                audio_file.seek(start)
            if end is not None:
                remaining = end - (start or 0)
            else:
                remaining = None
            while True:
                chunk_size = 1024 ** 2
                if remaining is not None and remaining < chunk_size:
                    chunk_size = remaining
                chunk = audio_file.read(chunk_size)
                if chunk:
                    if remaining is not None:
                        remaining -= len(chunk)
                    yield chunk
                else:
                    if remaining is not None:
                        assert remaining == 0
                    return

    def on_connection_close(self):
        """
        Handle the event when the connection is closed. It sets the 'disconnected' attribute to True.
        """
        logging.warning( 'YouTube: User quit during transcoding (%s)', self.request.remote_ip )
        self.disconnected = True

    def data_received(self, chunk):
        pass

class UserHandler(web.RequestHandler):
    """
    Handles HTTP requests for YouTube user processing.
    
    This request handler manages user channel downloads and conversions,
    providing endpoints to process YouTube user channels and convert
    their content to audio or video formats.
    """

    def initialize(self, channel_handler_path: str):
        """
        Initialize the channel handler with the specified path.

        Args:
            channel_handler_path (str): The path to the channel handler.

        Returns:
            None
        """
        self.channel_handler_path = channel_handler_path

    def get_canonical(self, url):
        """
        Get the canonical URL from the given input URL.

        Args:
            url (str): The input URL for which the canonical URL needs to be retrieved.

        Returns:
            str: The canonical URL if found, otherwise None.
        """
        logging.info( 'YouTube: Getting canonical for %s', url )
        req = requests.get( url )
        if req.status_code == 200:
            from bs4 import BeautifulSoup
            bs = BeautifulSoup( req.text, 'lxml' )
            can_url = None

            # loop through all links and find the canonical url
            for link in bs.find_all("link"):
                try:
                    if link['rel'][0] == 'canonical':
                        can_url = link['href']
                        break
                except:
                    # not all links have a rel
                    pass

            del bs
            return can_url
        return None

    def get_channel_token(self, username: str) -> str:
        """
        Get the channel token for the given username.

        Args:
            username (str): The username for which the channel token is being retrieved.

        Returns:
            str: The channel token associated with the given username.
        """
        global channel_name_to_id
        if username in channel_name_to_id and channel_name_to_id[username]['expire'] > datetime.datetime.now():
            return channel_name_to_id[username]['id']
        yt_url = f"https://www.youtube.com/@{username}/about"
        canon_url = self.get_canonical( yt_url )
        logging.debug( 'Canonical url: %s', canon_url )
        if canon_url is None:
            return None
        token_index = canon_url.rfind("/") + 1
        channel_token = canon_url[token_index:]
        channel_name_to_id[username] = {
            'id': channel_token,
            'expire': datetime.datetime.now() + datetime.timedelta(hours=24)
        }
        return channel_token

    def get(self, username):
        """
        A method to handle a Youtube channel by name and redirect to the corresponding URL.

        Args:
            username (str): The username of the Youtube channel.

        Returns:
            None
        """
        logging.debug( 'YouTube: Handling Youtube channel by name: %s', username )
        append = None
        append_index = username.find('/')
        if append_index > -1:
            append = username[append_index:]
            username = username[:append_index]
        channel_token = self.get_channel_token(username)

        if channel_token is None:
            logging.error( 'YouTube: Failed to get canonical URL of %s', username )
        else:
            selfurl = self.channel_handler_path + channel_token
            if append is not None:
                selfurl += append
            logging.info( 'YouTube: Redirect to %s', selfurl )
            self.redirect( selfurl, permanent = False )
        return None

    def data_received(self, chunk):
        pass

class ClearCacheHandler(web.RequestHandler):
    """
    Handles HTTP requests for clearing various caches in the YouTube application.
    
    This request handler provides endpoints to clear different types of caches
    including video files, video links, playlist feeds, channel feeds, and
    channel name to ID mappings.
    """

    ALL = "ALL"
    NONE = "NONE"

    VIDEO_FILES = "VIDEO_FILES"
    VIDEO_LINKS = "VIDEO_LINKS"
    PLAYLIST_FEED = "PLAYLIST_FEED"
    CHANNEL_FEED = "CHANNEL_FEED"
    CHANNEL_NAME_TO_ID = "CHANNEL_NAME_TO_ID"

    def post(self):
        """
        A description of the entire function, its parameters, and its return types.
        """
        self.get()

    def get(self):
        """
        A function to handle clearing the cache for various video and playlist items.
        """
        global video_links, playlist_feed, channel_feed, channel_name_to_id

        video_file = self.get_argument(ClearCacheHandler.VIDEO_FILES, ClearCacheHandler.NONE, True)
        video_link = self.get_argument(ClearCacheHandler.VIDEO_LINKS, ClearCacheHandler.NONE, True)
        playlist_feed = self.get_argument(ClearCacheHandler.PLAYLIST_FEED, ClearCacheHandler.NONE, True)
        channel_feed = self.get_argument(ClearCacheHandler.CHANNEL_FEED, ClearCacheHandler.NONE, True)
        channel_name_to_id = self.get_argument(ClearCacheHandler.CHANNEL_NAME_TO_ID, ClearCacheHandler.NONE, True)

        if any(element != ClearCacheHandler.NONE for element in [video_file, video_link, playlist_feed, channel_feed, channel_name_to_id]):
            logging.info( 'YouTube: Force clear cache started (%s)', self.request.remote_ip )

        if video_file == ClearCacheHandler.ALL:
            for f in glob.glob('./audio/*mp3'):
                try:
                    os.remove(f)
                    logging.info( 'YouTube: Deleted %s', f )
                except Exception as e:
                    logging.error( 'YouTube: Error remove file %s: %s', f, e )
        elif video_file != ClearCacheHandler.NONE:
            f = f"./audio/{video_file}"
            try:
                os.remove(f)
                logging.info( 'YouTube: Deleted %s', f )
            except Exception as e:
                logging.error( 'YouTube: Error remove file %s: %s', f, e )

        if video_link == ClearCacheHandler.ALL:
            video_links_length = len(video_links)
            video_links = {}
            logging.info( 'YouTube: Cleaned %s items from video list', video_links_length )
        elif video_link != ClearCacheHandler.NONE:
            if video_link in video_links:
                del video_links[video_link]
                logging.info( 'YouTube: Cleaned 1 items from video list' )

        if playlist_feed == ClearCacheHandler.ALL:
            playlist_feed_length = len(playlist_feed)
            playlist_feed = {}
            logging.info( 'YouTube: Cleaned %s items from playlist feeds', playlist_feed_length )
        elif playlist_feed != ClearCacheHandler.NONE:
            if playlist_feed in playlist_feed:
                del playlist_feed[playlist_feed]
                logging.info( 'YouTube: Cleaned 1 items from playlist feeds' )

        if channel_feed == ClearCacheHandler.ALL:
            channel_feed_length = len(channel_feed)
            channel_feed = {}
            logging.info( 'YouTube: Cleaned %s items from channel feeds', channel_feed_length )
        elif channel_feed != ClearCacheHandler.NONE:
            if channel_feed in channel_feed:
                del channel_feed[channel_feed]
                logging.info( 'YouTube: Cleaned 1 items from chann  el feeds' )

        if channel_name_to_id == ClearCacheHandler.ALL:
            channel_name_to_id_length = len(channel_name_to_id)
            channel_name_to_id = {}
            logging.info( 'YouTube: Cleaned %s items from channel name map', channel_name_to_id_length )
        elif channel_name_to_id != ClearCacheHandler.NONE:
            if channel_name_to_id in channel_name_to_id:
                del channel_name_to_id[channel_name_to_id]
                logging.info( 'YouTube: Cleaned 1 items from channel name map' )

        self.write(f'<html><head><title>PodTube (v{__version__}) cache</title>')
        self.write('<link rel="shortcut icon" href="favicon.ico">')
        self.write('</head><body>')

        self.write("<label>Clear cache</label>")
        self.write("<br/><br/>")
        self.write("<form method='POST'>")
        self.write(f"<label for='{ClearCacheHandler.VIDEO_LINKS}'>Cached video links: </label>")
        self.write(f"<select id='{ClearCacheHandler.VIDEO_LINKS}' name='{ClearCacheHandler.VIDEO_LINKS}'>")
        self.write(f"<option value='{ClearCacheHandler.NONE}' selected>{ClearCacheHandler.NONE}</option>")
        self.write(f"<option value='{ClearCacheHandler.ALL}'>{ClearCacheHandler.ALL}</option>")
        for video, info in video_links.items():
            self.write(f"<option value='{video}'>{video}</option>")
        self.write("</select>")
        self.write("<br/><br/>")

        self.write(f"<label for='{ClearCacheHandler.PLAYLIST_FEED}'>Cached playlist feed: </label>")
        self.write(f"<select id='{ClearCacheHandler.PLAYLIST_FEED}' name='{ClearCacheHandler.PLAYLIST_FEED}'>")
        self.write(f"<option value='{ClearCacheHandler.NONE}' selected>{ClearCacheHandler.NONE}</option>")
        self.write(f"<option value='{ClearCacheHandler.ALL}'>{ClearCacheHandler.ALL}</option>")
        for playlist, info in playlist_feed.items():
            self.write(f"<option value='{playlist}'>{playlist}</option>")
        self.write("</select>")
        self.write("<br/><br/>")

        self.write(f"<label for='{ClearCacheHandler.CHANNEL_FEED}'>Cached channel feed: </label>")
        self.write(f"<select id='{ClearCacheHandler.CHANNEL_FEED}' name='{ClearCacheHandler.CHANNEL_FEED}'>")
        self.write(f"<option value='{ClearCacheHandler.NONE}' selected>{ClearCacheHandler.NONE}</option>")
        self.write(f"<option value='{ClearCacheHandler.ALL}'>{ClearCacheHandler.ALL}</option>")
        for channel, info in channel_feed.items():
            self.write(f"<option value='{channel}'>{channel}</option>")
        self.write("</select>")
        self.write("<br/><br/>")

        self.write(f"<label for='{ClearCacheHandler.CHANNEL_NAME_TO_ID}'>Cached channel name to id: </label>")
        self.write(f"<select id='{ClearCacheHandler.CHANNEL_NAME_TO_ID}' name='{ClearCacheHandler.CHANNEL_NAME_TO_ID}'>")
        self.write(f"<option value='{ClearCacheHandler.NONE}' selected>{ClearCacheHandler.NONE}</option>")
        self.write(f"<option value='{ClearCacheHandler.ALL}'>{ClearCacheHandler.ALL}</option>")
        for channel, info in channel_name_to_id.items():
            self.write(f"<option value='{channel}'>@{channel}</option>")
        self.write("</select>")
        self.write("<br/><br/>")

        self.write(f"<label for='{ClearCacheHandler.VIDEO_FILES}'>Cached video files: </label>")
        self.write(f"<select id='{ClearCacheHandler.VIDEO_FILES}' name='{ClearCacheHandler.VIDEO_FILES}'>")
        self.write(f"<option value='{ClearCacheHandler.NONE}' selected>{ClearCacheHandler.NONE}</option>")
        self.write(f"<option value='{ClearCacheHandler.ALL}'>{ClearCacheHandler.ALL}</option>")
        for f in sorted(glob.glob('./audio/*mp3'), key=lambda a_file: os.path.getctime(a_file)):
            size = os.path.getsize(f)
            if size > 10**12:
                size = str(size // 2**40) + 'TiB'
            elif size > 10**9:
                size = str(size // 2**30) + 'GiB'
            elif size > 10**6:
                size = str(size // 2**20) + 'MiB'
            elif size > 10**3:
                size = str(size // 2**10) + 'KiB'
            else:
                size = str(size) + 'B'
            f = os.path.basename(f)
            self.write(f"<option value='{f}'>{f} ({size})</option>")
        self.write("</select>")
        self.write("<br/><br/>")
        self.write("<input type='submit' value='CLEAR SELECTED CACHE' />")
        self.write("</form>")
        self.write("<br/>")

        self.write('</body></html>')

    def data_received(self, chunk):
        pass
