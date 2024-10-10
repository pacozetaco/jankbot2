from mcrcon import MCRcon

class ArkRcon:
    def __init__(self, command):
        self.command = command
        self.RCON_HOST = "lol"
        self.RCON_PORT = 123
        self.RCON_PASSWORD = "lol"
    

    def execute_command(self):
        try:
            with MCRcon(self.RCON_HOST, self.RCON_PASSWORD, self.RCON_PORT) as mcr:
                mcr.command(self.command)
        except Exception as e:
            print(f"Error connecting to RCON: {e}")
            return None
        
command = "ServerChat No Dinos?"

rcon = ArkRcon(command)
reply = rcon.execute_command()

print(reply)