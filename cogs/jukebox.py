from discord.ext import commands
import re, discord, yt_dlp, asyncio, random, functools

def jukebox_channel_only(func):
    @functools.wraps(func)
    async def wrapper(self, *args):
        if args[0].channel.name != "jukebox-spam":
            return
        return await func(self, *args)
    return wrapper

class Jukebox(commands.Cog):
    def __init__(self, bot, channel):
        self.channel = channel
        self.bot = bot
        self.playlist = []
        self.voice_instance = None
        self.voice_id = None
        self.currently_playing = None
        self.bot.loop.create_task(self.info_channel())
        self.bot.loop.create_task(self.people_check())
    
    @commands.command(name="join")
    @jukebox_channel_only
    async def join(self, ctx):
        # Check if the user is in a voice channel
        if ctx.author.voice is None:
            await ctx.send("You are not connected to a voice channel.")
            return
        voice_channel = ctx.author.voice.channel
        # Check if the bot is already in the same channel
        if self.voice_instance is not None and self.voice_id == voice_channel:
            await ctx.send("You're already in the same voice channel.")
            return
        # If the bot is already in a channel, move to the new channel
        if self.voice_instance is not None:
            await self.voice_instance.move_to(voice_channel)
            self.voice_id = voice_channel
            await ctx.send(f"Moved to {voice_channel.name}.")
        else:
            # Connect to the new channel
            self.voice_instance = await voice_channel.connect()
            self.voice_id = voice_channel
            await ctx.send(f"Connected to {voice_channel.name}.")

    @commands.command(name="leave")
    @jukebox_channel_only
    async def leave(self, ctx):
        voice_channel = ctx.author.voice.channel
        if self.voice_id != voice_channel:
            await ctx.send("You're not in the same voice channel.")
            return
        if self.voice_instance is not None:
            self.voice_instance.stop()
            await self.voice_instance.disconnect()
            self.voice_instance = None
            self.voice_id = None
            self.playlist = []
            await ctx.send("Disconnected from voice channel.")
    
    @commands.command(name="play")
    @jukebox_channel_only
    async def play(self, ctx):
        try:
            voice_channel = ctx.author.voice.channel
        except:
            await ctx.send("You are not connected to a voice channel.")
            return
        if voice_channel != self.voice_id and self.voice_id is not None:
            await ctx.send("You are not in the same voice channel. Join the same voice channel as the bot or type !join.")
            return
        elif self.voice_id is None:
            self.voice_instance = await voice_channel.connect()
            self.voice_id = voice_channel
            self.bot.loop.create_task(self.afk_timer())

        request = ctx.message.content.split("!play ", 1)[1]
        youtube_regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/'
        if re.match(youtube_regex, request):
            await self.process_request(ctx, request)
        elif request.startswith(("http://", "https://", "www.")):
            await ctx.send("Only YouTube links are allowed.")
        else:
            await self.search_youtube(ctx, request)

    async def people_check(self):
        while True:
            if self.voice_instance is not None and self.voice_id is not None:
                memebers_in_voice = len(self.voice_id.members)
                if memebers_in_voice < 2:
                    self.playlist = []
                    self.currently_playing = None
                    self.voice_instance.stop()
                    await self.voice_instance.disconnect()
                    self.voice_instance = None
                    self.voice_id = None
            await asyncio.sleep(60)

    async def search_ydl(self, query):
        max_results = 5
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"ytsearch{max_results}:music {query}"
            info = await asyncio.to_thread(ydl.extract_info, search_query, download=False)
            return info

    async def search_youtube(self, ctx, query):
        info = await self.search_ydl(query)
        search_embeds = []
        songs = []
        for i, entry in enumerate(info['entries'], start=1):
            song_info = {
                'artist': entry.get('uploader'),
                'song_name': entry.get('title'),
                'url': entry.get('url'),
                'id': entry.get('id'),
                'duration': entry.get('duration')
            }
            minutes = int(song_info["duration"] / 60)
            seconds = f"{int(song_info['duration'] % 60):02d}"
            songs.append(song_info)
            # Define max lengths
            max_title_length = 43  # Increase title length by 5
            max_description_length = 38  # Total length for description

            # Calculate duration length to adjust title formatting
            duration_length = len(f"{minutes}:{seconds}")  # Get the length of the formatted duration
            artist_display = song_info['artist'][:max_title_length - duration_length - 15]  # Adjust for index and duration length

            # Create the title with maximum character space used
            title = f"`{i:2}. {artist_display:<{max_title_length - duration_length - 15}}   {minutes}:{seconds}`"

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
            await self.process_request(ctx, chosen_song['url'])

    async def process_request(self, ctx, video_url):
        self.ctx = ctx
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'extract_flat': 'in_playlist', 
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = await asyncio.to_thread(ydl.extract_info, video_url, download=False)
                if 'entries' in info_dict:
                    view = JukeboxView(["Yes", "No"], self, ctx)
                    content = (f"Playlist detected with {len(info_dict['entries'])} songs. Queue em'?")
                    await ctx.reply(content=content, view=view, delete_after=10)
                    await view.wait() 
                    if view.boolean:
                        for entry in info_dict['entries']:
                            song_info = {
                                'artist': entry.get('uploader'),
                                'song_name': entry.get('title'),
                                'url': entry.get('url'),
                                'id': entry.get('id'),
                                'duration': entry.get('duration')
                            }
                            self.playlist.append(song_info)
                            if self.voice_instance.is_playing() == False:
                                self.currently_playing = self.playlist.pop(0)
                                self.play_audio(self.currently_playing['url'])
                        await ctx.reply(f"Added {len(info_dict['entries'])} songs to the queue.")

                else:
                    song_info = {
                        'artist': info_dict.get('uploader', 'Unknown Artist'),
                        'song_name': info_dict.get('title', 'Unknown Title'),
                        'url': f"{video_url}",
                        'id': info_dict.get('id'),
                        'duration': info_dict.get('duration')
                    }
                    self.playlist.append(song_info)
                    await ctx.reply(f"Added song to playlist. {song_info['artist']} - {song_info['song_name']}")
        except Exception as e:
            print(f"Failed to extract audio info: {e}")
        if self.voice_instance.is_playing() == True:
            return
        self.currently_playing = self.playlist.pop(0)
        self.play_audio(self.currently_playing['url'])

    def play_audio(self, url):
        ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'extract_flat': 'in_playlist', 
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)
                song_url = video_info['url']
        except Exception as e:
            print(f"Failed to extract audio info: {e}")
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        source = discord.FFmpegPCMAudio(song_url, **ffmpeg_options)
        self.voice_instance.volume = 0.8
        self.voice_instance.play(source, after=lambda e: self.after_playback(e))
    
    def after_playback(self, error):
        if error:
            print(f"Error occurred: {error}")
        if self.voice_instance.is_playing() == True:
            return
        if self.playlist:
            self.currently_playing = self.playlist.pop(0)  
            print(self.currently_playing)
            self.play_audio(self.currently_playing['url'])  
        else:
            self.bot.loop.create_task(self.afk_timer())
            self.currently_playing = None
            print("Playback has ended, and there are no more songs in the playlist.")

    async def afk_timer(self):
        i = 1
        while True:
            if self.voice_instance is None:
                break
            if self.voice_instance.is_playing() == False:
                i += 1
                if i > 10:
                    await self.voice_instance.disconnect()
                    self.voice_instance = None
                    self.voice_id = None
                    break
                await asyncio.sleep(60)
            else:
                break

    async def info_channel(self):
        channel = self.channel
        print(channel)
        await channel.purge()

        # Initial embed when starting up the Jukebox
        embed = discord.Embed(
            title="Booting up Jukebox",
            color=discord.Color.blue()
        )
        message_instance = await channel.send(embed=embed)

        last_playing_message = "No song playing"
        last_playlist = ""
        last_image = "https://i.imgur.com/AJpM3Oc.jpeg"  # Default image
        currently_playing_message = "No song playing"

        while True:
            length = len(self.playlist)
            outof = min(length, 10)  # Adjust max songs displayed
            playlist = ""
            # Construct the playlist string
            for i, song in enumerate(self.playlist[:10], 1):
                minutes = int(song['duration'] / 60)
                seconds = f"{int(song['duration'] % 60):02d}"
                # Format the song info with fixed-width fields
                playlist += f"`{i:2}. {song['artist'][:13]:<13} - {song['song_name'][:26]:<26} - {minutes}:{seconds}`\n"

            if self.currently_playing is not None:
                # Format currently playing song
                minutes = int(self.currently_playing['duration'] / 60)
                seconds = f"{int(self.currently_playing['duration'] % 60):02d}"
                if self.voice_instance.is_paused() == True:
                    pp = "Paused"
                else:
                    pp = "Playing"
                currently_playing_message = (
                    f"{pp}: {self.currently_playing['artist']} - "
                    f"{self.currently_playing['song_name']} - {minutes}:{seconds}"
                )
                image_link = f"https://img.youtube.com/vi/{self.currently_playing['id']}/maxresdefault.jpg"

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
                    view = JukeboxView(buttons, self, channel)
                    await message_instance.edit(embed=embed, view=view)
            
            else:
                # Default case when no song is playing
                embed = discord.Embed(
                    color=discord.Color.blue()
                )
                embed.set_image(url="https://i.imgur.com/AJpM3Oc.jpeg")
                embed.add_field(name="" ,value="To add songs, go to #jukebox-spam channel and type `!play <youtube or youtube music link>`", inline=False)
                embed.set_footer(text="We have Youtube Premium at home.")
                embed.add_field(name=f"Song Queue {outof}/{length}", value="No songs in the playlist.", inline=False)  # Default playlist message
                
                # Only update if the message is not already showing this embed
                if last_playing_message != "No song playing at the moment.":
                    last_playing_message = "No song playing at the moment."
                    await message_instance.edit(embed=embed, view=None)

            await asyncio.sleep(3)

async def setup(bot, channel):
    await bot.add_cog(Jukebox(bot, channel))

class JukeboxView(discord.ui.View):
    def __init__(self, buttons, jukebox, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.jukebox = jukebox
        self.boolean = None
        self.reply = None
        for button_label in buttons:
            if button_label == "Yes":
                style = discord.ButtonStyle.green
            elif button_label == "Play":
                style = discord.ButtonStyle.green
            elif button_label == "No":
                style = discord.ButtonStyle.red
            elif button_label == "Pause":
                style = discord.ButtonStyle.gray
            elif button_label == "Skip":
                style = discord.ButtonStyle.blurple
            elif button_label == "Skip All":
                style = discord.ButtonStyle.red
            elif button_label == "Shuffle Queue":
                style = discord.ButtonStyle.blurple
            else:
                style = discord.ButtonStyle.blurple  
            button = discord.ui.Button(label=button_label, custom_id=button_label, style=style)
            button.callback = self.button_callback 
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        if interaction.data["custom_id"] == "Yes":
            if interaction.user == self.ctx.author:
                self.boolean = True
                await interaction.response.send_message("Adding songs to queue... this takes a sec depending on how big the playlist is.", ephemeral=True, delete_after=5)
                self.stop()
        elif interaction.data["custom_id"] == "No":
            if interaction.user == self.ctx.author:
                self.boolean = False
                await interaction.response.send_message("No songs added to queue.", ephemeral=True, delete_after=5)
                self.stop()
            return interaction.user,False
        elif interaction.data["custom_id"] == "Pause":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                if self.jukebox.voice_instance.is_paused():
                    return
                self.jukebox.voice_instance.pause()
                await interaction.response.send_message("JankBot paused.", delete_after=5, ephemeral=True)
                self.jukebox.bot.loop.create_task(self.afk_timer())
            else:
                await interaction.response.send_message("We are not in the same voice channel.", ephemeral=True, delete_after=5)
        elif interaction.data["custom_id"] == "Play":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                if self.jukebox.voice_instance.is_playing():
                    return
                self.jukebox.voice_instance.resume()
                await interaction.response.send_message("Resuming JankBot.", delete_after=5)
            else:
                await interaction.response.send_message("We are not in the same voice channel.", ephemeral=True, delete_after=5)
        elif interaction.data["custom_id"] == "Next Song":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                await interaction.response.send_message("Song skipped!", delete_after=5, ephemeral=True)
                self.jukebox.voice_instance.stop()
                    
        elif interaction.data["custom_id"] == "Skip All":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                self.jukebox.playlist = []
                await interaction.response.send_message("Nuking the playlist...", delete_after=5, ephemeral=True)
                self.jukebox.voice_instance.stop()
            else:
                await interaction.response.send_message("We are not in the same voice channel.", ephemeral=True, delete_after=5)
        elif interaction.data["custom_id"] == "Shuffle Queue":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                random.shuffle(self.jukebox.playlist)
                await interaction.response.send_message("Queue shuffled!", delete_after=5, ephemeral=True)
            else:
                await interaction.response.send_message("We are not in the same voice channel.", ephemeral=True, delete_after=5)
        elif interaction.data["custom_id"] == "1":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                await interaction.response.send_message("Adding song to queue...", ephemeral=True, delete_after=5)
                self.reply = "1"
                self.stop()
        elif interaction.data["custom_id"] == "2":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                await interaction.response.send_message("Adding song to queue...", ephemeral=True, delete_after=5)
                self.reply = "2"
                self.stop()
        elif interaction.data["custom_id"] == "3":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                await interaction.response.send_message("Adding song to queue...", ephemeral=True, delete_after=5)
                self.reply = "3"
                self.stop()
        elif interaction.data["custom_id"] == "4":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                await interaction.response.send_message("Adding song to queue...", ephemeral=True, delete_after=5)
                self.reply = "4"
                self.stop()
        elif interaction.data["custom_id"] == "5":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                await interaction.response.send_message("Adding song to queue...", ephemeral=True, delete_after=5)
                self.reply = "5"
                self.stop()



