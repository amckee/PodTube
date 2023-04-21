# [PodTube](https://github.com/aquacash5/PodTube) (v2023.04.12.05)

This is an extended functionality fork of a python application for converting Youtube, Rumble and Bitchute channels into podcast-friendly RSS feeds.

For basic or original usage that may be needed, see the original project page. To use this fork:

## Usage

### Youtube

#### Key

You will need a Youtube API key in the `config.ini` file:

```
[youtube]
api_key=<key goes here, obviously>
```

Or set the key to the environment variable `YT_API_KEY`

The environment variable has higher priority than config

#### Channels

```
http://yourserver.com/youtube/channel/youtube-channel-id
```

YouTube channel by @<username> (should automatically grab canonical URL):

```
http://yourserver.com/youtube/user/@username
```

#### Playlists

```
http://yourserver.com/youtube/playlist/<PlaylistID>
```

#### Audio

If you want an audio podcast add a /audio to the url

```
http://yourserver.com/youtube/playlist/<PlaylistID>/audio

http://yourserver.com/youtube/channel/youtube-channel-id/auido

http://yourserver.com/youtube/user/@username/auido
```

### Bitchute

#### Channels

```
http://yourserver.com/bitchute/channel/bitchute-channel-name
```

### Rumble

#### Channels

```
http://yourserver.com/rumble/channel/rumble-channel-name
```

#### Users

```
http://yourserver.com/rumble/user/rumble-user-name
```

#### Categories

```
http://yourserver.com/rumble/category/category-name
```

### Daily Motion

```
http://yourserver.com/dailymotion/user/dailymotion-user-name
```

## Docker
Docker container info:
Be sure to open a port to containers default 15000


`-e YT_API_KEY`  -  required for Youtube functions

[https://hub.docker.com/r/ftawesome/podtube](https://hub.docker.com/r/ftawesome/podtube)