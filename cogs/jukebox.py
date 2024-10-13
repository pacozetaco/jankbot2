from discord.ext import commands
import re, discord, yt_dlp, asyncio, random

class Jukebox(commands.Cog):
    def __init__(self, bot, channel):
        self.channel = channel
        self.bot = bot
        self.playlist = []
        self.voice_instance = None
        self.voice_id = None
        self.currently_playing = None
        self.bot.loop.create_task(self.info_channel())
    
    @commands.command(name="join")
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

        request = ctx.message.content.split("!play ", 1)[1]
        youtube_regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/'
        if re.match(youtube_regex, request):
            await self.process_request(ctx, request)
        elif request.startswith(("http://", "https://", "www.")):
            await ctx.send("Only YouTube links are allowed.")
        # else:
        #     await self.search_youtube(ctx, request)

    # async def search_youtube(self, ctx, request):
    #     # Implement your search logic here
    #     view = JukeboxView(["Yes", "No"], self)
    #     await ctx.send(content=f"Searching for: {request}", view=view)


    async def process_request(self, ctx, video_url):
        self.ctx = ctx
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'extract_flat': 'in_playlist',  # To extract playlist info without downloading
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=False)
                if 'entries' in info_dict:
                    view = JukeboxView(["Yes", "No"], self, ctx)
                    content = (f"Playlist detected with {len(info_dict['entries'])} songs. Queue em'?")
                    await ctx.send(content=content, view=view, delete_after=10)
                    await view.wait() 
                    if view.boolean:
                        for entry in info_dict['entries']:
                            # Extract relevant information from each entry
                            song_info = {
                                'artist': entry.get('uploader'),
                                'song_name': entry.get('title'),
                                'url': entry.get('url'),
                                'id': entry.get('id'),
                                'duration': entry.get('duration')
                            }
                            # video_info = ydl.extract_info(song_info['url'], download=False)
                            # song_info['url'] = video_info['url']
                            self.playlist.append(song_info)
                            if self.voice_instance.is_playing() == False:
                                self.currently_playing = self.playlist.pop(0)
                                self.play_audio(self.currently_playing['url'])
                        await ctx.send(f"Added {len(info_dict['entries'])} entries to the playlist.")

                else:
                    song_info = {
                        'artist': info_dict.get('uploader', 'Unknown Artist'),
                        'song_name': info_dict.get('title', 'Unknown Title'),
                        'url': f"{video_url}",
                        'id': info_dict.get('id'),
                        'duration': info_dict.get('duration')
                    }
                    self.playlist.append(song_info)
                    await ctx.send(f"Added song to playlist. {song_info['artist']} - {song_info['song_name']}")
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
        'extract_flat': 'in_playlist',  # To extract playlist info without downloading
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
        # Check if there's a next song in the playlist
        if self.voice_instance.is_playing() == True:
            return
        if self.playlist:
            self.currently_playing = self.playlist.pop(0)  # Get the next song
            print(self.currently_playing)
            self.play_audio(self.currently_playing['url'])  # Play the next song
        else:
            print("Playback has ended, and there are no more songs in the playlist.")

    async def info_channel(self):
        channel = self.channel
        print(channel)
        await channel.purge()
        embed = discord.Embed(
            title="Booting up Jukebox",
            #description=playlist
            )
        message_instance = await channel.send(embed=embed)
        last_playing = ""
        last_playlist = ""
        last_image = ""
        currently_playing_message = "No song playing"
        while True:
            length = len(self.playlist)
            if length > 5:
                outof = 5
            else:
                outof = length
            playlist = f"Song Queue:    {outof}/{length}\n---------------------\n"
            i = 1
            if self.playlist:
                for song in self.playlist:
                    minutes = int(song['duration'] / 60)
                    seconds = int(song['duration'] % 60)
                    if seconds < 10:
                        seconds = f"0{seconds}"
                    playlist += (f"{i}. {song['artist']} - {song['song_name']} - {minutes}:{seconds}\n")
                    i += 1
                    if i > 5:
                        break
            if self.currently_playing is not None:
                minutes = int(self.currently_playing['duration'] / 60)
                seconds = int(self.currently_playing['duration'] % 60)
                currently_playing_message = f"Playing: {self.currently_playing['artist']} - {self.currently_playing['song_name']} - {minutes}:{seconds}"
                image_link = f"https://img.youtube.com/vi/{self.currently_playing['id']}/maxresdefault.jpg"
                buttons = ["Play", "Pause", "Next Song", "Skip All", "Shuffle Queue"]
                view = JukeboxView(buttons, self, channel)
                embed = discord.Embed(
                    title=currently_playing_message,
                    #description=playlist
                )
                if last_image != image_link:
                    last_image = image_link
                    embed.set_image(url=image_link)
                    await message_instance.edit(embed=embed, view=view)
                if last_playing != currently_playing_message:
                    last_playing = currently_playing_message
                    embed.set_author(name=playlist)
                    embed.set_image(url=image_link)
                    await message_instance.edit(embed=embed, view=view)
                if last_playlist != playlist:
                    last_playlist = playlist
                    embed.set_author(name=playlist)
                    embed.set_image(url=image_link)
                    await message_instance.edit(embed=embed, view=view)
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
                style = discord.ButtonStyle.green
            else:
                style = discord.ButtonStyle.blurple  # Default style for safety
            button = discord.ui.Button(label=button_label, custom_id=button_label, style=style)
            button.callback = self.button_callback  # Set the callback here
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        if interaction.data["custom_id"] == "Yes":
            if interaction.user == self.ctx.author:
                self.boolean = True
                await interaction.response.send_message("Adding songs to queue...", ephemeral=True, delete_after=5)
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
                await interaction.response.send_message("JankBot paused.", delete_after=5)
        elif interaction.data["custom_id"] == "Play":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                if self.jukebox.voice_instance.is_playing():
                    return
                self.jukebox.voice_instance.resume()
                await interaction.response.send_message("Resuming JankBot.", delete_after=5)
        elif interaction.data["custom_id"] == "Next Song":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                await interaction.response.send_message("Song skipped!", delete_after=5)
                self.jukebox.voice_instance.stop()
                    
        elif interaction.data["custom_id"] == "Skip All":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                self.jukebox.playlist = []
                await interaction.response.send_message("Nuking the playlist...", delete_after=5)
                self.jukebox.voice_instance.stop()
        elif interaction.data["custom_id"] == "Shuffle Queue":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                random.shuffle(self.jukebox.playlist)
                await interaction.response.send_message("Queue shuffled!", delete_after=5)




