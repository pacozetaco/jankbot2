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


    async def search_youtube(self, ctx, request):
        await ctx.send(content=f"Searching for: {request}... Just kidding, WIP")


    async def process_request(self, ctx, video_url):
        self.ctx = ctx
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'extract_flat': 'in_playlist', 
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=False)
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
        embed = discord.Embed(
            title="Booting up Jukebox",
            )
        message_instance = await channel.send(embed=embed)
        last_playing = ""
        last_playlist = ""
        last_image = ""
        currently_playing_message = "No song playing"
        while True:
            length = len(self.playlist)
            if length > 10:
                outof = 10
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
                    if seconds == 0:
                        seconds = "00"
                    playlist += (f"{i}. {song['artist']} - {song['song_name']} - {minutes}:{seconds}\n")
                    i += 1
                    if i > 10:
                        break
            if self.currently_playing is not None:
                minutes = int(self.currently_playing['duration'] / 60)
                seconds = int(self.currently_playing['duration'] % 60)
                if seconds < 10:
                    seconds = f"0{seconds}"
                if seconds == 0:
                    seconds = "00"
                currently_playing_message = f"Playing: {self.currently_playing['artist']} - {self.currently_playing['song_name']} - {minutes}:{seconds}"
                image_link = f"https://img.youtube.com/vi/{self.currently_playing['id']}/maxresdefault.jpg"
                buttons = ["Play", "Pause", "Next Song", "Skip All", "Shuffle Queue"]
                view = JukeboxView(buttons, self, channel)
                embed = discord.Embed(
                    title=currently_playing_message,
                )
                if last_image != image_link:
                    last_image = image_link
                    embed.set_footer(text=playlist)
                    embed.set_image(url=image_link)
                    await message_instance.edit(embed=embed, view=view)
                if last_playing != currently_playing_message:
                    last_playing = currently_playing_message
                    embed.set_footer(text=playlist)
                    embed.set_image(url=image_link)
                    await message_instance.edit(embed=embed, view=view)
                if last_playlist != playlist:
                    last_playlist = playlist
                    embed.set_footer(text=playlist)
                    embed.set_image(url=image_link)
                    await message_instance.edit(embed=embed, view=view)
            else:
                embed = discord.Embed(
                    title="No songs playing at the moment.",
                    description=f"To add songs, go to song-queue channel and type `!play <youtube link>`",
                )
                embed.set_image(url="https://i.imgur.com/AJpM3Oc.jpeg")
                embed.set_footer(text="We have YouTube premium at home.")
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
                await interaction.response.reply("Adding songs to queue... this takes a sec depending on how big the playlist is.", ephemeral=True, delete_after=5)
                self.stop()
        elif interaction.data["custom_id"] == "No":
            if interaction.user == self.ctx.author:
                self.boolean = False
                await interaction.response.reply("No songs added to queue.", ephemeral=True, delete_after=5)
                self.stop()
            return interaction.user,False
        elif interaction.data["custom_id"] == "Pause":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                if self.jukebox.voice_instance.is_paused():
                    return
                self.jukebox.voice_instance.pause()
                await interaction.response.reply("JankBot paused.", delete_after=5)
            else:
                await interaction.response.reply("We are not in the same voice channel.", ephemeral=True, delete_after=5)
        elif interaction.data["custom_id"] == "Play":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                if self.jukebox.voice_instance.is_playing():
                    return
                self.jukebox.voice_instance.resume()
                await interaction.response.reply("Resuming JankBot.", delete_after=5)
            else:
                await interaction.response.reply("We are not in the same voice channel.", ephemeral=True, delete_after=5)
        elif interaction.data["custom_id"] == "Next Song":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                await interaction.response.reply("Song skipped!", delete_after=5)
                self.jukebox.voice_instance.stop()
                    
        elif interaction.data["custom_id"] == "Skip All":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                self.jukebox.playlist = []
                await interaction.response.reply("Nuking the playlist...", delete_after=5)
                self.jukebox.voice_instance.stop()
            else:
                await interaction.response.reply("We are not in the same voice channel.", ephemeral=True, delete_after=5)
        elif interaction.data["custom_id"] == "Shuffle Queue":
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_id:
                random.shuffle(self.jukebox.playlist)
                await interaction.response.reply("Queue shuffled!", delete_after=5)
            else:
                await interaction.response.reply("We are not in the same voice channel.", ephemeral=True, delete_after=5)




