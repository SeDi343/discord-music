#!/usr/bin/env python3
# Imports
import os
import sys
import json
import asyncio
import requests
import traceback
#from youtube_dl import YoutubeDL
from yt_dlp import YoutubeDL
from discord import app_commands, Intents, Client, Interaction, Status, Game, FFmpegPCMAudio, errors, PCMVolumeTransformer

#########################################################################################
# Requirements for Discord Bot
#########################################################################################

# Read config file
with open("config.json", 'r') as jsonfile:
   config_data = json.load(jsonfile)
   token = config_data.get("discord_token")

# Check if token is valid
r = requests.get("https://discord.com/api/v10/users/@me", headers={
    "Authorization": f"Bot {token}"
})

# If the token is correct, it will continue the code
data = r.json()

if not data.get("id", None):
   print("\n".join(["ERROR: Token is not valid!"]))
   sys.exit(False)

# Welcome in console
print("\n".join([
   "Starting Discord Bot..."
]))

# Configurations for Youtube DL
yt_dl_opts = {
   'format': 'm4a/bestaudio/best',
   'noplaylist': 'True',
   'outtmpl': 'download/%(id)s',
}
ytdl = YoutubeDL(yt_dl_opts)
stream = False

# Configurations for FFMPEG
ffmpeg_options = {
   'options': '-vn'
}

# Variable for multiple voice clients in different guilds
voice_clients = {}

# Variable for queue
queues = {}

# New queue
new_queue = {}

# Define a flag to indicate whether the bot should continue playing the next song
should_continue = {}

# Variable for Volume
volume_val = {}

# Main Class for Discord
class MusicBot(Client):
   def __init__(self):
      super().__init__(intents = Intents.all())
      self.tree = app_commands.CommandTree(self)

   async def setup_hook(self) -> None:
      """ This is called when the bot boots, to setup the global commands """
      await self.tree.sync(guild = None)

client = MusicBot()

#########################################################################################
# Start Up
#########################################################################################

@client.event
async def on_ready():
    """ This is called when the bot is ready and has a connection with Discord
        It also prints out the bot's invite URL that automatically uses your
        Client ID to make sure you invite the correct bot with correct scopes.
    """
    print("\n".join([
        f"Logged in as {client.user} (ID: {client.user.id})",
        "",
        f"Use this URL to invite {client.user} to your server:",
        f"https://discord.com/api/oauth2/authorize?client_id={client.user.id}&scope=applications.commands%20bot"
    ]))

    #await client.change_presence(status=Status.online, activity=Game(name="You don't regret the things you did wrong as much as the ones you didn't even try."))
    await client.change_presence(status=Status.online, activity=Game(name="Update: Can now queue up songs for you :)"))

#########################################################################################
# Functions
#########################################################################################

# Function to check out all available commands
async def _init_command_help_response(interaction):
   """The function to check help"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the help command.")

      await interaction.response.send_message("\n".join([
         f"Available Commands for {client.user.mention}:",
         "**\\help** - Shows this Message.",
         "**\\join** - Let\'s the user join into Users Channel.",
         "**\\play url** - Start playback of Youtube URL or add it to queue if playback already started.",
         "**\\search string** - Search Youtube and play first Video from Search or add it to queue if playback already started.",
         "**\\next** or **\\skip** - Skip current playback and continue with next song in the queue.",
         "**\\queue** or **\\list** - Print out the currently listed queue of songs",
         "**\\volume 0-100** - Change Volume of Playback. Default is 3.",
         "**\\pause** - Pause the current Playback to continue Playback later.",
         "**\\resume** - Resume paused Playback.",
         "**\\stop** - Stops current Playback.",
         "**\\disconnect** or **\\leave** - Remove Bot from Playback Channel.",
         f"**\\donation** - A link to support the creator of {client.user.mention}",
      ]))
   except Exception:
      print(f" > Exception occured processing help command: {traceback.print_exc()}")
      return await interaction.response.send_message(f"Can not process help command. Please contact <@164129430766092289> when this happened.")


# Private Function to play next song in queue
def _play_next_song(guild):
   if should_continue[guild]:
      if len(queues[guild]) > 0:
         player = queues[guild].pop(0)
         new_queue[guild] = False
         voice_clients[guild].play(player['player'], after=lambda _: _play_next_song(guild))
         voice_clients[guild].source.volume = volume_val[guild]
   else:
      should_continue[guild]

# Function to join channel
async def _init_command_join_response(interaction):
   """The function to join a channel"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the join command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      # Connect to Users Channel
      if voice_clients.setdefault(interaction.guild.id) != None:
         await voice_clients[interaction.guild.id].disconnect()
      voice_client = await interaction.user.voice.channel.connect()
      voice_clients[voice_client.guild.id] = voice_client

      # Create an empty list for the queued songs
      queues[interaction.guild.id] = []

      # Set default volume level
      volume_val[interaction.guild.id] = 0.01

      # Write in Chat that Bot joined channel
      await interaction.followup.send(f"Joined Channel **{interaction.user.voice.channel.name}**")
   except Exception:
      print(f" > Exception occured processing join command: {traceback.print_exc()}")
      return await interaction.followup.send("Unable to Join Channel. Make sure you are in a Voice Channel.")


# Function to start playing
async def _init_command_play_response(interaction, url):
   """The function to start playing audio"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the play command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      # If URL contains spotify link print out this exception.
      if "spotify.com" in url:
         await interaction.followup.send("Unable to start Spotify Playback. Currently only Youtube is supported.")
         return

      # Check if user parsed a youtube list.
      if "&list=" in url:
         await interaction.followup.send("Can not add Youtube Playlists to Bot.")
         return

      # If no Youtube URL is given
      if not any(substring in url for substring in ["youtube.com", "youtu.be"]):
         await interaction.followup.send("Youtube URL is required for this command. Use **/search** if you want to search for a song.")
         return

      # Similar to a Thread it will run independent from the program. Sent command will only
      # effect current user session
      loop = asyncio.get_event_loop()
      data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=(not stream)))

      song = data['url'] if stream else ytdl.prepare_filename(data)
      player = PCMVolumeTransformer(FFmpegPCMAudio(song, **ffmpeg_options), volume = volume_val[interaction.guild.id])

      # Check if Bot is connected to a channel
      if voice_clients[interaction.guild.id] != None:

          # Check if queue for voice channel does already exist. If not create one
         if queues[interaction.guild.id] == None:
            queues[interaction.guild.id] = []

         # Tell Discord that it should continue playback
         should_continue[interaction.guild.id] = True

         # Add player to queue
         queues[interaction.guild.id].append({'player': player, 'title': data['title'], 'duration': data['duration_string']})

         # Check if Bot is not already playing
         if not voice_clients[interaction.guild.id].is_playing() and queues[interaction.guild.id]:
            voice_clients[interaction.guild.id].play(queues[interaction.guild.id][0]['player'], after=lambda _: _play_next_song(interaction.guild.id))
            new_queue[interaction.guild.id] = True
         else:
            if new_queue[interaction.guild.id] == True:
               return await interaction.followup.send(f"Queued Song: **{data['title']}** (`{data['duration_string']}`)\n{len(queues[interaction.guild.id])-1} Songs queued")
            else:
               return await interaction.followup.send(f"Queued Song: **{data['title']}** (`{data['duration_string']}`)\n{len(queues[interaction.guild.id])} Songs queued")
      else:
         return await interaction.followup.send("Not connected to a channel. Use **/join** first")

      await interaction.followup.send(f"Start playing: **{data['title']}** (`{data['duration_string']}`)")

   except KeyError or errors.ClientException:
      print(f" > Exception occured processing play command: {traceback.print_exc()}")
      return await interaction.followup.send("Not connected to a channel. Use **/join** first!")
   except Exception:
      print(f" > Exception occured processing play command: {traceback.print_exc()}")
      return await interaction.followup.send("Can not start Playback.")


# Function to search playing
async def _init_command_search_response(interaction, search):
   """The function to search youtube"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the search command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      # Similar to a Thread it will run independent from the program. Sent command will only
      # effect current user session
      loop = asyncio.get_event_loop()
      data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{search}", download=(not stream))['entries'][0])

      song = data['url'] if stream else ytdl.prepare_filename(data)
      player = PCMVolumeTransformer(FFmpegPCMAudio(song, **ffmpeg_options), volume = volume_val[interaction.guild.id])

      # Check if Bot is connected to a channel
      if voice_clients[interaction.guild.id] != None:

          # Check if queue for voice channel does already exist. If not create one
         if queues[interaction.guild.id] == None:
            queues[interaction.guild.id] = []

         # Tell Discord that it should continue playback
         should_continue[interaction.guild.id] = True

         # Add player to queue
         queues[interaction.guild.id].append({'player': player, 'title': data['title'], 'duration': data['duration_string']})

         # Check if Bot is not playing something and song is in queue
         if not voice_clients[interaction.guild.id].is_playing() and queues[interaction.guild.id]:
            voice_clients[interaction.guild.id].play(queues[interaction.guild.id][0]['player'], after=lambda _: _play_next_song(interaction.guild.id))
            new_queue[interaction.guild.id] = True
         else:
            if new_queue[interaction.guild.id] == True:
               return await interaction.followup.send(f"Queued Song: **{data['title']}** (`{data['duration_string']}`)\n{len(queues[interaction.guild.id])-1} Songs queued")
            else:
               return await interaction.followup.send(f"Queued Song: **{data['title']}** (`{data['duration_string']}`)\n{len(queues[interaction.guild.id])} Songs queued")
      else:
         return await interaction.followup.send("Not connected to a channel. Use **/join** first")

      await interaction.followup.send(f"Start playing: **{data['title']}** (`{data['duration_string']}`)")

   except KeyError or errors.ClientException:
      print(f" > Exception occured processing play command: {traceback.print_exc()}")
      return await interaction.followup.send("Not connected to a channel. Use **/join** first!")
   except Exception:
      print(f" > Exception occured processing search command: {traceback.print_exc()}")
      return await interaction.followup.send("Can not start Playback.")


# Function for next track
async def _init_command_next_response(interaction):
   """The function to play next track in the queue"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the next command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      # Check if Bot is connected to a channel
      if voice_clients[interaction.guild.id] != None:
         # Check if Bot is playing something and there are songs in the queue start playback of next song
         if len(queues[interaction.guild.id]) > 0:
            if voice_clients[interaction.guild.id].is_playing():
               voice_clients[interaction.guild.id].stop()
            if new_queue[interaction.guild.id] == True:
               return await interaction.followup.send(f"Start playing: **{queues[interaction.guild.id][1]['title']}** (`{queues[interaction.guild.id][1]['duration']}`)")
            else:
               return await interaction.followup.send(f"Start playing: **{queues[interaction.guild.id][0]['title']}** (`{queues[interaction.guild.id][0]['duration']}`)")
         else:
            return await interaction.followup.send("There are no queued songs")
      else:
         return await interaction.followup.send("Not connected to a channel. Use **/join** first")

   except Exception:
      print(f" > Exception occured processing next command: {traceback.print_exc()}")
      return await interaction.followup.send("Can not skip track.")


# Function to print out List of Queue
async def _init_command_queue_response(interaction):
   """The fucntion to list all queued songs"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the queue command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      queue_string = ""

      if new_queue[interaction.guild.id] == True:
         if len(queues[interaction.guild.id]) > 0:
            for i,item in enumerate(queues[interaction.guild.id]):
               if i != 0:
                  queue_string += f"{i} **{item['title']}** (`{item['duration']}`)\n"
            return await interaction.followup.send(queue_string)
         else:
            return await interaction.followup.send("No Songs in Queue")
      else:
         if len(queues[interaction.guild.id]) > 0:
            for i,item in enumerate(queues[interaction.guild.id]):
               queue_string += f"{i+1} **{item['title']}** (`{item['duration']}`)\n"
            return await interaction.followup.send(queue_string)
         else:
            return await interaction.followup.send("No Songs in Queue")

   except Exception:
      print(f" > Exception occured processing queue command: {traceback.print_exc()}")
      return await interaction.followup.send("Can not print out queued songs.")

# Function to change volume
async def _init_command_volume_response(interaction, volume):
   """The function to change volume"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the volume command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      if 0 <= volume <= 100:
         if voice_clients[interaction.guild.id].is_playing():
            volume_val[interaction.guild.id] = volume / 100
            voice_clients[interaction.guild.id].source.volume = volume_val[interaction.guild.id]
         else:
            return await interaction.followup.send(f"Bot is not playing anything.")
      else:
         return await interaction.followup.send(f"Value must be between **0-100%**")

      await interaction.followup.send(f"Changed Volume to **{volume}**%")
   except Exception:
      print(f" > Exception occured processing volume command: {traceback.print_exc()}")
      return await interaction.followup.send("Can not change Volume.")


# Function to pause
async def _init_command_pause_response(interaction):
   """The function to pause"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the pause command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      voice_clients[interaction.guild.id].pause()

      await interaction.followup.send("Pausing Playback")
   except Exception:
      print(f" > Exception occured processing pause command: {traceback.print_exc()}")
      return await interaction.followup.send("Can not pause Playback.")


# Function to resume
async def _init_command_resume_response(interaction):
   """The function to resume"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the resume command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      voice_clients[interaction.guild.id].resume()

      await interaction.followup.send("Resuming Playback")
   except Exception:
      print(f" > Exception occured processing resume command: {traceback.print_exc()}")
      return await interaction.followup.send("Can not resume Playback.")


# Function to stop
async def _init_command_stop_response(interaction):
   """The function to stop"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the stop command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      # Delete list for the queued songs
      queues[interaction.guild.id] = []

      # Set the flag to False to indicate that the bot should not continue playing songs
      should_continue[interaction.guild.id] = False

      voice_clients[interaction.guild.id].stop()

      await interaction.followup.send("Stop Playback")
   except Exception:
      print(f" > Exception occured processing stop command: {traceback.print_exc()}")
      return await interaction.followup.send("Can not stop Playback.")


# Function to disconnect
async def _init_command_disconnect_response(interaction):
   """The function to disconnect"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the disconnect command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      # Delete list for the queued songs
      queues[interaction.guild.id] = []

      # Set the flag to False to indicate that the bot should not continue playing songs
      should_continue[interaction.guild.id] = False

      # Disconnect from the Channel
      if voice_clients[interaction.guild.id].is_playing():
         voice_clients[interaction.guild.id].stop()
      await voice_clients[interaction.guild.id].disconnect()

      await interaction.followup.send("Disconnected")
   except Exception:
      print(f" > Exception occured processing disconnect command: {traceback.print_exc()}")
      return await interaction.followup.send(f"Can not disconnect from channel {interaction.user.voice.channel.name}.")


# Function to send donation response
async def _init_command_donation_response(interaction):
   """The function to send donation link"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the donation command.")

      donationlink = config_data.get("donation_link")

      await interaction.response.send_message("\n".join([
         f"Hey {interaction.user.mention}, thank you for considering donating to support my work!",
         f"You can donate via PayPal using {donationlink} :heart_hands:"]))
   except Exception:
      print(f" > Exception occured processing donation command: {traceback.print_exc()}")
      return await interaction.response.send_message(f"Can not process donation command. Please contact <@164129430766092289> when this happened.")

#########################################################################################
# Commands
#########################################################################################

# Command to check help
@client.tree.command()
async def help(interaction: Interaction):
   """Help Command for Music Bot"""
   await _init_command_help_response(interaction)

# Command to join a users channel
@client.tree.command()
async def join(interaction: Interaction):
   """A command to join a users channel"""
   await _init_command_join_response(interaction)

# Command to start playing using youtube url
@client.tree.command()
async def play(interaction: Interaction, url: str):
   """A command to start playing audio using youtube url"""
   await _init_command_play_response(interaction, url)

# Command to start playing by searching youtube
@client.tree.command()
async def search(interaction: Interaction, search: str):
   """A command to search youtube"""
   await _init_command_search_response(interaction, search)

# Command to play next track
@client.tree.command()
async def next(interaction: Interaction):
   """A command to play next track in queue"""
   await _init_command_next_response(interaction)

# Command to play next track
@client.tree.command()
async def skip(interaction: Interaction):
   """A command to play next track in queue"""
   await _init_command_next_response(interaction)

# Command to check queue
@client.tree.command()
async def queue(interaction: Interaction):
   """A command to check the current queued songs"""
   await _init_command_queue_response(interaction)

# Command to check queue
@client.tree.command()
async def list(interaction: Interaction):
   """A command to check the current queued songs"""
   await _init_command_queue_response(interaction)

# Command to change volume
@client.tree.command()
async def volume(interaction: Interaction, volume: float):
   """A command to change volume"""
   await _init_command_volume_response(interaction, volume)

# Command to pause
@client.tree.command()
async def pause(interaction: Interaction):
   """A command to pause"""
   await _init_command_pause_response(interaction)

# Command to resume
@client.tree.command()
async def resume(interaction: Interaction):
   """A command to resume"""
   await _init_command_resume_response(interaction)

# Command to stop
@client.tree.command()
async def stop(interaction: Interaction):
   """A command to stop"""
   await _init_command_stop_response(interaction)

# Command to disconnect
@client.tree.command()
async def disconnect(interaction: Interaction):
   """A command to disconnect"""
   await _init_command_disconnect_response(interaction)

# Command to leave
@client.tree.command()
async def leave(interaction: Interaction):
   """A command to leave"""
   await _init_command_disconnect_response(interaction)

# Command for Donation
@client.tree.command()
async def donate(interaction: Interaction):
   """A command to send donation link"""
   await _init_command_donation_response(interaction)

#########################################################################################
# Server Start
#########################################################################################

# Runs the bot with the token you provided
client.run(token)
