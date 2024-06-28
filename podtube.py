#!/usr/bin/python3

from configparser import ConfigParser
import glob
import logging
import os
from argparse import ArgumentParser
import sys

from tornado import ioloop, web
import misaka
import utils
import youtube
import bitchute
import rumble
import dailymotion

# Handled automatically by git pre-commit hook
__version__ = '2024.06.24.1'

class FileHandler(web.RequestHandler):
    def get(self):
        """
        A method to handle GET requests and serve the README page with PodTube information.
        """
        logging.info('ReadMe (%s)', self.request.remote_ip)
        self.write('<html><head><title>PodTube (v')
        self.write(__version__)
        self.write(')</title><link rel="shortcut icon" href="favicon.ico">')
        self.write('<link rel="stylesheet" type="text/css" href="markdown.css">')
        self.write('</head><body>')
        with open('README.md') as text:
            self.write(
                misaka.html(
                    text.read(),
                    extensions=('tables', 'fenced-code')
                )
            )
        self.write('</body></html>')

def get_env_or_config_option(conf: ConfigParser, env_name: str, config_name: str, default_value = None):
    """
    Get the value of a configuration option from the given ConfigParser object or from the environment variable.
    
    Args:
        conf (ConfigParser): The ConfigParser object containing the configuration options.
        env_name (str): The name of the environment variable to check for the option value.
        config_name (str): The name of the configuration option to retrieve.
        default_value: The default value to return if the option is not found in the configuration or environment.

    Returns:
        The value of the configuration option from the ConfigParser object or environment variable, or the default value if not found.
    """
    return utils.get_env_or_config_option(conf, env_name, config_name, "general", default_value=default_value)

def make_app(config: ConfigParser):
    """
    Initializes the web application with the given configuration and returns the initialized web application.

    Parameters:
    - config: ConfigParser - the configuration to initialize the web application.

    Returns:
    - web.Application - the initialized web application.
    """
    youtube.init(config)
    webapp = web.Application([
        (r'/youtube/channel/(.*)', youtube.ChannelHandler, {
            'video_handler_path': '/youtube/video/',
            'audio_handler_path': '/youtube/audio/',
        }),
        (r'/youtube/playlist/(.*)', youtube.PlaylistHandler, {
            'video_handler_path': '/youtube/video/',
            'audio_handler_path': '/youtube/audio/',
        }),
        (r'/youtube/video/(.*)', youtube.VideoHandler),
        (r'/youtube/audio/(.*)', youtube.AudioHandler),
        (r'/youtube/user/@(.*)', youtube.UserHandler, {'channel_handler_path': '/youtube/channel/'}),
        (r'/youtube/cache/', youtube.ClearCacheHandler),
        (r'/rumble/user/(.*)', rumble.UserHandler),
        (r'/rumble/channel/(.*)', rumble.ChannelHandler),
        (r'/rumble/video/(.*)', rumble.VideoHandler),
        (r'/rumble/category/(.*)', rumble.CategoryHandler),
        (r'/bitchute/channel/(.*)', bitchute.ChannelHandler),
        (r'/bitchute/video/(.*)', bitchute.VideoHandler),
        (r'/dailymotion/channel/(.*)', dailymotion.ChannelHandler),
        (r'/dailymotion/video/(.*)', dailymotion.VideoHandler),
        (r'/config.ini', web.RedirectHandler, {'url': '/'}),
        (r'/README.md', web.RedirectHandler, {'url': '/'}),
        (r'/Dockerfile', web.RedirectHandler, {'url': '/'}),
        (r'/', FileHandler),
        (r'/(.*)', web.StaticFileHandler, {'path': '.'})
    ], compress_response=True)
    return webapp

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists('./audio'):
        os.mkdir('audio')
    defaults = {}
    parser = ArgumentParser(
        description="This is a python application for converting Youtube, Rumble and Bitchute channels into podcast-friendly RSS feeds."
    )
    parser.add_argument(
        '--config-file',
        type=str,
        help='Location and name of config file'
    )
    parser.add_argument(
        'port',
        type=int,
        nargs='?',
        help='Port Number to listen on'
    )
    defaults["port"] = 15000
    parser.add_argument(
        '--log-file',
        type=str,
        help='Location and name of log file'
    )
    defaults["log_file"] = '/dev/stdout'
    parser.add_argument(
        '--log-format',
        type=str,
        help='Logging format using syntax for python logging module'
    )
    defaults["log_format"] = '%(asctime)-15s [%(levelname)s] %(message)s'
    parser.add_argument(
        '--log-level',
        type=str,
        help="Logging level using for python logging module",
        choices=logging._nameToLevel.keys()
    )
    defaults['log_level'] = logging.getLevelName(logging.INFO)
    parser.add_argument(
        '--log-filemode',
        type=str,
        help="Logging file mode using for python logging module",
        choices=['a', 'w']
    )
    defaults['log_filemode'] = 'a'
    parser.add_argument(
        '-v', '--version',
        action='version',
        version="%(prog)s " + __version__
    )
    args = parser.parse_args()
    conf = None
    env_conf_file = os.getenv("CONFIG_FILE")
    if env_conf_file is not None:
        args.config_file = env_conf_file
    if args.config_file:
        conf = ConfigParser(inline_comment_prefixes='#')
        read_ok = conf.read(args.config_file)
        if not read_ok:
            print("Error reading configuration file: " + args.config_file, file=sys.stderr, flush=True)
            conf = None
    args.port         = args.port         if args.port         is not None else get_env_or_config_option(conf, "GENERAL_PORT"        , "port"        , defaults["port"])
    args.log_file     = args.log_file     if args.log_file     is not None else get_env_or_config_option(conf, "GENERAL_LOG_FILE"    , "log_file"    , defaults["log_file"])
    args.log_format   = args.log_format   if args.log_format   is not None else get_env_or_config_option(conf, "GENERAL_LOG_FORMAT"  , "log_format"  , defaults["log_format"])
    args.log_level    = args.log_level    if args.log_level    is not None else get_env_or_config_option(conf, "GENERAL_LOG_LEVEL"   , "log_level"   , defaults["log_level"])
    args.log_filemode = args.log_filemode if args.log_filemode is not None else get_env_or_config_option(conf, "GENERAL_LOG_FILEMODE", "log_filemode", defaults["log_filemode"])
    logging.basicConfig(
        level=logging.getLevelName(args.log_level),
        format=args.log_format,
        filename=args.log_file,
        filemode=args.log_filemode
    )
    for file in glob.glob('audio/*.temp'):
        os.remove(file)
    logging.info("Start server")
    app = make_app(conf)
    app.listen(args.port)
    logging.info(f'Started listening on {args.port}')
    ioloop.IOLoop.instance().start()
