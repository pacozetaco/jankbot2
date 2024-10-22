from discord.ext import commands
import re, discord, yt_dlp, asyncio, random, functools, discord

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
        self.message_instance = None
        self.voice_instance = None
        self.bot.loop.create_task(self.info_prep())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        await self.people_check()
        if before.channel is not None and after.channel is None:
            if member.id == self.bot.user.id:
                await self.nuke_player()

    async def info_prep(self):
        await self.channel.purge()
        embed = discord.Embed(
            title="Booting up Jukebox",
            color=discord.Color.blue()
        )
        self.message_instance = await self.channel.send(embed=embed)
        await self.info_channel()

    async def nuke_player(self):
        self.playlist = []
        self.voice_instance = None
        await self.info_channel()

    @commands.command(name="leave")
    @jukebox_channel_only
    async def leave(self, ctx):
        if self.voice_instance:
            await self.voice_instance.disconnect()

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

    async def people_check(self):
        if self.voice_instance and len(self.voice_instance.channel.members) < 2:
            await self.voice_instance.disconnect()

    async def info_channel(self):
        length = len(self.playlist)-1
        outof = min(length, 10)  # Adjust max songs displayed
        playlist = ""
        if self.playlist != []:
            for i, song in enumerate(self.playlist[1:11], 1):
                time = self.format_time(song['duration'])
                # Format the song info with fixed-width fields
                playlist += f"`{i:2}. {song['artist'][:13]:<13} - {song['song_name'][:26]:<26} - {time}`\n"
            # Format currently playing song
            time = self.format_time(self.playlist[0]['duration'])
            currently_playing_message = (
                f"Playing: {self.playlist[0]['artist']} - "
                f"{self.playlist[0]['song_name']} - {time}"
            )
            image_link = f"https://img.youtube.com/vi/{self.playlist[0]['id']}/maxresdefault.jpg"

            embed = discord.Embed(title=currently_playing_message, color=discord.Color.blue())
            embed.set_image(url=image_link)
            embed.add_field(name=f"Song Queue {outof}/{length}", value=playlist, inline=False)  # Add the playlist as a field
            buttons = ["Play", "Pause", "Skip", "Shuffle", "Nuke"]
            view = JukeboxView(buttons, self, self.channel)
            await self.message_instance.edit(embed=embed, view=view)

        else:
            embed = discord.Embed(
                color=discord.Color.blue()
            )
            embed.set_image(url="https://i.imgur.com/AJpM3Oc.jpeg")
            embed.add_field(name="" ,value="To add songs, go to #jukebox-spam channel and type `!play <yt / yt music link or search for a song >`", inline=False)
            embed.set_footer(text="We have Youtube Premium at home.")
            embed.add_field(name=f"Song Queue 0/0", value="No songs in the playlist.", inline=False)  # Default playlist message
            await self.message_instance.edit(embed=embed, view=None)

    async def idle_timer(self):
        idle_time = 0
        while True:
            if self.voice_instance is not None:
                if not self.voice_instance.is_playing():
                    idle_time += 1
                    if idle_time > 10:
                        await self.voice_instance.disconnect()
                        break
                else:
                    break
            else:
                break
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
        await view.wait()
        if view.reply is not None:
            chosen_song = songs.pop(int(view.reply) - 1)
            await msg.delete()
            return f"https://www.youtube.com/watch?v={chosen_song['id']}"
        else:
            await msg.delete()
    
    async def process_request(self, ctx):
        request = ctx.message.content.split("!play ", 1)[1]
        if not request.startswith(("http://", "https://", "www.")):
            request = await self.search_youtube(ctx)
        try:
            info_dict = await self.get_dict(request)
            if 'entries' in info_dict:
                view = JukeboxView(["Yes", "No"], self, ctx)
                content = (f"Playlist detected with {len(info_dict['entries'])} songs. Queue em'?")
                await ctx.reply(content=content, view=view, delete_after=10)
                await view.wait()
                if view.boolean:
                    self.playlist.extend([self.get_song_info(entry) for entry in info_dict['entries'] if entry['title'] != "[Deleted video]"])
                    if self.voice_instance.is_playing() or self.voice_instance.is_paused():
                        pass
                    else:
                        await self.play_audio()
                    await ctx.reply(f"{len(info_dict['entries'])} songs added to queue.")
            else:
                self.playlist.append(self.get_song_info(info_dict))
                await ctx.reply(f"Added song to playlist. {self.playlist[-1]['artist']} - {self.playlist[-1]['song_name']}")
        except Exception as e:
            print(e, flush=True)
            return await ctx.send("Something went wrong. Please try again.")
        await self.info_channel()
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
            await self.voice_instance.disconnect()
        else:
            if self.playlist != []:
                self.playlist.pop(0)
                await self.info_channel()
                if self.playlist != []:
                    await self.play_audio()
                else:
                    try:
                        self.voice_instance.stop()
                    except:
                        pass
                    await self.bot.loop.create_task(self.idle_timer()) 

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
                await interaction.response.send_message("OK", ephemeral=True, delete_after=5)
                self.stop()
        elif custom_id in ("Pause", "Play"):
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_instance.channel:
                self.jukebox.voice_instance.pause() if custom_id == "Pause" else self.jukebox.voice_instance.resume()
                await interaction.response.defer()
                if custom_id == "Pause":
                    await self.jukebox.bot.loop.create_task(self.jukebox.idle_timer())
        elif custom_id in ("Nuke", "Shuffle", "Skip"):
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_instance.channel:
                await interaction.response.defer()
                if custom_id == "Nuke":
                    self.jukebox.playlist = ["nuked"]
                    self.jukebox.voice_instance.stop()
                elif custom_id == "Shuffle":
                    self.jukebox.playlist[1:] = random.sample(self.jukebox.playlist[1:], len(self.jukebox.playlist) - 1)
                    await self.jukebox.info_channel()
                elif custom_id == "Skip":
                    self.jukebox.voice_instance.stop()
        elif custom_id.isdigit():
            if interaction.user.voice and interaction.user.voice.channel == self.jukebox.voice_instance.channel:
                await interaction.response.defer()
                self.reply = custom_id
                self.stop()
