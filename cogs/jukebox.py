from discord.ext import commands
import re, discord, yt_dlp, asyncio, random, functools

def jukebox_channel_only(func):
    @functools.wraps(func)
    async def wrapper(self, *args):
        if args[0].channel.name != "jukebox-spam":
            return
        print(f"Channel check passed for {args[0].channel.name}", flush=True)
        return await func(self, *args)
    print("Jukebox channel only decorator defined", flush=True)
    return wrapper
    
class JukeBox(commands.Cog):
    def __init__(self, bot, info_channel):
        self.bot = bot
        self.channel = info_channel
        self.playlist = []
        self.voice_instance = None
        print(f"Jukebox initialized with {info_channel.name} channel", flush=True)
        self.bot.loop.create_task(self.people_check())
        self.bot.loop.create_task(self.info_channel())
        self.bot.loop.create_task(self.idle_timer())

    @commands.command(name="play")
    @jukebox_channel_only
    async def play(self, ctx):
        print(f"Play command received in {ctx.channel.name} channel", flush=True)
        if not ctx.author.voice:
            return await ctx.send("You are not in a voice channel.")
        print(f"{ctx.author.name} is not in a voice channel", flush=True)
        if self.voice_instance and self.voice_instance.channel.id != ctx.author.voice.channel.id:
            return await ctx.send("You are not in the same voice channel as me.")
        print(f"User {ctx.author.name} is in wrong voice channel", flush=True)
        if not self.voice_instance:
            self.voice_instance = await ctx.author.voice.channel.connect()
        print(f"Connected to voice channel for user {ctx.author.name}", flush=True)
        if not self.valid_request(ctx):
            return await ctx.send("Invalid request. Please try again.")
        print(f"User {ctx.author.name} has a valid YouTube link", flush=True)
        await self.process_request(ctx)

    async def people_check(self):
        while True:
            print(f"People check running for Jukebox in channel {self.channel.name}", flush=True)
            if self.voice_instance and len(self.voice_instance.channel.members) < 2:
                self.playlist = []
                await self.voice_instance.disconnect()
                self.voice_instance = None
                print("User count in voice channel is low, clearing playlist", flush=True)
            print(f"People check ran for Jukebox in channel {self.channel.name}", flush=True)
            await asyncio.sleep(10)

    async def info_channel(self):
        print(f"Info channel running for Jukebox in {self.channel.name} channel", flush=True)
        await self.channel.purge()
        # Initial embed when starting up the Jukebox
        embed = discord.Embed(
            title="Booting up Jukebox",
            color=discord.Color.blue()
        )
        message_instance = await self.channel.send(embed=embed)

        last_playing_message = "No song playing"
        last_playlist = ""
        last_image = "https://i.imgur.com/AJpM3Oc.jpeg"  # Default image
        currently_playing_message = "No song playing"

        while True:
            length = len(self.playlist)-1
            outof = min(length, 10)  # Adjust max songs displayed
            playlist = ""
            # Construct the playlist string
            for i, song in enumerate(self.playlist[1:10], 1):
                time = self.format_time(song['duration'])
                # Format the song info with fixed-width fields
                playlist += f"`{i:2}. {song['artist'][:13]:<13} - {song['song_name'][:26]:<26} - {time}`\n"

            if self.playlist != []:
                # Format currently playing song
                time = self.format_time(self.playlist[0]['duration'])
                if self.voice_instance.is_paused() == True:
                    pp = "Paused"
                else:
                    pp = "Playing"
                currently_playing_message = (
                    f"{pp}: {self.playlist[0]['artist']} - "
                    f"{self.playlist[0]['song_name']} - {time}"
                )
                image_link = f"https://img.youtube.com/vi/{self.playlist[0]['id']}/maxresdefault.jpg"

                # Check if there are changes to update the embed
                if (last_playing_message != currently_playing_message or
                    last_playlist != playlist or
                    last_image != image_link):

                    # Create a new embed for currently playing
                    embed = discord.Embed(title=currently_playing_message, color=discord.Color.blue())
                    embed.set_image(url=image_link)
                    embed.add_field(name=f"Song Queue {outof}/{length}", value=playlist, inline=False)  # Add the playlist as a field

                    # Update the last states
                    last_playing_message = currently_playing_message
                    last_playlist = playlist
                    last_image = image_link

                    # Send updated embed
                    buttons = ["Play", "Pause", "Skip", "Shuffle", "Nuke"]
                    view = JukeboxView(buttons, self, self.channel)
                    await message_instance.edit(embed=embed, view=view)

            else:
                # Default case when no song is playing
                embed = discord.Embed(
                    color=discord.Color.blue()
                )
                embed.set_image(url="https://i.imgur.com/AJpM3Oc.jpeg")
                embed.add_field(name="" ,value="To add songs, go to #jukebox-spam channel and type `!play <yt / yt music link or search for a song >`", inline=False)
                embed.set_footer(text="We have Youtube Premium at home.")
                embed.add_field(name=f"Song Queue 0/0", value="No songs in the playlist.", inline=False)  # Default playlist message

                # Only update if the message is not already showing this embed
                if last_playing_message != "No song playing at the moment.":
                    last_playing_message = "No song playing at the moment."
                    await message_instance.edit(embed=embed, view=None)

            print(f"Info channel check ran for Jukebox in {self.channel.name} channel", flush=True)
            await asyncio.sleep(3)

    async def idle_timer(self):
        while True:
            idle_time = 0
            if self.voice_instance is not None:
                if not self.voice_instance.is_playing():
                    idle_time += 1
                    if idle_time > 10:
                        await self.voice_instance.disconnect()
                        self.voice_instance = None
                        print("Idle timer detected no audio playing, clearing voice instance", flush=True)
                else:
                    idle_time = 0
            else:
                idle_time = 0
            print(f"Idle timer ran for Jukebox in channel {self.channel.name}", flush=True)
            await asyncio.sleep(30)

    def valid_request(self, ctx):
        regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/'
        request = ctx.message.content.split("!play ", 1)[1]
        print(f"Checking if {request} is a valid YouTube link", flush=True)
        return bool(re.match(regex,request)) or not request.startswith(("http://", "https://", "www."))
    
    def format_time(self, duration):
        minutes = int(duration / 60)
        seconds = f"{int(duration % 60):02d}"
        print(f"Formatting time for song with duration {duration} seconds", flush=True)
        return f"{minutes}:{seconds}"

    async def search_youtube(self, ctx):
        query = ctx.message.content.split("!play ", 1)[1]
        search_query = f"ytsearch5:music {query}"
        info = await self.get_dict(search_query)
        if not info['entries']:
            await ctx.reply("No songs found.")
            return None
        songs = []
        for entry in info['entries']:
            song_info = self.get_song_info(entry)
            songs.append(song_info)
        embeds = []
        for i, song in enumerate(songs[:5], start=1):
            embed = discord.Embed(color=0x3b88c3)
            duration = self.format_time(song['duration'])
            song_name = f"{song['song_name']}"
            artist_name = f"`{i}. {song['artist'][:43]:<{43}}{duration[:6]:<{6}}`"
            embed.add_field(name=artist_name, value=song_name, inline=False)
            embed.set_thumbnail(url=f"https://img.youtube.com/vi/{song['id']}/maxresdefault.jpg")
            embeds.append(embed)
        view = JukeboxView([str(i) for i in range(1, 6)], self, ctx)
        msg = await ctx.reply(embeds=embeds, view=view, delete_after=15)
        print(f"Sending search results to channel {ctx.channel.name}", flush=True)
        await view.wait()
        if view.reply is not None:
            chosen_song = songs.pop(int(view.reply) - 1)
            await msg.delete()
            return f"https://www.youtube.com/watch?v={chosen_song['id']}"
        else:
            print("No song was chosen from search results", flush=True)
            await msg.delete()

    async def process_request(self, ctx):
        request = ctx.message.content.split("!play ", 1)[1]
        if not request.startswith(("http://", "https://", "www.")):
            request = await self.search_youtube(ctx)
        print(f"Processing YouTube link {request} for user {ctx.author.name}", flush=True)
        try:
            info_dict = await self.get_dict(request)
            if 'entries' in info_dict:
                view = JukeboxView(["Yes", "No"], self, ctx)
                content = (f"Playlist detected with {len(info_dict['entries'])} songs. Queue em'?")
                await ctx.reply(content=content, view=view, delete_after=10)
                await view.wait()
                if view.boolean:
                    self.playlist.extend([self.get_song_info(entry) for entry in info_dict['entries']])
                    if not self.voice_instance.is_playing():
                        await self.play_audio()
                    await ctx.reply(f"{len(info_dict['entries'])} songs added to queue.")
            else:
                self.playlist.append(self.get_song_info(info_dict))
                await ctx.reply(f"Added song to playlist. {self.playlist[-1]['artist']} - {self.playlist[-1]['song_name']}")
        except Exception as e:
            print(e, flush=True)
            return await ctx.send("Something went wrong. Please try again.")
        if self.voice_instance.is_playing() or self.voice_instance.is_paused():
            return
        else:
            await self.play_audio()

    def get_song_info(self,entry):
        return {
            'artist': entry.get('uploader'),
            'song_name': entry.get('title'),
            'url': entry.get('url'),
            'id': entry.get('id'),
            'duration': entry.get('duration')
        }

    async def get_dict(self, request):
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'extract_flat': 'in_playlist',
            }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return await asyncio.to_thread(ydl.extract_info, request, download=False)

    async def after_playback(self, error):
        if error:
            print(error, flush=True)
        self.playlist.pop(0)
        if self.playlist:
            await self.play_audio()
        else:
            self.voice_instance.stop()
    async def play_audio(self):
        request = self.playlist[0]['url']
        info_dict = await self.get_dict(request)
        song_url = info_dict['url']
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        source = discord.FFmpegPCMAudio(song_url, **ffmpeg_options)
        self.voice_instance.volume = 0.8
        self.voice_instance.play(source, after=lambda e: self.bot.loop.create_task(self.after_playback(e)))

async def setup(bot, info_channel):
    await bot.add_cog(JukeBox(bot, info_channel))

class JukeboxView(discord.ui.View):
    def __init__(self, buttons, jukebox, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.jukebox = jukebox
        self.boolean = None
        self.reply = None

        for button_label in buttons:
            style = {
                "Yes": discord.ButtonStyle.green,
                "Play": discord.ButtonStyle.green,
                "No": discord.ButtonStyle.red,
                "Pause": discord.ButtonStyle.gray,
                "Skip": discord.ButtonStyle.blurple,
                "Nuke": discord.ButtonStyle.red,
                "Shuffle": discord.ButtonStyle.blurple,
            }.get(button_label, discord.ButtonStyle.blurple)

            button = discord.ui.Button(label=button_label, custom_id=button_label, style=style)
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        if custom_id in ("Yes", "No"):
            if interaction.user == self.ctx.author:
                self.boolean = custom_id == "Yes"
                await interaction.response.defer()
                self.stop()
        elif custom_id in ("Pause", "Play"):
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_instance.channel:
                self.jukebox.voice_instance.pause() if custom_id == "Pause" else self.jukebox.voice_instance.resume()
                await interaction.response.defer()
        elif custom_id in ("Nuke", "Shuffle", "Skip"):
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_instance.channel:
                if custom_id == "Nuke":
                    self.jukebox.playlist = []
                    self.jukebox.voice_instance.stop()
                elif custom_id == "Shuffle":
                    import random
                    self.jukebox.playlist[1:] = random.sample(self.jukebox.playlist[1:], len(self.jukebox.playlist) - 1)
                elif custom_id == "Skip":
                    self.jukebox.voice_instance.stop()
                await interaction.response.defer()
        elif custom_id.isdigit():
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_instance.channel:
                await interaction.response.defer(ephemeral=True)
                self.reply = custom_id
                self.stop()


