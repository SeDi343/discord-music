# Welcome to a simple Music Discord Bot
A Music Discord Bot that uses ytdl and ffmpeg to play some fancy music and simply works. This Bot uses Slash Commands.  

### Dependencies
* python3.8
* ffmpeg
* screen
First you need to download ffmpeg https://ffmpeg.org/download.html#build-linux  
This Music Bot requires python3 and python venv(tested on 3.11 and 3.13) https://www.python.org/downloads/  

Install python requirements using:
* python3 -m venv discord-music-venv
* source discord-music-venv/bin/activate
* pip install -r requirements.txt
* python index.py / sh start.sh (for a screen session)

### Installation
Create a new application at https://discord.com/developers/applications and put Bot Token into config.json
