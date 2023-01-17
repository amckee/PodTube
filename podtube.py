#!/usr/bin/python3

import glob, logging, os
from argparse import ArgumentParser

#import misaka
import youtube, bitchute, rumble, dailymotion
from tornado import gen, httputil, ioloop, iostream, process, web

__version__ = 'v2022.12.20.1'

def make_app(key="test"):
    webapp = web.Application([
        (r'/youtube/channel/(.*)', youtube.ChannelHandler),
        (r'/youtube/playlist/(.*)', youtube.PlaylistHandler),
        (r'/youtube/video/(.*)', youtube.VideoHandler),
        (r'/youtube/audio/(.*)', youtube.AudioHandler),
        (r'/youtube/', youtube.FileHandler),
        (r'/rumble/user/(.*)', rumble.UserHandler),
        (r'/rumble/channel/(.*)', rumble.ChannelHandler),
        (r'/rumble/video/(.*)', rumble.VideoHandler),
        (r'/bitchute/channel/(.*)', bitchute.ChannelHandler),
        (r'/bitchute/video/(.*)', bitchute.VideoHandler),
        (r'/dailymotion/channel/(.*)', dailymotion.ChannelHandler),
        (r'/dailymotion/video/(.*)', dailymotion.VideoHandler),
        (r'/(.*)', web.StaticFileHandler, {'path': '.'})
    ], compress_response=True)
    return webapp

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists('./audio'):
        os.mkdir('audio')
    parser = ArgumentParser(prog='PodTube')
    parser.add_argument(
        'port',
        type=int,
        default=15000,
        nargs='?',
        help='Port Number to listen on'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        default='podtube.log',
        metavar='FILE',
        help='Location and name of log file'
    )
    parser.add_argument(
        '--log-format',
        type=str,
        default='%(asctime)-15s %(message)s',
        metavar='FORMAT',
        help='Logging format using syntax for python logging module'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version="%(prog)s " + __version__
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG,
        format=args.log_format,
        filename=args.log_file,
        filemode='a'
    )
    for file in glob.glob('audio/*.temp'):
        os.remove(file)
    app = make_app( )
    app.listen(args.port)
    logging.info(f'Started listening on {args.port}')
    ioloop.PeriodicCallback(
        callback=youtube.cleanup,
        callback_time=1000
    ).start()
    ioloop.PeriodicCallback(
        callback=youtube.convert_videos,
        callback_time=1000
    ).start()
    ioloop.IOLoop.instance().start()
