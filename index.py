#!/usr/bin/env python3
# Imports
import os
import sys
import json
import asyncio
import requests
import traceback
from youtube_dl import YoutubeDL
from discord import app_commands, Intents, Client, Interaction, Status, Game, FFmpegPCMAudio

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
yt_dl_opts = {'format': 'bestaudio/best'}
ytdl = YoutubeDL(yt_dl_opts)

# Configurations for FFMPEG
ffmpeg_options = {'options': "-vn"}

# Variable for multiple voice clients in different guilds
voice_clients = {}

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

    await client.change_presence(status=Status.online, activity=Game(name="Ready for The Imperial March!"))

#########################################################################################
# Functions
#########################################################################################

# Function to join channel
async def _init_command_join_response(interaction):
   """The function to join a channel"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the join command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      # Connect to Users Channel
      voice_client = await interaction.user.voice.channel.connect()
      voice_clients[voice_client.guild.id] = voice_client

      # Write in Chat that Bot joined channel
      await interaction.followup.send(f"Joined Channel \"{interaction.user.voice.channel.name}\"")
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

      # Similar to a Thread it will run independent from the program. Sent command will only
      # effect current user session
      loop = asyncio.get_event_loop()
      data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

      song = data['url']
      player = FFmpegPCMAudio(song, **ffmpeg_options)

      if voice_clients[interaction.guild.id] != None:
         voice_clients[interaction.guild.id].play(player)
      else:
         return await interaction.followup.send("Not connected to a channel. Use /join first")

      await interaction.followup.send(f"Start playing: {url}")

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
      data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]['formats'][0])

      song = data['url']
      player = FFmpegPCMAudio(song, **ffmpeg_options)

      if voice_clients[interaction.guild.id] != None:
         voice_clients[interaction.guild.id].play(player)
      else:
         return await interaction.followup.send("Not connected to a channel. Use /join first")

      await interaction.followup.send(f"Start playing: \"{search}\"")

   except Exception:
      print(f" > Exception occured processing search command: {traceback.print_exc()}")
      return await interaction.followup.send("Can not start Playback.")


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
      return await interaction.folloup.send("Can not pause Playback.")


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
      return await interaction.folloup.send("Can not resume Playback.")


# Function to stop
async def _init_command_stop_response(interaction):
   """The function to stop"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the stop command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      voice_clients[interaction.guild.id].stop()

      await interaction.followup.send("Stop Playback")
   except Exception:
      print(f" > Exception occured processing stop command: {traceback.print_exc()}")
      return await interaction.folloup.send("Can not stop Playback.")


# Function to disconnect
async def _init_command_disconnect_response(interaction):
   """The function to disconnect"""
   try:
      # Respond in the console that the command has been ran
      print(f"> {interaction.guild} : {interaction.user} used the disconnect command.")

      # Tell Discord that request takes some time
      await interaction.response.defer()

      await voice_clients[interaction.guild.id].disconnect()

      await interaction.followup.send("Disconnected")
   except Exception:
      print(f" > Exception occured processing disconnect command: {traceback.print_exc()}")
      return await interaction.folloup.send(f"Can not disconnect from channel {interaction.user.voice.channel.name}.")

#########################################################################################
# Commands
#########################################################################################

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

#########################################################################################
# Server Start
#########################################################################################

# Runs the bot with the token you provided
client.run(token)
