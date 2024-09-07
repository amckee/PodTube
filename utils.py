from configparser import ConfigParser, NoOptionError, NoSectionError
import logging
import os
from asyncio import sleep
from datetime import datetime
import sys
from urllib.parse import urlencode

from pytubefix import YouTube

video_links = dict()
metric_chart = {
    'k': 3,  # kilo
    'M': 6,  # Mega
    'G': 9,  # Giga
    'T': 12  # Tera
}

def parametrize(url, params):
    return url + '?' + urlencode(params)

def get_resolution(yt_video):
    return int(''.join(filter(str.isdigit, yt_video.resolution[:-1])))

def get_youtube_url(video_id):
    if video_id in video_links and video_links[video_id]['expire'] > datetime.now():
        return video_links[video_id]['url']
    yt_video = YouTube(f'http://www.youtube.com/watch?v={video_id}')
    video_url = yt_video.streams.get_highest_resolution().url
    parts = {part.split('=')[0]: part.split('=')[1] for part in video_url.split('?')[-1].split('&')}
    link = {'url': video_url, 'expire': datetime.fromtimestamp(int(parts['expire']))}
    video_links[video_id] = link
    return link['url']

def metric_to_base(metric):
    return int(metric[:-1]) * (10 ** metric_chart[metric[-1]])

async def get_total_storage(directory='.'):
    total_storage = 0
    for root, directories, files in os.walk(directory):
        for file in files:
            total_storage += os.path.getsize(os.path.join(root, file))
            await sleep(0)
    return total_storage

def convert_to_bool(input) -> bool:
    if type(input) is str:
        return input.lower() in ['1', 'true', 't', 'yes', 'y', 'on']
    return bool(input)

def get_env_or_config_option(conf: ConfigParser, env_name: str, config_name: str, config_section: str, conf_raw: bool = True, default_value = None):
    value = os.getenv(env_name)
    if value is not None:
        log_or_print("Got '%s' from ENV: %s", env_name, value)
    elif conf is not None:
        try:
            value = conf.get(config_section, config_name, raw=conf_raw)
            log_or_print("Got '%s:%s' from config file: %s", config_section, config_name, value)
        except Exception as e:
            value = default_value
            if isinstance(e, (NoSectionError, NoOptionError)):
                log_or_print("No configuration '%s:%s'. Default value is used: %s", config_section, config_name, value)
            else:
                error_or_print("An error occurred while reading configuration '%s:%s'. Default value is used: %s. Error: %s", config_section, config_name, value, e)
    else:
        value = default_value
        log_or_print("No configuration file or environment variable '%s'. Default value is used: %s", env_name, value)
    return value


def is_log_inited():
    return len(logging.root.handlers) > 0

def log_or_print(msg: str, *args, **kwargs):
    if is_log_inited():
        logging.info(msg, *args, **kwargs)
    else:
        print(msg % args, file=sys.stdout, flush=True)

def error_or_print(msg: str, *args, **kwargs):
    if is_log_inited():
        logging.error(msg, *args, **kwargs)
    else:
        print(msg % args, file=sys.stderr, flush=True)