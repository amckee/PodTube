# Archived

This project is now archived. I haven't worked on it for years and
[amckee](https://github.com/amckee) is pushing forward with new and exciting
changes on his fork at [https://github.com/amckee/PodTube](https://github.com/amckee/PodTube).

# [PodTube](https://github.com/aquacash5/PodTube) (v3.0)

This is a python application for converting Youtube playlists and channels into podcast rss feeds.

### [LICENSE](https://github.com/aquacash5/podtube/blob/master/LICENSE)

## Requirements

#### Python

- [tornado](https://pypi.org/project/tornado/)
- [misaka](https://pypi.python.org/pypi/misaka/)
- [pytube](https://pypi.python.org/pypi/pytube/)
- [feedgen](https://pypi.python.org/pypi/feedgen/)
- [requests](https://pypi.org/project/requests/)
- [psutil](https://pypi.org/project/psutil/)

#### System

- [ffmpeg](http://ffmpeg.org/)

## Starting Server

```
podtube.py [-h] key [port]
```

#### Positional Arguments:

| Key  | Description              | Default |
| ---- | ------------------------ | ------- |
| key  | Google's API Key         | None    |
| port | Port Number to listen on | 80      |

#### Optional Arguments:

| Key                 | Description                                           |
| ------------------- | ----------------------------------------------------- |
| -h, --help          | show this help message and exit                       |
| --log-file FILE     | Location and name of log file                         |
| --log-format FORMAT | Logging format using syntax for python logging module |
| -v, --version       | show program's version number and exit                |

## Usage

#### Playlists

Get the playlist id from the youtube url

```
https://www.youtube.com/playlist?list=<PlaylistID>
```

Add the url to your podcast client of choice

```
http://<host>:<port>/playlist/<PlaylistID>
```

If you want an audio podcast add a /audio to the url

```
http://<host>:<port>/playlist/<PlaylistID>/audio
```

#### Channels

Get the channel id or username from the youtube url

```
https://www.youtube.com/channel/<ChannelID>
```
or
```
https://www.youtube.com/user/<Username>
```

Add the url to your podcast client of choice

```
http://<host>:<port>/channel/<ChannelID>
```
or
```
http://<host>:<port>/channel/<Username>
```

If you want an audio podcast add a /audio to the url

```
http://<host>:<port>/channel/<Username>/audio
```

## Examples

#### Playlists

[http://podtube.aquacash5.com/playlist/PLlUk42GiU2guNzWBzxn7hs8MaV7ELLCP_](http://podtube.aquacash5.com/playlist/PLlUk42GiU2guNzWBzxn7hs8MaV7ELLCP_)

[http://podtube.aquacash5.com/playlist/PLlUk42GiU2guNzWBzxn7hs8MaV7ELLCP_/video](http://podtube.aquacash5.com/playlist/PLlUk42GiU2guNzWBzxn7hs8MaV7ELLCP_/video)

[http://podtube.aquacash5.com/playlist/PLlUk42GiU2guNzWBzxn7hs8MaV7ELLCP_/audio](http://podtube.aquacash5.com/playlist/PLlUk42GiU2guNzWBzxn7hs8MaV7ELLCP_/audio)


#### Channels

[http://podtube.aquacash5.com/channel/scishow](http://podtube.aquacash5.com/channel/scishow)

[http://podtube.aquacash5.com/channel/UCZYTClx2T1of7BRZ86-8fow](http://podtube.aquacash5.com/channel/UCZYTClx2T1of7BRZ86-8fow)

[http://podtube.aquacash5.com/channel/scishow/video](http://podtube.aquacash5.com/channel/scishow/video)

[http://podtube.aquacash5.com/channel/UCZYTClx2T1of7BRZ86-8fow/video](http://podtube.aquacash5.com/channel/UCZYTClx2T1of7BRZ86-8fow/video)

[http://podtube.aquacash5.com/channel/scishow/audio](http://podtube.aquacash5.com/channel/scishow/audio)

[http://podtube.aquacash5.com/channel/UCZYTClx2T1of7BRZ86-8fow/audio](http://podtube.aquacash5.com/channel/UCZYTClx2T1of7BRZ86-8fow/audio)
