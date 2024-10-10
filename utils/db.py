import mysql.connector, config
from datetime import datetime
from mysql.connector import Error

sqldb = {
    'host': config.MYSQL_HOST,
    'port': config.MYSQL_PORT,
    'user': config.MYSQL_USER,
    'password': config.MYSQL_PASSWORD,
    'database': config.MYSQL_DATABASE
}

async def daily_coins(message):
    now = datetime.now()
    user_name = str(message.author)
    claim_date = now.date()
    try:
        with mysql.connector.connect(**sqldb) as con:
            cur = con.cursor()
            cur.execute('''
            CREATE TABLE IF NOT EXISTS jankcoins (
                name VARCHAR(255) PRIMARY KEY UNIQUE,
                coins BIGINT, 
                lastclaim DATE
            )''')
            # Check if the user exists
            cur.execute("SELECT * FROM jankcoins WHERE name = %s", [user_name])
            existing_user = cur.fetchone()
            if existing_user is None:
                # If the user doesn't exist, insert a new record
                cur.execute("INSERT INTO jankcoins (name, coins, lastclaim) VALUES (%s, %s, %s)", (user_name, 100, claim_date))
                reply = "100 coins added! Balance: 100"
            elif existing_user[2] != claim_date:
                # If the last claim date is not today, add 100 coins and update the last claim date
                cur.execute('''UPDATE jankcoins SET coins = %s, lastclaim = %s WHERE name = %s''', (int(existing_user[1]) + 100, claim_date, user_name))
                reply = f"100 coins added! Balance: {existing_user[1] + 100}"
            else:
                reply = f"You already claimed today! Balance: {existing_user[1]}"
            con.commit()
            print(existing_user[2], claim_date)
    except Error as e:
        reply = "An error occurred, please try again later."
        print(f"Error: {e}")
    return reply

async def get_balance(user):
    try:
        with mysql.connector.connect(**sqldb) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM jankcoins WHERE name = %s", [user])
            result = cur.fetchone()
            if result is None:
                return 0
            else:
                return result[1]
    except Error as e:
        print(f"Error: {e}")

async def set_balance(user, transaction_amount):
    try:
        with mysql.connector.connect(**sqldb) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM jankcoins WHERE name = %s", [user])
            user_data = cur.fetchone()
            cur.execute('''UPDATE jankcoins SET coins = %s WHERE name = %s''', (int(user_data[1]) + transaction_amount, user_data[0]))
            con.commit()
            print(f"Updated balance for {user} to {user_data[1] + transaction_amount}")
    except Error as e:
        print(f"Error: {e}")

async def log_hilo(gamelog):
    now = datetime.now()
    try:
        with mysql.connector.connect(**sqldb) as con:
            cur = con.cursor()
            cur.execute('''
            CREATE TABLE IF NOT EXISTS hilo_log (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                date DATE,
                time TIME,
                player TEXT,
                bet BIGINT,
                choice TEXT,
                roll INT,
                result TEXT
            )''')
            date = now.date()
            time = now.time()
            cur.execute('''
            INSERT INTO hilo_log (
                date, time, player, bet, choice, roll, result
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                date,
                time,
                gamelog.player,
                gamelog.bet,
                gamelog.choice,
                gamelog.roll,
                gamelog.result
            ))
            con.commit()
    except Error as e:
        print(f"Error: {e}")

async def log_deathroll(gamelog):
    now = datetime.now()
    try:
        with mysql.connector.connect(**sqldb) as con:
            cur = con.cursor()
            cur.execute('''
            CREATE TABLE IF NOT EXISTS deathroll_log (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                date DATE,
                time TIME,
                player TEXT,
                bet BIGINT,
                whofirst TEXT,
                result TEXT,
                gamecontent TEXT
            )''')
            date = now.date()
            time = now.time()
            cur.execute('''
            INSERT INTO deathroll_log (
                date, time, player, bet, whofirst, result, gamecontent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                date,
                time,
                gamelog.player,
                gamelog.bet,
                gamelog.whos_first,
                gamelog.result,
                gamelog.game_content
            ))
            con.commit()
    except Error as e:
        print(f"Error: {e}")

async def log_bj(gamelog):
    now = datetime.now()
    try:
        with mysql.connector.connect(**sqldb) as con:
            cur = con.cursor()
            cur.execute('''
            CREATE TABLE IF NOT EXISTS bj_log (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                date DATE,
                time TIME,
                player TEXT,
                bet BIGINT,
                result TEXT
            )''')
            date = now.date()
            time = now.time()
            cur.execute('''
            INSERT INTO bj_log (
                date, time, player, bet, result
            ) VALUES (%s, %s, %s, %s, %s)
            ''', (
                date,
                time,
                gamelog.player,
                gamelog.bet,
                gamelog.result
            ))
            con.commit()
    except Error as e:
        print(f"Error: {e}")

async def win_loss(ctx):
    user = str(ctx.author.name)
    game_stats = {
        "hilo": {"wins": 0, "losses": 0, "coins_won": 0, "coins_lost": 0},
        "blackjack": {"wins": 0, "losses": 0, "coins_won": 0, "coins_lost": 0},
        "deathroll": {"wins": 0, "losses": 0, "coins_won": 0, "coins_lost": 0},
    }

    tables = {
        "hilo": "hilo_log",
        "blackjack": "bj_log",
        "deathroll": "deathroll_log",
    }

    for game, table in tables.items():
        try:
            with mysql.connector.connect(**sqldb) as con:
                cur = con.cursor()
                cur.execute(f"SELECT result, bet FROM {table} WHERE player = %s", [user])
                rows = cur.fetchall()
                
                for result, bet in rows:
                    if result == 'won':
                        game_stats[game]["wins"] += 1
                        game_stats[game]["coins_won"] += bet
                    elif result == 'lost':
                        game_stats[game]["losses"] += 1
                        game_stats[game]["coins_lost"] += bet
        except Error as e:
            print(f"Error: {e}")

    # Prepare win/loss statistics message
    win_loss_message = f"**Game Win/Loss Statistics for {user}**\n"
    win_loss_message += "```md\n"
    win_loss_message += f"{'Game':<15} {'Win %':<7} {'W':<5} {'L':<5}\n"
    win_loss_message += f"{'-' * 35}\n"

    total_wins = total_losses = 0

    for game, stats in game_stats.items():
        wins = stats['wins']
        losses = stats['losses']

        # Calculate win percentage
        total_games = wins + losses
        win_percentage = (wins / total_games * 100) if total_games > 0 else 0.0

        win_loss_message += f"{game.title():<15} {win_percentage:<7.2f} {wins:<5} {losses:<5}\n"
        
        # Update total values
        total_wins += wins
        total_losses += losses

    # Calculate total win percentage
    total_games = total_wins + total_losses
    total_win_percentage = (total_wins / total_games * 100) if total_games > 0 else 0.0

    win_loss_message += f"{'Total':<15} {total_win_percentage:<7.2f} {total_wins:<5} {total_losses:<5}\n"
    win_loss_message += f"{'-' * 35}\n"
    win_loss_message += "```"

    # Prepare coins statistics message
    coins_message = f"**Game Coins Statistics for {user}**\n"
    coins_message += "```md\n"
    coins_message += f"{'Game':<15} {'W Coins':<10} {'L Coins':<10}\n"
    coins_message += f"{'-' * 35}\n"

    total_won_coins = total_lost_coins = 0

    for game, stats in game_stats.items():
        won_coins = stats['coins_won']
        lost_coins = stats['coins_lost']

        coins_message += f"{game.title():<15} {won_coins:<10} {lost_coins:<10}\n"
        
        # Update total coins values
        total_won_coins += won_coins
        total_lost_coins += lost_coins

    coins_message += f"{'Total':<15} {total_won_coins:<10} {total_lost_coins:<10}\n"
    coins_message += f"{'-' * 35}\n"
    coins_message += "```"

    # Combine both messages
    combined_message = win_loss_message + "\n" + coins_message

    # Send the message to the Discord channel
    return combined_message





