from dotenv import load_dotenv
import os

#JANKBOT CASINO CONFIG
MAIN_CASINO_CHANNEL = "casino"

#MAIN BOT SETUP PULLED FROM .ENV
load_dotenv()
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

#ARK SERVER CONFIG
ARK_SFTP_SERVER = os.getenv("ARK_SFTP_SERVER")
ARK_SFTP_USER = os.getenv("ARK_SFTP_USER")
ARK_SFTP_PASS = os.getenv("ARK_SFTP_PASS")
ARK_SFTP_UPLOAD_DIR = os.getenv("ARK_SFTP_UPLOAD_DIR")
ARK_CONTAINER_NAME = os.getenv("ARK_CONTAINER_NAME")
ARK_CONTAINER_IP = os.getenv("ARK_CONTAINER_IP")
ARK_ADMIN_PW = os.getenv("ARK_ADMIN_PW")
ARK_CONFIG_CHANNEL = os.getenv("ARK_CONFIG_CHANNEL")
ARK_STATUS_CHANNEL = os.getenv("ARK_STATUS_CHANNEL")
ARK_RCON_HOST = os.getenv("ARK_RCON_HOST")
ARK_RCON_PORT = os.getenv("ARK_RCON_PORT")

