import paramiko, os, config

async def upload_config(message):
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename == "GameUserSettings.ini" or attachment.filename == "Game.ini":
                file_path = f"./temp/{attachment.filename}"
                await attachment.save(file_path)
                await message.reply(f"Config file {attachment.filename} received!")

                if attachment.filename == "GameUserSettings.ini":
                    try:

                        with open(file_path, 'r') as file:
                            lines = file.readlines()

                        # Write the updated contents to a new file
                        with open(file_path, 'w') as file:
                            for line in lines:
                                # Update the password if the line contains the key
                                if line.startswith('ServerAdminPassword'):
                                    line = f'ServerAdminPassword={config.ARK_ADMIN_PW}\n'
                                file.write(line)

                    except Exception as e:
                        await message.reply(f"Failed to update the config file.")
                        return

                try:
                    # Create the SSH client and automatically accept host key
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    # Connect to the SFTP server
                    ssh.connect(config.ARK_SFTP_SERVER, username=config.ARK_SFTP_USER, password=config.ARK_SFTP_PASS)
                    with ssh.open_sftp() as sftp:
                        # Navigate to the upload directory and upload the file
                        sftp.chdir(config.ARK_SFTP_UPLOAD_DIR)
                        sftp.put(file_path, f"{config.ARK_SFTP_UPLOAD_DIR}/{attachment.filename}")
                        await message.reply(f"File `{attachment.filename}` uploaded successfully.")
                        # Close the SSH connection
                        ssh.close()

                except Exception as e:
                    await message.reply(f"Failed to upload the file due to an unexpected error.")

                finally:
                    # Ensure the temporary file is deleted
                    if os.path.exists(file_path):
                        os.remove(file_path)

    else:
        await message.reply("No config file attached!")
