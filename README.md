# [PodTube](https://github.com/aquacash5/PodTube) (v2023.04.12.05)

This is an extended functionality fork of a python application for converting Youtube, Rumble and Bitchute channels into podcast-friendly RSS feeds.

For basic or original usage that may be needed, see the original project page. To use this fork:

To use Youtube channels:
https://yourserver.com/youtube/channel/youtube-channel-id
  - You will need a Youtube API key in the 'config.ini' file:
  ```
  [youtube]
  api_key=<key goes here, obviously>
  ```
YouTube channel by @<username> (should automatically grab canonical URL):
https://yourserver.com/youtube/user/@username

To use Bitchute channels:
http://yourserver.com/bitchute/channel/bitchute-channel-name

For Rumble channels:
http://yourserver.com/rumble/channel/rumble-channel-name

For Rumble users:
http://yourserver.com/rumble/user/rumble-user-name

For Rumble Categories:
http://yourserver.com/rumble/category/category-name

For Daily Motion users:
http://yourserver.com/dailymotion/user/dailymotion-user-name



Docker container info:
Be sure to open a port to containers default 15000

-e YT_API_KEY  -  required for Youtube functions

https://hub.docker.com/r/ftawesome/podtube