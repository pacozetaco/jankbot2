from mcrcon import MCRcon

class ArkRcon:
    def __init__(self, command):
        self.command = command
        self.RCON_HOST = 
        self.RCON_PORT = 
        self.RCON_PASSWORD = 
    

    def execute_command(self):
        try:
            with MCRcon(self.RCON_HOST, self.RCON_PASSWORD, self.RCON_PORT) as mcr:
                reply = mcr.command(self.command)
                return reply
        except Exception as e:
            print(f"Error connecting to RCON: {e}")
            return None
        
command = "ListPlayers"
#command = "Playerlist"

rcon = ArkRcon(command)
reply = rcon.execute_command()

print(reply)
i = 1
for player in reply.split("\n"):
    if player.strip():
        player_info = player.split(". ")
        if len(player_info) > 1:
            player_name = player_info[1].split(",")[0]
            print(f"{i}: " + player_name)
            i += 1
online = i-1
print(f"Online: {online}")