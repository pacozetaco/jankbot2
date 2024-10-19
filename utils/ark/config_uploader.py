import paramiko, os, config

async def upload_config(message):
    print("upload_config() called", flush=True)
    
    if message.attachments:
        for attachment in message.attachments:
            print(f"Processing attachment {attachment.filename}", flush=True)
            
            if attachment.filename == "GameUserSettings.ini" or attachment.filename == "Game.ini":
                file_path = f"./temp/{attachment.filename}"
                await attachment.save(file_path)
                print(f"Config file {attachment.filename} saved to disk", flush=True)
                await message.reply(f"Config file {attachment.filename} received!", flush=True)

                if attachment.filename == "GameUserSettings.ini":
                    try:
                        print("Updating config file contents...", flush=True)

                        with open(file_path, 'r') as file:
                            lines = file.readlines()

                        # Write the updated contents to a new file
                        with open(file_path, 'w') as file:
                            for line in lines:
                                # Update the password if the line contains the key
                                if line.startswith('ServerAdminPassword'):
                                    print("Updating ServerAdminPassword...", flush=True)
                                    line = f'ServerAdminPassword={config.ARK_ADMIN_PW}\n'
                                print(f"Writing line to file: {line}", flush=True)
                                file.write(line)

                    except Exception as e:
                        print(f"Error updating config file: {e}", flush=True)
                        await message.reply(f"Failed to update the config file.", flush=True)
                        return

                try:
                    # Create the SSH client and automatically accept host key
                    ssh = paramiko.SSHClient()
                    print("Creating SSH client...", flush=True)
                    
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    print("Setting SSH client policy...", flush=True)
                    
                    # Connect to the SFTP server
                    ssh.connect(config.ARK_SFTP_SERVER, username=config.ARK_SFTP_USER, password=config.ARK_SFTP_PASS)
                    print(f"Connecting to SFTP server: {config.ARK_SFTP_SERVER}", flush=True)
                    
                    with ssh.open_sftp() as sftp:
                        # Navigate to the upload directory and upload the file
                        sftp.chdir(config.ARK_SFTP_UPLOAD_DIR)
                        print(f"Changing dir on SFTP server to {config.ARK_SFTP_UPLOAD_DIR}", flush=True)
                        
                        sftp.put(file_path, f"{config.ARK_SFTP_UPLOAD_DIR}/{attachment.filename}")
                        print(f"Uploading file {attachment.filename} to SFTP server", flush=True)
                        
                        await message.reply(f"File `{attachment.filename}` uploaded successfully!", flush=True)
                        
                        # Close the SSH connection
                        ssh.close()
                        print("Closing SSH client...", flush=True)

                except Exception as e:
                    print(f"Error uploading file: {e}", flush=True)
                    await message.reply(f"Failed to upload the file due to an unexpected error.", flush=True)

                finally:
                    # Ensure the temporary file is deleted
                    if os.path.exists(file_path):
                        print("Deleting temp file...", flush=True)
                        
                        os.remove(file_path)

    else:
        print("No config file attached!", flush=True)
        await message.reply("No config file attached!", flush=True)
