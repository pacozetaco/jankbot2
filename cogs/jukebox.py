from discord.ext import commands
import re, discord, yt_dlp, asyncio, random, functools

def jukebox_channel_only(func):
    @functools.wraps(func)
    async def wrapper(self, *args):
        if args[0].channel.name != "jukebox-spam":
            return
        return await func(self, *args)
    return wrapper
    
class JukeBox(commands.Cog):
    def __init__(self, bot, info_channel):
        self.bot = bot
        self.channel = info_channel
        self.playlist = []
        self.voice_instance = None
        self.bot.loop.create_task(self.people_check())
        self.bot.loop.create_task(self.info_channel())
        self.bot.loop.create_task(self.idle_timer())

    async def people_check(self):
        while True:
            if self.voice_instance and len(self.voice_instance.channel.members) < 2:
                self.playlist = []
                await self.voice_instance.disconnect()
                self.voice_instance = None
            await asyncio.sleep(10)

    async def idle_timer(self):
        while True:
            idle_time = 0
            if self.voice_instance is not None:
                if not self.voice_instance.is_playing():
                    idle_time += 1
                    if idle_time > 10:
                        await self.voice_instance.disconnect()
                        self.voice_instance = None
                else:
                    idle_time = 0
            else:
                idle_time = 0
            await asyncio.sleep(30)

    def valid_request(self, ctx):
        regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/'
        request = ctx.message.content.split("!play ", 1)[1]
        return bool(re.match(regex,request)) or not request.startswith(("http://", "https://", "www."))
    
    def format_time(self, duration):
        minutes = int(duration / 60)
        seconds = f"{int(duration % 60):02d}"
        return f"{minutes}:{seconds}"

    async def search_youtube(self, ctx):
        query = ctx.message.content.split("!play ", 1)[1]
        max_results = 5
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch{max_results}:music {query}"
            info = await asyncio.to_thread(ydl.extract_info, search_query, download=False)
            search_embeds = []
            songs = []
            for i, entry in enumerate(info['entries'], start=1):
                song_info = self.get_song_info(entry)
                format_time = self.format_time(song_info['duration'])
                songs.append(song_info)
                # Define max lengths
                max_title_length = 43  # Increase title length by 5
                max_description_length = 38  # Total length for description
                # Calculate duration length to adjust title formatting
                duration_length = len(f"{format_time}")  # Get the length of the formatted duration
                artist_display = song_info['artist'][:max_title_length - duration_length - 15]  # Adjust for index and duration length
                # Create the title with maximum character space used
                title = f"`{i:2}. {artist_display:<{max_title_length - duration_length - 15}}   {format_time}`"
                # Ensure song name takes up maximum description length
                description = f"`  {song_info['song_name'][:max_description_length]:<{max_description_length}}`"
                # Create embed with title and song name as description
                search_embed = discord.Embed(title=title, description=description, color=0x3b88c3)
                search_embed.set_thumbnail(url=f"https://img.youtube.com/vi/{song_info['id']}/maxresdefault.jpg")
                search_embeds.append(search_embed)
            max_button = len(search_embeds) + 1
            buttons = ""
            i = 1
            while i < max_button:
                buttons += str(i)
                i += 1
            view = JukeboxView(buttons, self, ctx)
            await ctx.reply(embeds=search_embeds, view=view, delete_after=15)
            await view.wait()
            if view.reply != None:
                chosen_song = songs.pop(int(view.reply)-1)
                chosen_song_url = f"https://www.youtube.com/watch?v={chosen_song['id']}"
                return chosen_song_url
    
    async def process_request(self, ctx):
        request = ctx.message.content.split("!play ", 1)[1]
        if request.startswith(("http://", "https://", "www.")) == False:
            request = await self.search_youtube(ctx)
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'extract_flat': 'in_playlist',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = await asyncio.to_thread(ydl.extract_info, request, download=False)
                if 'entries' in info_dict:
                    view = JukeboxView(["Yes", "No"], self, ctx)
                    content = (f"Playlist detected with {len(info_dict['entries'])} songs. Queue em'?")
                    await ctx.reply(content=content, view=view, delete_after=10)
                    await view.wait()
                    if view.boolean:
                        for entry in info_dict['entries']:
                            song_info = self.get_song_info(entry)
                            self.playlist.append(song_info)
                            if not self.voice_instance.is_playing():
                                self.play_audio()
                        await ctx.reply(f"{len(info_dict['entries'])} songs added to queue.")
                else:
                    song_info = self.get_song_info(info_dict)
                    song_info['url'] = info_dict.get('url')
                    self.playlist.append(song_info)
                    await ctx.reply(f"Added song to playlist. {song_info['artist']} - {song_info['song_name']}")
        except Exception as e:
            print(e, flush=True)
            return await ctx.send("Something went wrong. Please try again.")
        if self.voice_instance.is_playing() or self.voice_instance.is_paused():
            return
        else:
            self.play_audio()
        
    def get_song_info(self,entry):
        return {
            'artist': entry.get('uploader'),
            'song_name': entry.get('title'),
            'url': entry.get('url'),
            'id': entry.get('id'),
            'duration': entry.get('duration')
        }
    
    def after_playback(self, error):
        self.playlist.pop(0)
        if error:
            print(error, flush=True)
        if len(self.playlist) > 0:
            self.play_audio()
        else:
            self.voice_instance.stop()
    
    def play_audio(self):
        request = self.playlist[0]['url']
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'extract_flat': 'in_playlist',
            }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(request, download=False)
            song_url = info_dict['url']
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        source = discord.FFmpegPCMAudio(song_url, **ffmpeg_options)
        self.voice_instance.volume = 0.8
        self.voice_instance.play(source, after=lambda e: self.after_playback(e))

    async def info_channel(self):
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
                    buttons = ["Play", "Pause", "Next Song", "Skip All", "Shuffle Queue"]
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
                embed.add_field(name=f"Song Queue {outof}/{length}", value="No songs in the playlist.", inline=False)  # Default playlist message

                # Only update if the message is not already showing this embed
                if last_playing_message != "No song playing at the moment.":
                    last_playing_message = "No song playing at the moment."
                    await message_instance.edit(embed=embed, view=None)

            await asyncio.sleep(3)

    @commands.command(name="play")
    @jukebox_channel_only
    async def play(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("You are not in a voice channel.")
        if self.voice_instance and self.voice_instance.channel.id != ctx.author.voice.channel.id:
            return await ctx.send("You are not in the same voice channel as me.")
        if not self.voice_instance:
            self.voice_instance = await ctx.author.voice.channel.connect()

        if not self.valid_request(ctx):
            return await ctx.send("Invalid request. Please try again.")

        await self.process_request(ctx)

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
                "Skip All": discord.ButtonStyle.red,
                "Shuffle Queue": discord.ButtonStyle.blurple,
            }.get(button_label, discord.ButtonStyle.blurple)

            button = discord.ui.Button(label=button_label, custom_id=button_label, style=style)
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        if custom_id == "Yes":
            if interaction.user == self.ctx.author:
                self.boolean = True
                await interaction.response.send_message("Ok",ephemeral=True, delete_after=5)
                self.stop()
        elif custom_id == "No":
            if interaction.user == self.ctx.author:
                self.boolean = False
                await interaction.response.send_message("Ok",ephemeral=True, delete_after=5)
                self.stop()
        elif custom_id in ["Pause", "Play", "Skip All", "Shuffle Queue", "Next Song"]:
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_instance.channel:
                if custom_id == "Pause":
                    phrase = "Paused"
                    self.jukebox.voice_instance.pause()
                elif custom_id == "Next Song":
                    phrase = "Skipped Song"
                    self.jukebox.voice_instance.stop()
                elif custom_id == "Play":
                    phrase = "Resumed"
                    self.jukebox.voice_instance.resume()
                elif custom_id == "Skip All":
                    phrase = "Nuked Queue"
                    self.jukebox.playlist = []
                    self.jukebox.voice_instance.stop()
                elif custom_id == "Shuffle Queue":
                    phrase = "Shuffled Queue"
                    import random
                    self.jukebox.playlist[1:] = random.sample(self.jukebox.playlist[1:], len(self.jukebox.playlist) - 1)
                await interaction.response.send_message(f"{phrase}", delete_after=5, ephemeral=True)
            else:
                await interaction.response.send_message("We are not in the same voice channel.", ephemeral=True, delete_after=5)
        elif custom_id.isdigit():
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_instance.channel:
                await interaction.response.defer(ephemeral=True)
                self.reply = custom_id
                self.stop()
