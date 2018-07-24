# DiscordBot 3.0
# Author: Carl Brockwell
# Date: October 2017 - June 2018
import asyncio
import discord
import logging
import datetime
import time
from discord.ext import commands
from flask import Flask

app = Flask(__name__)

# Setup basic log/debug messages
logging.basicConfig(level=logging.INFO)

# Global variable, objects setup"
TOKEN = input("Welcome to DiscordBot\rPlease enter your bot security token:")
channelId = input("Please enter the channel ID you want DiscordBot to post notifications to:")
general_channel = discord.Object(channelId)
bot_description = "[Enter your bot description here]"
bot = commands.Bot(command_prefix='!', description=bot_description)
bot_version_number = '3.1'
purge_time_secs = 259200
non_game_reference_list = ["abc123", "launcher"]  # Reference list on apps to ignore/exclude as a game being played.
halt = False


@app.route('/')
# MAINTENANCE ROUTINE(S)
# Routine purge activity to clear message in channel every n seconds.
async def purge_background_task():
    await bot.wait_until_ready()
    channel = bot.get_channel(channelId)

    while not bot.is_closed:
        try:
            await bot.purge_from(channel, limit=100)
            await bot.send_message(channel, "Message purge on channel:" + channel.mention + " completed.")
            await asyncio.sleep(purge_time_secs)  # task runs every n seconds
        except:  # Catch exception when purge exceeds the number of messages that can be deleted due to their age.
            await asyncio.sleep(purge_time_secs)  # task runs every n seconds


# First instance that the function finds a word/phrase is contained within the 'non-game' name list return true to
# ensure that this is not considered a real game but a game launcher or pre-app of some kind.
async def check_non_game_reference_list(after):
    for game_name in non_game_reference_list:
        if str(game_name).lower() in str(after.game).lower():
            print("Notice: non game reference identified - reference item:{0} ¦ game name: {1}".format(str(game_name),
                                                                                                       str(after.game)))
            return True
        else:
            continue
    else:
        return False


# Get free channel
def get_free_channel(all_channels):
    for channel in all_channels:
        channel_members = channel.voice_members
        if str(channel.type) == 'voice' and channel_members == [] and channel.name != "AFK":
            free_channel = channel
            return free_channel
        continue


# EVENTS

# Upon bot successfully connecting, print bot information into console and run background routine(s)
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print("ID: " + bot.user.id)
    print('------')

    bot.loop.create_task(purge_background_task())  # Initiate purge routine.


def is_connected(self):
    # bool : Indicates if the voice client is connected to voice."""
    return self._is_connected(self)


# When member enters voice chat for the first time after connecting, move them and the first member found playing the
#  same game (or none ) into their own channel, if they are in voice channels, else announce member joining channel.
@bot.event
async def on_voice_state_update(before, after):
    if before.voice_channel is None:  # Member is not previously connected to a voice channel.
        all_members = bot.get_all_members()
        for member in all_members:
            if str(after.game) == str(member.game) and member.name != after.name and \
                    after.voice.voice_channel is not None and member.voice.voice_channel is not None \
                    and str(member.voice.voice_channel) != "AFK":
                await bot.move_member(after, member.voice_channel)
                await bot.send_message(general_channel, "{0} has been moved to {1} with {2}, as they are playing: {3}."
                                       .format(after.mention, member.voice_channel.mention, member.mention,
                                               str(member.game)))
                break

    # if after.voice_channel is not None:
    #   await bot.send_message(general_channel, after.mention + " has joined: " + str(after.voice_channel.mention),
    #                         tts=True)


@bot.event
# Recognise a member has had a status change
async def on_member_update(before, after):
    # Game status check and announce it.
    if before.game != after.game:
        if await check_non_game_reference_list(before) is False and after.game is None:
            game_update_string = after.mention + " has stopped playing: " + str(before.game)
            await bot.send_message(general_channel, game_update_string)
        else:
            if await check_non_game_reference_list(after) is False and after.game is not None:
                game_update_string = after.mention + " is now playing: " + str(after.game)
                await bot.send_message(general_channel, game_update_string)

            # Player game status changed. compile server members and channels and create variables.
            all_channels = bot.get_all_channels()
            all_members = bot.get_all_members()
            game_list = []

            # If a member starts playing the same game as another member in a separate channel on the server,
            # move the latest member to the same channel
            for member in all_members:
                if str(member.game).lower() == str(after.game).lower() and after.game is not None \
                        and after.voice_channel != member.voice_channel and member.voice_channel != "AFK":
                    await bot.move_member(after, member.voice_channel)
                break

            # Providing member is connected to a valid voice channel, perform checks to identify members
            # playing the same game
            if after.voice_channel is not None and after.voice_channel != "AFK":
                channel = after.voice_channel
                voice_channel_members = channel.voice_members

                # Iterate through members in voice channel of updating member and if a different member
                # is also playing the same game, add to the duplicating game list.
                for member in voice_channel_members:
                    for member_check in voice_channel_members:
                        if member.game == member_check.game and member.name != member_check.name and \
                                member.game is not None and member_check is not None and \
                                str(member.game).lower() not in game_list:
                            game_list.append(str(member.game).lower())
                            print("game list appended")  # Log task for debugging
                            print(game_list)  # Log task for debugging

                # If there are at least 2 instances now where more than 1 member is playing the same game
                # e.g. 2 members playing game A and 2 members playing game B,
                # move the latest member pair to a new channel.
                # This ensures there are no cross conversations between games but ensures individual members who
                # aren't playing a game or are playing a game on their own, are free to remain in channel or move
                # themselves at will.
                if len(game_list) >= 2:
                    print("game list larger than 2, criteria met")  # Log task for debugging
                    print(game_list)  # Log task for debugging
                    await bot.send_message(general_channel, "Warning, members playing the game: " + str(after.game) +
                                           " will be moved to another channel in 10 seconds",
                                           tts=True)  # Announce the player pair names moved in general channel.
                    time.sleep(15)  # Interval between jobs in seconds +5 secs to account for message announcement time.
                    free_channel = get_free_channel(all_channels)  # Get the next available free voice channel
                    await bot.move_member(after, free_channel)  # Move triggering member.
                    members_moved_text = str(after.mention) + ", "  # Variable for announcement text
                    for member in voice_channel_members:  # For each member in the voice channel
                        if str(member.game) == str(after.game):  # if member game matches the triggering member game
                            await bot.move_member(member, free_channel)  # Move member.
                            members_moved_text += member.mention + ", "  # Add members to announcement text.
                    await bot.send_message(general_channel, members_moved_text + "moved to: " + free_channel.mention,
                                           tts=True)  # Announce the player pair names moved in general channel.

    # Member status check for nickname change and announce it in general chat. Note: 'if-else' condition handling
    # in place to accommodate the fact that nickname returns a noneType if it matches the member's server name.
    if before.nick != after.nick:
        nickname_update_string = before.mention + " has an updated nickname "
        if before.nick is None:
            nickname_update_string += "from: '" + before.name + "'"
        else:
            nickname_update_string += "from: '" + before.nick + "'"
        if after.nick is None:
            nickname_update_string += " to: '" + after.name + "'"
        else:
            nickname_update_string += " to: '" + after.nick + "'"
        await bot.send_message(general_channel, nickname_update_string)

    # Check member status change and announce it
    if str(before.status) != str(after.status) and after.id != "97028501449748480":
        await bot.send_message(general_channel, after.mention + " is " + str(after.status), tts=True)
        print(after.name + " is " + str(after.status) + " " + str(datetime.datetime.now()))  # Log task for debugging


# COMMANDS

# @bot.command(pass_context=True)
# async def halt():
# return

if __name__ == '__main__':
    bot.run(TOKEN)
