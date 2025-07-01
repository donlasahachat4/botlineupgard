import flask
import requests
from flask import Flask, jsonify, request,send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import sqlite3
import difflib
import time
import math
import base64
from datetime import datetime , timedelta
from PIL import Image
import os
import random
import re
import random
import string
import threading
import math
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'change-me')
jwt = JWTManager(app)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins='*')

#domain = "https://cus2.witheeit.xyz"
#domain = "https://cus2.witheeit.xyz"
domain = "https://cus2.witheeit.xyz/"

Channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')

line_notify_token = os.environ.get('LINE_NOTIFY_TOKEN', '')
# line_notify_token = 'BxIZDd6bnTXnNeJm1BjeH9IOKTYqAhcJgtPYooUZDlL'
# possibilities = ['p1','p2','p3','p4']

db_name = 'chicken_cus2.db'

link_acc_room = """ห้องฝาก-ถอน\nxxx\n👈จิ้มเลย ลิ้งเข้าห้องฝาก"""

link_play_room = """ห้องเล่น \n xx\n👈จิ้มเลย ลิ้งเข้าห้องเล่น"""

acc_number = '8112908061'

acc_msg = ''

start_amount = 0

game_name='นายหัว88'

ac_msg = """ฝาก ห้ามนำสลิปส่งในกลุ่ม\nให้แจ้งผ่านไลน์นี้เท่านั้น\n👇🏻👇🏻👇🏻👇🏻👇🏻\nhttps://lin.ee/JY73X9U"""




last_emission_time = 0
lock = threading.Lock()
timer_started = False

def start_timer():
    global timer_started
    socketio.sleep(1)  # Wait for 3 seconds
    with lock:
        print('data_send')
        socketio.emit('incoming_data',{'incoming_data':'data'})  # Emit the socket message
        timer_started = False

def generate_order_id(k=10):
    return ''.join(random.choices(string.ascii_lowercase, k=k))

def send_line_notify(message):
    try:
        url = 'https://notify-api.line.me/api/notify'
        headers = {
            'Authorization': f'Bearer {line_notify_token}'
        }
        data = {
            'message': message
        }
        response = requests.post(url, headers=headers, data=data)
        print(response.text)
        return response.status_code, response.text
    except Exception as e:
        print(e)
        return 0

def find_similar(word, possibilities=['']):
    matches = difflib.get_close_matches(word, possibilities, n=1, cutoff=0.6)
    return matches[0] if matches else None

def combine_images(images):
    # Create the full file paths with .jpg extension
    image_paths = [img for img in images]
    
    # Open images and store them in a list
    image_list = [Image.open(image) for image in image_paths]
    
    # Concatenate the image names to form the output filename
    name_img = '_'.join([os.path.splitext(os.path.basename(img))[0] for img in image_paths])
    output_path = f'pic/{name_img}.jpg'
    link_path = f'{name_img}.jpg'

    # Check if the output image already exists
    if os.path.exists(output_path):
        print(f"File '{output_path}' already exists. Returning the path.")
        return link_path
    
    # Determine the number of columns (2) and rows
    num_columns = 2
    num_images = len(image_list)
    num_rows = (num_images + 1) // num_columns  # Calculates the number of rows required (adding 1 ensures extra image gets its own row)

    # Get the max width of any image for column width, and max height of any image for row height
    max_width = max(img.width for img in image_list)
    max_height = max(img.height for img in image_list)

    # Calculate the total width and total height for the combined image
    total_width = num_columns * max_width
    total_height = num_rows * max_height

    # Create a new blank image with total width and height
    combined_image = Image.new('RGB', (total_width, total_height))

    # Paste each image into the combined image
    x_offset = 0
    y_offset = 0
    for i, img in enumerate(image_list):
        combined_image.paste(img, (x_offset, y_offset))

        # Move to the next column (or row if end of row is reached)
        if (i + 1) % num_columns == 0:  # If we just pasted the second image in the row
            x_offset = 0  # Reset x_offset to start a new row
            y_offset += max_height  # Move down to the next row
        else:
            x_offset += max_width  # Move to the next column
    
    # Save the combined image
    combined_image.save(output_path)
    print(f"New file '{output_path}' created.")
    
    return link_path

def create_bet_summary_image(bet_summary):
    # Extract the bet summary results
    data = bet_summary['data']
    
    # Create a list to store the image filenames
    image_names = []

    # Add images based on the counts in the bet_summary
    for animal, count in data.items():
        if count > 0:  # Only include images where there is a count greater than 0
            if animal == 'high':
                animal = 'h'
            elif animal =='low':
                animal = 'l'
            image_names += [animal] * count  # Add the image name as many times as the count
    
    # Path to where the images are stored, and they are named as the animals, e.g., 'ไก่.jpg'
    image_paths = [f'html/image/{name}.jpg' for name in image_names]

    # Check if there are images to combine
    if image_paths:
        result_image_path = combine_images(image_paths)  # Use combine_images function
        return result_image_path  # Return the path of the combined image
    else:
        return None

def get_bets_user(user_id):
    round = get_present_round()
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT sub_round,chicken,amount_play FROM play WHERE user_id =? AND round =? ',(user_id,round))
        datas = cursor.fetchall()
        if not datas:
            return None
        else:
            bets = []
            for data in datas:
                bet = {
                    'chicken':data[1],
                    'sub_round':data[0],
                    'amount':data[2],
                  
                }
                bets.append(bet)
            return bets

def calculate_card_points(card):
    """Calculate the point value of a single card based on its rank."""
    value = card[:-1]  # Remove the suit to get the card value
    if value in ['J', 'Q', 'K']:
        return 0  # Face cards have a point value of 0
    elif value == 'A':
        return 1  # Ace is worth 1 point
    else:
        return int(value) 
    
def create_bet_bubble1(bets, user_id):

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, display_name, picture_url, amount FROM user_profiles WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            raise ValueError("User not found in the database")

        game_id = user_data[0]
        user_name = user_data[1]
        user_pic = user_data[2]
        balance = user_data[3]

    bet_contents = []
    for bet in bets:
        bet_chicken = 'แดง'
        bg_color = '#FF0000'
        if bet['chicken'] == 'ง':
            bet_chicken = 'น้ำเงิน'
            bg_color = '#0000FF'

        # Create a horizontal box to hold both the text and the amount with different backgrounds
        data = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"ราคาที่ {bet['sub_round']} {bet_chicken}",
                            "color": "#ffffff"
                        }
                    ],
                    "backgroundColor": bg_color,
                    "flex": 3  # Adjust flex ratio as needed
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"{bet['amount']} บ.",
                            "align": "center"
                        }
                    ],
                    "backgroundColor": "#FFFFFF",  # Default background color for the amount box
                    "flex": 1  # Adjust flex ratio as needed
                }
            ]
        }

        bet_contents.append(data)

    bb_content = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "image",
                                    "url": user_pic,
                                    "size": "md",
                                    "align": "start"
                                }
                            ],
                            "width": "45px"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": f"ID: {game_id}) {user_name}"
                                        }
                                    ]
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": bet_contents
                                },
                                {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": f"คงเหลือ {balance} บ.",
                                            "align": "end"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    if not user_pic:
        bb_content = {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                        {
                                            "type": "box",
                                            "layout": "horizontal",
                                            "contents": [
                                                {
                                                    "type": "text",
                                                    "text": f"ID: {game_id}) {user_name}"
                                                }
                                            ]
                                        },
                                        {
                                            "type": "box",
                                            "layout": "vertical",
                                            "contents": bet_contents
                                        },
                                        {
                                            "type": "box",
                                            "layout": "horizontal",
                                            "contents": [
                                                {
                                                    "type": "text",
                                                    "text": f"ยอดคงเหลือ {balance} บ.",
                                                    "align": "end"
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    return bb_content

def is_suited(hand):
    """Check if the cards in the hand have the same suit."""
    suits = [card[-1] for card in hand]  # Extract the suit from each card
    return suits[0] == suits[1]  # Return True if both cards have the same suit

def get_user_profile(user_id):
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    headers = {
        "Authorization": f"Bearer {Channel_access_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(response.text)
        return None
    
def get_present_round(sub_round=0):
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT round,sub_round FROM round ORDER BY id DESC LIMIT 1')
        current_round = cursor.fetchone()
        if sub_round ==1:
            return current_round[0],current_round[1]
        if current_round:
            return current_round[0]
        
        return None

def get_picture(dice):
    url = f'{domain}/pictures/d{dice}.png'
    return url

def update_balance(id, amount, operation, admin_id='game'):
    try:
        with sqlite3.connect(db_name) as conn:
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('PRAGMA busy_timeout = 5000')
            cursor = conn.cursor()

            print('test update_balance')
            cursor.execute('SELECT amount FROM user_profiles WHERE id = ?', (id,))
            current_amount = cursor.fetchone()

            if current_amount:
                try:
                    current_amount = float(current_amount[0])
                except:
                    current_amount = 0

                if operation == '+':
                    new_amount = current_amount + amount
                elif operation == '-':
                    new_amount = current_amount - amount

                if new_amount < 0:
                    return {'amount': current_amount, 'reply': f"User ID: {id} ยอดเงินมีแค่ {current_amount} บาท\nไม่สามารถหักเกินได้ กรุณาลองใหม่อีกครั้ง"}

                cursor.execute('UPDATE user_profiles SET amount = ?, backup_amount = ? WHERE id = ?', 
                               (str(round(new_amount)), str(round(new_amount)), id))

                current_utc_time = datetime.utcnow()
                thailand_time = current_utc_time + timedelta(hours=7)
                thailand_time_str = thailand_time.strftime('%d-%m-%Y %H:%M:%S')

                cursor.execute('''INSERT INTO log_add_remove_balance (user_id, admin_id, amount, datetime)
                                  VALUES (?, ?, ?, ?)''', (id, admin_id, f"{operation}{amount}", thailand_time_str))

                conn.commit()
                print('test update_balance3')
                return round(new_amount)
            else:
                print('test3')
                return None
    except sqlite3.OperationalError as e:
        print(f"SQLite error: {e}")
        return None


def init_db():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT ,
            display_name TEXT,
            picture_url TEXT,
            status_message TEXT,
            acc_num TEXT,
            bank_name TEXT,
            amount TEXT,
            backup_amount TEXT,
            acc_name TEXT
        )
    ''')
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_add_remove_balance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT ,
            admin_id TEXT,
            amount TEXT,
            datetime TEXT
    )
""")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_pass (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
    )
""")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS focus_group(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id TEXT,
            status TEXT,
            game_status TEXT,
            role TEXT        
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_group(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS round(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round INT,
            bet_ratio TEXT,
            max_bet INT,
            sub_round INT )
                   ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS play(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            round INT,
            user_play TEXT,
            chicken TEXT,
            bet_ratio TEXT,
            amount_play TEXT,
            sub_round INT
                   )
''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS result(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chicken TEXT,
            round INT,
            profit INT
                          )
''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            min_bet INT,
            max_bet_total INT,
            max_auto_close INT,
            max_round INT
                          )
''')
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_acc_room TEXT,
            link_play_room TEXT,
            acc_num TEXT,
            acc_pic TEXT,
            game_name TEXT,
            ac_msg TEXT,
            open_pic TEXT,
            close_pic TEXT,
            red_win TEXT,
            blue_win TEXT,
            tie TEXT,
            how_to_play_pic TEXT,
            msg_how_to_play TEXT
        )
        """)
    conn.commit()
    conn.close()

def create_bet_bubble(bets, round_value, bet_setting='', color='light_blue'):
    if color == 'blue':
        c_color = "#0000FF"
    elif color == 'red':
        c_color = "#FF0000"
    else:
        c_color = "#19cdfa"

    contents = {
        "type": "bubble",
        "size": "giga",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": game_name, "align": "center", "size": "xxl", "color": "#FFFFFF", "weight": "bold"},
                {"type": "text", "text": "ยอดแทงทั้งหมด", "align": "center", "size": "xl", "color": "#FFFFFF", "weight": "bold"}
            ],
            "backgroundColor": c_color
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"รอบที่ {round_value} ราคา: {bet_setting}", "weight": "bold", "size": "lg"},
                {"type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": "ID", "weight": "bold", "size": "sm", "flex": 1},
                    {"type": "text", "text": "น้ำเงิน", "weight": "bold", "size": "sm", "flex": 1, "align": "center","color":"#0000ff"},
                    {"type": "text", "text": "แดง", "weight": "bold", "size": "sm", "flex": 1, "align": "center","color":"#ff0000"}
                ]}
            ]
        }
    }

    for bet in bets:
        print(bet)
        user_id = bet[0]
        display_name = bet[1]
        blue_amount = 0
        red_amount = 0

        # Parse the bet types and amounts
        for user_play in bet[2]:
            play = user_play.split('=')[0]
            amount = user_play.split('=')[1]
            if play == "ง":
                blue_amount += int(amount)
            elif play == "ด":
                red_amount += int(amount)

        chicken = bet[4]
      

        bet_summary = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": f"{user_id}) {display_name}", "size": "sm", "flex": 1},
                {"type": "text", "text": f"{blue_amount}", "size": "sm", "flex": 1, "align": "center"},
                {"type": "text", "text": f"{red_amount}", "size": "sm", "flex": 1, "align": "center"}
            ]
        }
        contents["body"]["contents"].append(bet_summary)

    return contents

def store_user_profile(user_profile):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Check if the user already exists
    cursor.execute('SELECT user_id FROM user_profiles WHERE user_id = ?', (user_profile['userId'],))
    existing_user = cursor.fetchone()

    if existing_user:
        # Update the existing user record
        print('user_exits')
        cursor.execute('''
            UPDATE user_profiles
            SET display_name = ?, picture_url = ?
            WHERE user_id = ?
        ''', (user_profile['displayName'], user_profile.get('pictureUrl', ''), user_profile['userId']))
    else:
        # Insert a new user record
        cursor.execute('''
            INSERT INTO user_profiles (user_id, display_name, picture_url, amount, backup_amount)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_profile['userId'], user_profile['displayName'], user_profile.get('pictureUrl', ''), start_amount, start_amount))
        cursor.execute('''INSERT INTO admin_group (user_id, role)
                                                    VALUES (?,?)''',(user_profile['userId'],'user'))  
        
    conn.commit()
    conn.close()

def store_message(user_id, group_id, message, timestamp, msg_id):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (user_id, group_id, message, timestamp, msg_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, group_id, message, timestamp, msg_id))
    conn.commit()
    conn.close()

def get_balance(user_id,pic=0):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    if pic ==0:
        cursor.execute('''SELECT id, display_name, amount FROM user_profiles WHERE user_id =? ''', (user_id,))
    else:
        cursor.execute('''SELECT id, display_name, amount ,picture_url FROM user_profiles WHERE user_id =? ''', (user_id,))
    data = cursor.fetchone()
    conn.close()
    return data

def analysis_type_bet(bet_input):
    # bet_input = bet_input.replace('=', '/','.','-').strip()
    if '/' in bet_input:
        bet_type, amount = bet_input.split('/')
        amount = int(amount)
    elif '=' in bet_input:
        bet_type, amount = bet_input.split('=')
        amount = int(amount)
    elif '.' in bet_input:
        bet_type, amount = bet_input.split('.')
        amount = int(amount)
    elif '-' in bet_input:
        bet_type, amount = bet_input.split('-')
        amount = int(amount) 
    else:
        bet_type = bet_input[0]
        amount = re.findall(r'\d+', bet_input)
        if len(amount) != 1:
            return 0 
        else:
            amount = int(amount[0])
    
    return {
        'chicken': bet_type,
        'amount': amount
    }

def calculate_and_update_rewards_hilo(round_value):
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT d1,d2,d3 FROM result WHERE round = ? ORDER BY id DESC LIMIT 1',(round_value,))
            dice_result = list(map(int,cursor.fetchone()))
            total = int(dice_result[0])+int(dice_result[1])+int(dice_result[2])
            counts = {i: dice_result.count(i) for i in range(1, 7)}
            total_payout = 0  # Keep track of total payout for the round

            # Fetch user bets for the current round
            cursor.execute('''
                SELECT user_id, type_bet, bet_catagory, number, amount_play
                FROM play
                WHERE round = ?
            ''', (round_value,))
            bets = cursor.fetchall()

            user_results = {}

            # Initialize user_results with zeroed values for each user
            for bet in bets:
                user_id, bet_type, bet_category, numbers, amount = bet
                amount = float(amount)
                if user_id not in user_results:
                    user_results[user_id] = {
                        'win': 0,
                        'loss': 0,
                        'net_change': 0,
                        'new_balance': 0,
                        'name': '',
                        'game_id': ''
                    }

            # Process each bet and calculate wins/losses
            for bet in bets:
                user_id, bet_type, bet_category, numbers, amount = bet
                numbers = [int(n) for n in numbers.split(',')] if numbers else []
                amount = float(amount)

                total_win = 0
                total_loss = 0
                won = False
                bet_payout = 0

                if bet_category == 'สูงต่ำ':
                    if bet_type in ['สูง', 'ส'] and 12 <= total <= 17:
                        bet_payout = amount * 1
                        won = True
                    elif bet_type in ['ต่ำ', 'ต'] and 4 <= total <= 10:
                        bet_payout = amount * 1
                        won = True
                elif bet_category in ['สูงเลข', 'ต่ำเลข']:
                    num = numbers[0]
                    if bet_category == 'สูงเลข' and 12 <= total <= 17 and num in dice_result:
                        bet_payout = amount * 2
                        won = True
                    elif bet_category == 'ต่ำเลข' and 4 <= total <= 10 and num in dice_result:
                        bet_payout = amount * 2
                        won = True
                elif bet_category == '11ไฮโล':
                    if total == 11:
                        bet_payout = amount * 6
                        won = True
                elif bet_category == 'สเปเชียล':

                    if sorted(numbers) == sorted(dice_result):
                        bet_payout = amount * 25
                        won = True
                elif bet_category == 'ตอง':
                    num = numbers[0]
                    if dice_result.count(num) == 3:
                        bet_payout = amount * 80
                        won = True
                elif bet_category == 'คู่ระบุ':
                    num = numbers[0]
                    if counts.get(num, 0) >= 2:
                        bet_payout = amount * 7
                        won = True
                elif bet_category == 'คู่ไม่ระบุ':
                    has_pair = any(count >= 2 for count in counts.values())
                    if has_pair:
                        bet_payout = amount * 1.5
                        won = True
                elif bet_category == 'โต๊ด':
                    match_count = sum(1 for n in numbers if n in dice_result)
                    if match_count == 2:
                        bet_payout = amount * 5
                        won = True
                    elif match_count == 3:
                        bet_payout = amount * 25
                        won = True
                elif bet_category == 'เต็ง':
                    num = numbers[0]
                    count = counts.get(num, 0)
                    if count > 0:
                        bet_payout = amount * count
                        won = True

                if won:
                    total_win += bet_payout
                else:
                    total_loss += amount

                # Update the accumulated results for the user
                user_results[user_id]['win'] += total_win
                user_results[user_id]['loss'] += total_loss

            # Calculate net change and update balances once for each user
            for user_id, data in user_results.items():
                data['net_change'] = data['win'] - data['loss']

                # Update user balance
                cursor.execute('SELECT amount, display_name, id FROM user_profiles WHERE user_id = ?', (user_id,))
                current_balance = cursor.fetchone()
                if current_balance:
                    user_balance, user_name, game_id = current_balance
                    new_balance = float(user_balance) + data['net_change']
                    cursor.execute('UPDATE user_profiles SET amount = ?, backup_amount = ? WHERE user_id = ?',
                                   (new_balance, new_balance, user_id))
                    data['new_balance'] = new_balance
                    data['name'] = user_name
                    data['game_id'] = game_id

                total_payout += data['net_change']

            # Update total profit for the round
            cursor.execute('UPDATE result SET profit = ? WHERE round = ?', (total_payout * -1, round_value))
            conn.commit()

            # Create rewards summary
            rewards_summary = []
            for user_id, data in user_results.items():
                new_balance = data['new_balance']
                net_change = data['net_change']
                sign = '+' if net_change > 0 else ''
                rewards_summary.append(f"{data['game_id']}){data['name']} |{sign}{int(net_change)} = {int(new_balance)}")

            return "\n".join(rewards_summary)

    except Exception as e:
        print(f"Error during calculation: {str(e)}")
        return '200'

def store_play(user_id, round_value, user_play, bet_dict,current_ratio,sub_round, amount_play=0):
    # print(bet_dict)

    # numbers = ''
    # numbers = ','.join(map(str, bet_dict['numbers'])) 
    global timer_started
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO play (user_id, round, user_play, chicken, bet_ratio,sub_round, amount_play)
        VALUES (?, ?, ?, ?, ?, ?,?)
    ''', (user_id, round_value, user_play, bet_dict['chicken'], current_ratio,sub_round, bet_dict['amount']))
    conn.commit()
    conn.close()
    with lock:
        if not timer_started:
            timer_started = True
            socketio.start_background_task(start_timer)
            
            
    # print(bet_dict)

def calculate_new_bet_with_ratio(user_id,bet_info):
    round_value = get_present_round()

    with sqlite3.connect(db_name) as conn:
        cursor=conn.cursor()
        cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ? AND user_id = ?', (round_value,user_id))
        records = cursor.fetchall()    
    user_totals = {'ด': 0, 'ง': 0}
    new_record =[(user_id,bet_info['chicken'],bet_ratio,bet_info['amount'])]
    records += new_record

    for record in records:
        user_id, chicken, bet_ratio, amount_play = record
        amount = float(amount_play)
        # Split and convert bet ratios
        parts = bet_ratio.split('/')
        bet1 = float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
        bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)
        main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
        if main_score =='ส':
            main_score =='ด'
        sp = 1.0
        sp2 = 1.0
        reward_main_score = bet2/bet1
        lose_main_score = 1
        reward_second_score = 1 
        lose_second_score = (bet2+0.2)/bet1
        if bet1 == 0.9 and bet2 == 0.9:
            reward_main_score = 0.9
            reward_second_score = 0.9
            lose_second_score = 1
        elif bet1 ==1 and bet2 ==0.1:
            lose_second_score = 0.1/(bet1-0.5)
        elif bet1 > 1 and bet2 ==0.1:
            lose_second_score = 0.1/(bet1-0.5)
        elif bet1 ==1 and bet2 == 0.9:
            lose_second_score = 1
        elif bet1 ==1 and bet2 ==0.95:
            lose_second_score= 1
        elif bet1 ==1 and bet2 ==0.85:
            lose_second_score =1

        # Predict for 'ด' and 'ง'
        for result_score in ['ด', 'ง']:
            reward_or_penalty = 0
            if chicken == main_score:
                if result_score == chicken:
                    # Case 1: Reward when the bet matches the main score
                    reward_or_penalty = amount * reward_main_score
                else:
                    # Case 1: Penalty when the bet loses with the main score
                    reward_or_penalty = -amount
            else:
                if result_score == chicken:
                    # Case 2: Reward when the result matches but not the main score
                    reward_or_penalty = amount * reward_second_score
                else:
                    # Case 2: Penalty when neither the bet nor the result matches
                    reward_or_penalty = -amount * lose_second_score

            # Accumulate the profit or loss for the result
            user_totals[result_score] += reward_or_penalty    
    return user_totals

def calculate_bet_with_ratio(user_id):
    round_value = get_present_round()

    with sqlite3.connect(db_name) as conn:
        cursor=conn.cursor()
        cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ? AND user_id = ?', (round_value,user_id))
        records = cursor.fetchall()    
    user_totals = {'ด': 0, 'ง': 0}
    for record in records:
        user_id, chicken, bet_ratio, amount_play = record
        amount = float(amount_play)
        # Split and convert bet ratios
        parts = bet_ratio.split('/')
        bet1 = float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
        bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)
        main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
        if main_score =='ส':
            main_score =='ด'
        sp = 1.0
        sp2 = 1.0
        reward_main_score = bet2/bet1
        lose_main_score = 1
        reward_second_score = 1 
        lose_second_score = (bet2+0.2)/bet1
        if bet1 == 0.9 and bet2 == 0.9:
            reward_main_score = 0.9
            reward_second_score = 0.9
            lose_second_score = 1
        elif bet1 ==1 and bet2 ==0.1:
            lose_second_score = 0.1/(bet1-0.5)
        elif bet1 > 1 and bet2 ==0.1:
            lose_second_score = 0.1/(bet1-0.5)
        elif bet1 ==1 and bet2 == 0.9:
            lose_second_score = 1
        elif bet1 ==1 and bet2 ==0.95:
            lose_second_score= 1
        elif bet1 ==1 and bet2 ==0.85:
            lose_second_score =1

        # Predict for 'ด' and 'ง'
        for result_score in ['ด', 'ง']:
            reward_or_penalty = 0
            if chicken == main_score:
                if result_score == chicken:
                    # Case 1: Reward when the bet matches the main score
                    reward_or_penalty = amount * reward_main_score
                else:
                    # Case 1: Penalty when the bet loses with the main score
                    reward_or_penalty = -amount
            else:
                if result_score == chicken:
                    # Case 2: Reward when the result matches but not the main score
                    reward_or_penalty = amount * reward_second_score
                else:
                    # Case 2: Penalty when neither the bet nor the result matches
                    reward_or_penalty = -amount * lose_second_score

            # Accumulate the profit or loss for the result
            user_totals[result_score] += reward_or_penalty 
    return user_totals   

def calculate_and_update_rewards(round_value):
    """
    Fetch all records for a given round, calculate total rewards or penalties for each user,
    update their balances, and return a summary.

    Parameters:
    round_value (int): The round number for which to calculate and update rewards.

    Returns:
    str: A summary of the total rewards and penalties for each user.
    """
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()

            # Fetch records for the given round from the play table
            cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ?', (round_value,))
            records = cursor.fetchall()
            user_totals = {}
            cursor.execute('SELECT chicken FROM result WHERE round = ? ORDER BY id DESC LIMIT 1', (round_value,))
            result_row = cursor.fetchone()
            if not result_row[0]:
                cursor.execute('UPDATE result SET profit = ? WHERE round = ?', ('0', round_value))
                conn.commit()
                return "No result found"
            if not records:
                cursor.execute('UPDATE result SET profit = ? WHERE round = ?', ('0', round_value))
                conn.commit()
                return "No records found for this round."
            for record in records:
                user_id, chicken, bet_ratio, amount_play = record
                amount = float(amount_play)

 
                if not result_row:
                    continue
                if result_row[0]=='ส':
                    amount = 0
                result_score = result_row[0]
                
                # Calculate reward or penalty
                parts = bet_ratio.split('/')
                bet1= float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
                bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)
                main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
                if main_score == 'ส':
                    main_score ='ด'
                sp = 1.0
                sp2 = 1.0
                reward_main_score = bet2/bet1
                lose_main_score = 1
                reward_second_score = 1 
                lose_second_score = (bet2+0.2)/bet1
                if bet1 == 0.9 and bet2 == 0.9:
                    reward_main_score = 0.9
                    reward_second_score = 0.9
                    lose_second_score = 1
                elif bet1 ==1 and bet2 ==0.1:
                    lose_second_score = 0.1/(bet1-0.5)
                elif bet1 > 1 and bet2 ==0.1:
                    lose_second_score = 0.1/(bet1-0.5)
                elif bet1 ==1 and bet2 == 0.9:
                    lose_second_score = 1
                elif bet1 ==1 and bet2 ==0.95:
                    lose_second_score= 1
                elif bet1 ==1 and bet2 ==0.85:
                    lose_second_score =1

                reward_or_penalty = 0
                if chicken == main_score:
                    if result_score == chicken:
                        # Case 1: Reward when the bet matches the main score
                        reward_or_penalty = amount * reward_main_score
                    else:
                        # Case 1: Penalty when the bet loses with the main score
                        reward_or_penalty = -amount  
                else:
                    if result_score == chicken:
                        # Case 2: Reward when the result matches but not the main score
                        reward_or_penalty = amount * reward_second_score
                    else:
                        # Case 2: Penalty when neither the bet nor the result matches
                        reward_or_penalty = -amount * lose_second_score
                # Accumulate the total for each user
                if user_id not in user_totals:
                    user_totals[user_id] = 0
                if reward_or_penalty > 0:
                    reward_or_penalty = math.floor(reward_or_penalty)
                elif reward_or_penalty <0:
                    reward_or_penalty = math.ceil(reward_or_penalty)
                user_totals[user_id] += reward_or_penalty

            # Update the user's balance in the database and create the summary
            rewards_summary = []
            for user_id, total_reward in user_totals.items():
                cursor.execute('SELECT amount,id,display_name FROM user_profiles WHERE user_id = ?', (user_id,))
                current_balance = cursor.fetchone()

                if current_balance:
                    
                    if total_reward > 0 :
                        total_reward = math.floor(total_reward)
                        operation = '+'
                    else:
                        total_reward = math.ceil(total_reward)
                        operation = '-'
                    new_balance = float(current_balance[0]) + math.floor(total_reward)
                    update_balance(current_balance[1],abs(total_reward),operation)
                    
                    # cursor.execute('UPDATE user_profiles SET amount = ?, backup_amount = ? WHERE user_id = ?',
                    #                (new_balance, new_balance, user_id))
                    #conn.commit()
                    sign = '+' if total_reward > 0 else ''
                    rewards_summary.append(f"{current_balance[1]}){current_balance[2]} | {sign}{int(total_reward)} = {int(new_balance)}")
                else:
                    rewards_summary.append(f"{current_balance[1]}){current_balance[2]} | Error: User not found")
            total_profit = sum(user_totals.values())
            total_profit = total_profit*(-1)
            cursor.execute('UPDATE result SET profit = ? WHERE round = ?', (total_profit, round_value))
            conn.commit()
            return "\n".join(rewards_summary)

    except Exception as e:
        return f"Error during calculation: {str(e)}"

def recalculate_and_update_rewards(round_value):
    """
    Fetch all records for a given round, calculate total rewards or penalties for each user,
    update their balances, and return a summary.

    Parameters:
    round_value (int): The round number for which to calculate and update rewards.

    Returns:
    str: A summary of the total rewards and penalties for each user.
    """
    try:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()

            # Fetch records for the given round from the play table
            cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ?', (round_value,))
            records = cursor.fetchall()
            user_totals = {}
            cursor.execute('SELECT chicken FROM result WHERE round = ? ORDER BY id DESC LIMIT 1', (round_value,))
            result_row = cursor.fetchone()
            if not result_row[0]:
                cursor.execute('UPDATE result SET profit = ? WHERE round = ?', ('0', round_value))
                conn.commit()
                return "No result found"
            if not records:
                cursor.execute('UPDATE result SET profit = ? WHERE round = ?', ('0', round_value))
                conn.commit()
                return "No records found for this round."
            for record in records:
                user_id, chicken, bet_ratio, amount_play = record
                amount = float(amount_play)

                # Simulate getting the actual result score (e.g., from a game result table)
                # cursor.execute('SELECT chicken FROM result WHERE round = ? ORDER BY id DESC LIMIT 1', (round_value,))
                # result_row = cursor.fetchone()
                if not result_row:
                    continue
                if result_row[0]=='ส':
                    amount = 0
                result_score = result_row[0]
                
                # Calculate reward or penalty
                parts = bet_ratio.split('/')
                bet1= float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
                bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)
                main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
                if main_score == 'ส':
                    main_score ='ด'
                sp = 1.0
                sp2 = 1.0
                reward_main_score = bet2/bet1
                lose_main_score = 1
                reward_second_score = 1 
                lose_second_score = (bet2+0.2)/bet1
                if bet1 == 0.9 and bet2 == 0.9:
                    reward_main_score = 0.9
                    reward_second_score = 0.9
                    lose_second_score = 1
                elif bet1 ==1 and bet2 ==0.1:
                    lose_second_score = 0.1/(bet1-0.5)
                elif bet1 > 1 and bet2 ==0.1:
                    lose_second_score = 0.1/(bet1-0.5)
                elif bet1 ==1 and bet2 == 0.9:
                    lose_second_score = 1
                elif bet1 ==1 and bet2 ==0.95:
                    lose_second_score= 1
                elif bet1 ==1 and bet2 ==0.85:
                    lose_second_score =1

                reward_or_penalty = 0
                if chicken == main_score:
                    if result_score == chicken:
                        # Case 1: Reward when the bet matches the main score
                        reward_or_penalty = amount * reward_main_score
                    else:
                        # Case 1: Penalty when the bet loses with the main score
                        reward_or_penalty = -amount  
                else:
                    if result_score == chicken:
                        # Case 2: Reward when the result matches but not the main score
                        reward_or_penalty = amount * reward_second_score
                    else:
                        # Case 2: Penalty when neither the bet nor the result matches
                        reward_or_penalty = -amount * lose_second_score
                # Accumulate the total for each user
                if user_id not in user_totals:
                    user_totals[user_id] = 0
                user_totals[user_id] += -reward_or_penalty

            # Update the user's balance in the database and create the summary
            rewards_summary = []
            for user_id, total_reward in user_totals.items():
                cursor.execute('SELECT amount,id,display_name FROM user_profiles WHERE user_id = ?', (user_id,))
                current_balance = cursor.fetchone()

                if current_balance:
                    
                    if total_reward > 0 :
                        total_reward = math.ceil(total_reward)
                        operation = '+'
                    else:
                        total_reward = math.floor(total_reward)
                        operation = '-'
                    new_balance = float(current_balance[0]) + math.ceil(total_reward)
                    update_balance(current_balance[1],abs(total_reward),operation,admin_id='recall')
                    # cursor.execute('UPDATE user_profiles SET amount = ?, backup_amount = ? WHERE user_id = ?',
                    #                (new_balance, new_balance, user_id))
                    # conn.commit()
                    sign = '+' if total_reward > 0 else ''
                    rewards_summary.append(f"{current_balance[1]}){current_balance[2]} | {sign}{int(total_reward)} = {int(new_balance)}")
                else:
                    rewards_summary.append(f"{current_balance[1]}){current_balance[2]} | Error: User not found")
            total_profit = sum(user_totals.values())
            total_profit = total_profit*(-1)
            # cursor.execute('UPDATE result SET profit = ? WHERE round = ?', (total_profit, round_value))
            # conn.commit()
            return "\n".join(rewards_summary)

    except Exception as e:
        return f"Error during calculation: {str(e)}"

def generate_random_string():
    letters = string.ascii_letters  # includes both uppercase and lowercase letters
    return ''.join(random.choice(letters) for _ in range(5))

def get_img_setting(d=0):
    global link_acc_room,link_play_room,acc_pic,game_name,ac_msg,open_pic,close_pic,red_win,blue_win,tie,how_to_play_pic,msg_how_to_play,acc_num
    if d == 0:
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT link_acc_room,link_play_room,acc_pic,game_name,ac_msg,open_pic,close_pic,red_win,blue_win,tie,how_to_play_pic,msg_how_to_play,acc_num FROM settings2 WHERE id =1')
            data = cursor.fetchone()
            setting = {
                "link_acc_room":data[0].replace('\\','/'),
                "link_play_room":data[1].replace('\\','/'),
                "acc_num":data[12].replace('\\','/'),
                "acc_pic":data[2].replace('\\','/'),
                "game_name":data[3].replace('\\','/'),
                "ac_msg":data[4].replace('\\','/'),
                "open_pic":data[5].replace('\\','/'),
                "close_pic":data[6].replace('\\','/'),
                "red_win":data[7].replace('\\','/'),
                "blue_win":data[8].replace('\\','/'),
                "tie":data[9].replace('\\','/'),
                "how_to_play_pic":data[10].replace('\\','/'),
                "msg_how_to_play":data[11].replace('\\','/')
            }
            link_acc_room=data[0].replace('\\','/')
            link_play_room=data[1].replace('\\','/')
            acc_pic=data[2].replace('\\','/')
            game_name=data[3].replace('\\','/')
            ac_msg=data[4].replace('\\','/')
            open_pic=data[5].replace('\\','/')
            close_pic=data[6].replace('\\','/')
            red_win=data[7].replace('\\','/')
            blue_win=data[8].replace('\\','/')
            tie=data[9].replace('\\','/')
            how_to_play_pic=data[10].replace('\\','/')
            msg_how_to_play=data[11].replace('\\','/')
            acc_num = data[12].replace('\\','/')
            return setting
    elif d == 1:
        link_acc_room="""ห้องฝาก-ถอน\nxxx\n👈จิ้มเลย ลิ้งเข้าห้องฝาก"""
        link_play_room="""ห้องเล่น \n xx\n👈จิ้มเลย ลิ้งเข้าห้องเล่น"""
        acc_pic=f"pictures/ac5.jpg"
        game_name='ufa5220 ทีเด็ดนายหัว'
        ac_msg="""ฝาก ห้ามนำสลิปส่งในกลุ่ม\nให้แจ้งผ่านไลน์นี้เท่านั้น\n👇🏻👇🏻👇🏻👇🏻👇🏻\nhttps://lin.ee/JY73X9U"""
        open_pic=f"pictures/open.jpg"
        close_pic=f"pictures/close.jpg"
        red_win=f"pictures/red.jpg"
        blue_win=f"pictures/blue.jpg"
        tie=f"pictures/tie.jpg"
        how_to_play_pic=f"pictures/how_to_play.jpg"
        msg_how_to_play=f"วิธีการเล่นมีดังต่อไปนี้"
        acc_num= '8112908061'
def calculate_rewards(type_data=1,round=1):
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT round FROM round')
        rounds = cursor.fetchall()

        rewards_summary = []
        grouped_totals = {}  # Maintain grouped totals globally across all rounds
        if type_data != 1:
            rounds = [round]
        try:
            for round in rounds:
                round_value = round[0]

                # Fetch records for the current round
                cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ?', (round_value,))
                records = cursor.fetchall()

                if not records:
                    continue

                # Fetch result for the current round
                cursor.execute('SELECT chicken FROM result WHERE round = ? ORDER BY id DESC LIMIT 1', (round_value,))
                result_row = cursor.fetchone()

                if not result_row:
                    continue

                user_totals = {}  # Reset user totals for each round
                user_amount_play = {}
                # Process records
                for record in records:
                    user_id, chicken, bet_ratio, amount_play = record
                    amount = float(amount_play)
                    result_score = result_row[0]

                    if result_score == 'ส':  # Handle special case
                        amount = 0

                    # Parse bet ratios
                    parts = bet_ratio.split('/')
                    bet1 = float(parts[1]) / 10
                    bet2 = float(parts[2]) / 10
                    main_score = parts[0][0]
                    if main_score =='ส':
                        main_score =='ด'
                    sp = 1.0
                    sp2 = 1.0
                    reward_main_score = bet2/bet1
                    lose_main_score = 1
                    reward_second_score = 1 
                    lose_second_score = (bet2+0.2)/bet1
                    if bet1 == 0.9 and bet2 == 0.9:
                        reward_main_score = 0.9
                        reward_second_score = 0.9
                        lose_second_score = 1
                    elif bet1 ==1 and bet2 ==0.1:
                        lose_second_score = 0.1/(bet1-0.5)
                    elif bet1 > 1 and bet2 ==0.1:
                        lose_second_score = 0.1/(bet1-0.5)
                    elif bet1 ==1 and bet2 == 0.9:
                        lose_second_score = 1
                    elif bet1 ==1 and bet2 ==0.95:
                        lose_second_score= 1
                    elif bet1 ==1 and bet2 ==0.85:
                        lose_second_score =1

                    for result_score in ['ด', 'ง']:
                        reward_or_penalty = 0
                        if chicken == main_score:
                            if result_score == chicken:
                                # Case 1: Reward when the bet matches the main score
                                reward_or_penalty = amount * reward_main_score
                            else:
                                # Case 1: Penalty when the bet loses with the main score
                                reward_or_penalty = -amount
                        else:
                            if result_score == chicken:
                                # Case 2: Reward when the result matches but not the main score
                                reward_or_penalty = amount * reward_second_score
                            else:
                                # Case 2: Penalty when neither the bet nor the result matches
                                reward_or_penalty = -amount * lose_second_score

                    # Accumulate user totals
                    user_totals[user_id] = user_totals.get(user_id, 0) + reward_or_penalty
                    if type_data !=1:
                        user_amount_play[user_id] = {'amount_play':user_amount_play.get(user_id,0).get('amount_play',0)+amount,
                                                     'reward':user_amount_play.get(user_id, 0).get('reward',0) + reward_or_penalty}
                        print(user_amount_play)

                # Update balances and group totals
                for user_id, total_reward in user_totals.items():
                    cursor.execute('SELECT amount, id, display_name FROM user_profiles WHERE user_id = ?', (user_id,))
                    current_balance = cursor.fetchone()

                    if current_balance:
                        amount, identifier, display_name = current_balance
                        new_balance = float(amount) + math.floor(total_reward)

                        # Group totals by identifier
                        if identifier not in grouped_totals:
                            grouped_totals[identifier] = {"total_reward": 0, "display_name": display_name, "new_balance": float(amount)}

                        # Accumulate grouped totals
                        grouped_totals[identifier]["total_reward"] += total_reward
                        grouped_totals[identifier]["new_balance"] = float(amount) + grouped_totals[identifier]["total_reward"]
                        grouped_totals[identifier]["amount"] = amount



            # Summarize grouped results
            for identifier, data in grouped_totals.items():
                total_reward = data["total_reward"]
                new_balance = data["new_balance"]
                display_name = data["display_name"]
                sign = '+' if total_reward > 0 else ''
                rewards_summary.append(f"{identifier}) {display_name} | {sign}{int(total_reward)} = {data['amount']}")
            
            if type_data != 1: 
                return grouped_totals
    
            else:
                return "\n".join(rewards_summary)
        except Exception as e:
            print(f"Error during calculation: {str(e)}")
            return 0

def calculate_rewards1(type_data=1, round=1,limit=None, offset=None):
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT round FROM round')
        rounds = cursor.fetchall()

        rewards_summary = []
        grouped_totals = {}  # Maintain grouped totals globally across all rounds
        formatted_user_data = []  # List to store formatted data for type_data != 1

        if type_data != 1:
            rounds = [(round,)]  # Ensure rounds is a list of tuples

        try:
            for round in rounds:
                round_value = round[0]

                # Fetch records for the current round
                cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ?', (round_value,))
                records = cursor.fetchall()

                if not records:
                    continue

                # Fetch result for the current round
                cursor.execute('SELECT chicken FROM result WHERE round = ? ORDER BY id DESC LIMIT 1', (round_value,))
                result_row = cursor.fetchone()

                if not result_row:
                    continue

                user_totals = {}  # Reset user totals for each round
                user_amount_play = {}  # Reset user amount play details

                # Process records
                for record in records:
                    user_id, chicken, bet_ratio, amount_play = record
                    amount = float(amount_play)
                    result_score = result_row[0]

                    if result_score == 'ส':  # Handle special case
                        amount = 0

                    # Parse bet ratios
                    parts = bet_ratio.split('/')
                    bet1 = float(parts[1]) / 10
                    bet2 = float(parts[2]) / 10
                    main_score = parts[0][0]
                    if main_score =='ส':
                        main_score =='ด'
                    sp = 1.0
                    sp2 = 1.0
                    reward_main_score = bet2/bet1
                    lose_main_score = 1
                    reward_second_score = 1 
                    lose_second_score = (bet2+0.2)/bet1
                    if bet1 == 0.9 and bet2 == 0.9:
                        reward_main_score = 0.9
                        reward_second_score = 0.9
                        lose_second_score = 1
                    elif bet1 ==1 and bet2 ==0.1:
                        lose_second_score = 0.1/(bet1-0.5)
                    elif bet1 > 1 and bet2 ==0.1:
                        lose_second_score = 0.1/(bet1-0.5)
                    elif bet1 ==1 and bet2 == 0.9:
                        lose_second_score = 1
                    elif bet1 ==1 and bet2 ==0.95:
                        lose_second_score= 1
                    elif bet1 ==1 and bet2 ==0.85:
                        lose_second_score =1

                    for result_score in ['ด', 'ง']:
                        reward_or_penalty = 0
                        if chicken == main_score:
                            if result_score == chicken:
                                # Case 1: Reward when the bet matches the main score
                                reward_or_penalty = amount * reward_main_score
                            else:
                                # Case 1: Penalty when the bet loses with the main score
                                reward_or_penalty = -amount
                        else:
                            if result_score == chicken:
                                # Case 2: Reward when the result matches but not the main score
                                reward_or_penalty = amount * reward_second_score
                            else:
                                # Case 2: Penalty when neither the bet nor the result matches
                                reward_or_penalty = -amount * lose_second_score

                    # Accumulate user totals
                    user_totals[user_id] = user_totals.get(user_id, 0) + reward_or_penalty

                    if type_data != 1:
                        if user_id not in user_amount_play:
                            user_amount_play[user_id] = {"amount_play": 0, "reward": 0}
                        user_amount_play[user_id]["amount_play"] += amount
                        user_amount_play[user_id]["reward"] += reward_or_penalty

                # Format data for type_data != 1
                if type_data != 1:
                    for user_id, details in user_amount_play.items():
                        # Fetch user_name (display_name) from user_profiles
                        cursor.execute('SELECT display_name,amount,id FROM user_profiles WHERE user_id = ?', (user_id,))
                        result = cursor.fetchone()  # Fetch the result
                        user_name = result[0] if result else "Unknown"  # Handle None safely

                        formatted_user_data.append({
                            "user_id": user_id,
                            "username": user_name,
                            "amount_play": details["amount_play"],
                            "reward": details["reward"],
                            "balance": result[1],
                            'game_id':result[2]
                        })

            if type_data != 1:
                total_records = len(formatted_user_data)
                total_pages = math.ceil(total_records / limit) if limit else 1
                paginated_data = formatted_user_data[offset:offset + limit] if limit is not None and offset is not None else formatted_user_data
                # print(total_pages)
                # print(total_records)
                # print(limit)
                # print('###############')
                # print(offset)
                return {
                    "data": paginated_data,
                    "pagination": {
                        
                        "total_records": total_records,
                        "total_pages": total_pages,
                        "limit": limit,
                        "offset": offset,
                    }
                }
           
            return "\n".join(rewards_summary)

        except Exception as e:
            print(f"Error during calculation: {str(e)}")
            return {"error": "Calculation failed", "details": str(e)}
        
def send_reply(reply_token, message):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Channel_access_token}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code

def send_reply2(reply_token, message,msg2):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Channel_access_token}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": message
            },{
                "type": "text",
                "text": msg2
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code

def send_msg_pic_msg1(reply_token,msg1,pic,msg2):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Channel_access_token}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": msg1
            },
            {
                "type": "image",
                "originalContentUrl":pic,
                "previewImageUrl": pic
            },
            {
                "type": "text",
                "text": msg2
            }

        ]
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.text)
    return response.status_code

def send_reply_with_picture(reply_token, message,pic_path,alt_text,flex_contents):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Channel_access_token}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "flex",
                "altText": alt_text,
                "contents": flex_contents
            }
            ,{
                "type": "text",
                "text": message
            },
            {
                "type": "image",
                "originalContentUrl":pic_path,
                "previewImageUrl": pic_path
            }
            
            # {
            #     "type": 'image',
            #     "url":pic_path2
            # }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.text)
    return response.status_code

def send_close_msg_pic(reply_token, message,pic_path,bubbles):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Channel_access_token}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": message
            },
            {
                "type": "image",
                "originalContentUrl":pic_path,
                "previewImageUrl": pic_path
            },
            {
                "type": "flex",
                "altText": "สรุปยอด",
                "contents":{
                "type": "carousel",
                "contents":bubbles}
            }

        ]
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.text)
    return response.status_code

def store_ratio(ratio,round_value):
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        # Check if `group_id` exists
        maxbet = ratio.split('/')[-1]
        ratio_pure = f'{ratio.split("/")[0]}/{ratio.split("/")[1]}/{ratio.split("/")[2]}'
        cursor.execute('UPDATE round SET max_bet = ?, bet_ratio = ? WHERE round = ?', (maxbet, ratio_pure, round_value))
        conn.commit()

def send_msg_pic(reply_token, message,pic_path):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Channel_access_token}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": message
            },
            {
                "type": "image",
                "originalContentUrl":pic_path,
                "previewImageUrl": pic_path
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.text)
    return response.status_code

def send_msg_pic1(reply_token, message,pic_path,pic_path1):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Channel_access_token}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "image",
                "originalContentUrl":pic_path,
                "previewImageUrl": pic_path
            },
            {
                "type": "text",
                "text": message
            },
            {
                "type": "image",
                "originalContentUrl":pic_path1,
                "previewImageUrl": pic_path1
            }

        ]
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.text)
    return response.status_code

def get_current_bet_ratio(round):
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT bet_ratio FROM round WHERE round = ?',(round,))
        ratio = cursor.fetchone()
        if ratio:
            return ratio[0]
        return None

def send_reply_pic(reply_token,pic_path):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Channel_access_token}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [

            {
                "type": "image",
                "originalContentUrl":pic_path,
                "previewImageUrl": pic_path
            }

        ]
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.text)
    return response.status_code

def send_flex_reply(reply_token, alt_text, flex_contents):
    url = 'https://api.line.me/v2/bot/message/reply'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Channel_access_token}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "flex",
                "altText": alt_text,
                "contents": flex_contents
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    print(response.text)
    return response.status_code

def get_current_sub_round_bet():
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT round,sub_round,bet_ratio,max_bet FROM round ORDER BY id DESC LIMIT 1')
        current_round = cursor.fetchone()
        if current_round:
            round_value = current_round[0]
            sub_round = current_round[1]
            bet_ratio = current_round[2]
            max_bet = current_round[3]
            bet_setting = bet_ratio+'/'+str(max_bet)
        else:
            reply_message = "Error: No round information available."
            # send_reply(reply_token, reply_message)
            return reply_message,'','',''

    # Retrieve all bets for the current round
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_profiles.id, user_profiles.display_name , play.user_play, play.amount_play,play.chicken
            FROM play
            JOIN user_profiles ON play.user_id = user_profiles.user_id
            WHERE play.round = ? AND play.sub_round = ?
        ''', (round_value,sub_round))
        bets = cursor.fetchall()

    # Split bets into chunks of 20 for each bubble
    grouped_bets = {}
    for bet in bets:
        user_id = bet[0]
        display_name = bet[1]
        user_play = bet[2]
        amount_play = bet[3]
        chicken = bet[4]
        if user_id not in grouped_bets:
            grouped_bets[user_id] = {
                "id": user_id,
                "display_name": display_name,
                "user_play": [user_play],
                "amount_play": [amount_play],
                "chicken":chicken
            }
        else:
            grouped_bets[user_id]["user_play"].append(user_play)
            grouped_bets[user_id]["amount_play"].append(amount_play)

    # Convert grouped bets to a list of tuples
    grouped_bets_list = [
        (bet_data["id"], bet_data["display_name"], bet_data["user_play"], bet_data["amount_play"],bet_data["chicken"])
        for bet_data in grouped_bets.values()
    ]
    if grouped_bets_list ==[]:
        reply_message = 'ยังไม่มียอดแทง'
        return reply_message,'','',''

    return '',bets,bet_setting,round_value

def create_user_balance_bubble(id,user_name,amount,user_pic):
    if not user_pic:
        user_pic = "https://sprofile.line-scdn.net/0hUqVPFxHkCl57KRsXuz90IQt5CTRYWFNMAhsSPEZ8UWxEEEkMA05HPE4gUW4STEkMB0cQMEd9A2h3On04ZX_2anwZV29HHkkLU0tBug"
    bubble = {
  "type": "bubble",
  "body": {
    "type": "box",
    "layout": "horizontal",
    "contents": [
      {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "image",
            "url": user_pic,
            "align": "start",
            "size": "xs"
          }
        ],
        "width": "60px"
      },
      {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "text",
            "text": f"ID: {id}  {user_name}",
            "gravity": "bottom",
            "weight": "bold"
          },
          {
            "type": "text",
            "text": f"คงเหลือ {amount} บ.",
            "gravity": "bottom",
            "weight": "bold"
          }
        ],
        "paddingTop": "10px",
        "paddingStart": "15px"
      }
    ],
    "backgroundColor": "#FFFFFF"
  }
}
    return bubble


def create_user_welcome_bubble(id,user_name,amount,user_pic):
    if not user_pic:
        user_pic = "https://sprofile.line-scdn.net/0hUqVPFxHkCl57KRsXuz90IQt5CTRYWFNMAhsSPEZ8UWxEEEkMA05HPE4gUW4STEkMB0cQMEd9A2h3On04ZX_2anwZV29HHkkLU0tBug"
    bubble = {
  "type": "bubble",
  "hero": {
    "type": "box",
    "layout": "vertical",
    "contents": [
      {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "text",
            "text": "สมาชิกใหม่",
            "size": "xxl",
            "color": "#FFFFFF",
            "margin": "20px"
          }
 
        ],
        "height": "70px",
        "alignItems": "center",
          "justifyContent": "center"
      }
    ],
    "background": {
      "type": "linearGradient",
      "angle": "90deg",
      "startColor": "#FF0000",
      "endColor": "#0000FF"
    }
  },
  "body": {
    "type": "box",
    "layout": "horizontal",
    "contents": [
      {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "image",
            "url": user_pic,
            "align": "start",
            "size": "xs"
          }
        ],
        "width": "60px"
      },
      {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "text",
            "text": f"ID: {id}  {user_name}",
            "gravity": "bottom",
            "weight": "bold"
          },
          {
            "type": "text",
            "text": f"คงเหลือ {amount} บ.",
            "gravity": "bottom",
            "weight": "bold"
          }
        ],
        "paddingTop": "10px",
        "paddingStart": "15px"
      }
    ],
    "backgroundColor": "#FFFFFF"
  }
}
    return bubble

@app.route('/pictures/<filename>',methods=['GET'])
def send_pic (filename):
    return send_from_directory('pic',filename)


PWD = generate_order_id(k=15)
PWD_return = generate_order_id(k=15)
PWD_remove = generate_order_id(k=15)
PWD_cr = generate_order_id(k=15)
@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    global PWD
    global PWD_return
    global PWD_remove
    global PWD_cr
    global link_acc_room,link_play_room,acc_pic,game_name,ac_msg,open_pic,close_pic,red_win,blue_win,tie,how_to_play_pic,msg_how_to_play,acc_num
    
    if request.method == 'POST':
        payload = request.json
        print(payload)
        if not payload['events']:
            return '200'
        for event in payload['events']:
            if event['type'] == 'memberJoined':
                group_id = event['source'].get('groupId')
                joined_members = event['joined']['members']
                reply_token = event['replyToken']
                for member in joined_members:
                    user_id = member.get('userId')
                    if user_id:
                        # Make API call to get user profile
                        headers = {
                            'Authorization': f'Bearer {Channel_access_token}'
                        }
                        response = requests.get(
                            f'https://api.line.me/v2/bot/group/{group_id}/member/{user_id}',
                            headers=headers
                        )
                        if response.status_code == 200:
                            profile_data = response.json()
                            store_user_profile(profile_data)
                            display_name = profile_data.get('displayName', 'Unknown')
                            if display_name != 'Unknown':
                                with sqlite3.connect(db_name) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('SELECT id,display_name,picture_url,amount FROM user_profiles WHERE user_id= ?', (user_id,))
                                    user_data = cursor.fetchone()
                                    u_id,display_name,picture_url,amount = user_data
                                bubble = create_user_welcome_bubble(u_id,display_name,amount,picture_url)
                                flex_message = {
                                "type": "carousel",
                                "contents": [bubble]
                            }

                                send_flex_reply(reply_token, f"Hello User", flex_message)

                return '200'
            #user_id = event['source']['userId']
            user_id = event['source'].get('userId',None)
            group_id = event['source'].get('groupId', None)
            if not group_id:
                return '200'
            reply_token = event['replyToken']
            
            if user_id =='U29d27e052f33e735976b76560e4c0d92':
                return '200'

            with sqlite3.connect(db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM user_profiles WHERE user_id = ?', (user_id,))
                data = cursor.fetchone()
                
            if not data:
                msg = event['message']['text']
                if 'C' == msg or 'add'==msg:
                    try:
                        user_profile = get_user_profile(user_id)
                        store_user_profile(user_profile)
                        with sqlite3.connect(db_name) as conn:
                            cursor = conn.cursor()
                            cursor.execute('SELECT id , display_name ,amount,picture_url  FROM user_profiles WHERE user_id=?',(user_id,))
                            profile = cursor.fetchone() 
                            cursor.execute('''INSERT INTO admin_group (user_id, role)
                                              VALUES (?,?)''',(user_id,'user'))   
                        # reply_message = f'ID:{profile[0]}) {profile[1]}\n{profile[2]}'
                        bubble = create_user_balance_bubble(profile[0],profile[1],profile[2],profile[3]) 
                        flex_contents = {
                                "type": "carousel",
                                "contents": [bubble]
                            }
                        # send_reply(reply_token,reply_message)
                        send_flex_reply(reply_token,'balance',bubble,flex_contents)
                        return '200'
                    except:
                        reply_message = 'แอดเพื่อนก่อนน้า'
                        send_reply(reply_token,reply_message)
                        return'200'

            if event.get('message','').get('type') =='image':
                with sqlite3.connect(db_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT role FROM admin_group WHERE user_id = ?', (user_id,))
                    role = cursor.fetchone()
                if role[0]=='admin':
                    return '200'
                if not data:
                    user_profile = get_user_profile(user_id)
                    print(user_profile)
                    if user_profile:
                        store_user_profile(user_profile)
                        user_name = user_profile['displayName']
                        print(f"Stored user profile for {user_name}")
                        with sqlite3.connect(db_name) as conn:
                            cursor = conn.cursor()
                            cursor.execute('SELECT id , display_name ,amount  FROM user_profiles WHERE user_id=?',(user_id,))
                            profile = cursor.fetchone() 
                            cursor.execute('''INSERT INTO admin_group (user_id, role)
                                              VALUES (?,?)''',(user_id,'user'))   
                        reply_message = f'ID:{profile[0]}) {profile[1]}\n{profile[2]}'
                else:
                    with sqlite3.connect(db_name) as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT id , display_name ,amount  FROM user_profiles WHERE user_id = ?',(user_id,))
                        profile = cursor.fetchone()    
                    reply_message = f'ID:{profile[0]}) {profile[1]}\n{profile[2]}'
                send_reply(reply_token,reply_message)
                return '200'

            with sqlite3.connect(db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT status,role FROM focus_group WHERE group_id = ?', (group_id,))
                status = cursor.fetchone()
                cursor.execute('SELECT role FROM admin_group WHERE user_id = ?', (user_id,))
                role = cursor.fetchone()
            if user_id == "U924c90198e3dd75025f5db62029ab398" or user_id == "Uafa0e3dc0a95041ee055024ef73d989d" or user_id == 'Ua58aec9a4c24fc4bf1693819028e6dc0' or user_id=='Uafcaccecafd8ed20c0d43fe07b1c7e7a':
                if role[0]=='user':
                    if '!'in event['message']['text']:
                        event['message']['text'] = event['message']['text'][1:]
                        role = ['admin',]
                elif role[0]=='admin':
                    if '@'in event['message']['text']:
                        event['message']['text'] = event['message']['text'][1:]
                        role = ['user',]

            if role[0] == 'admin':
                msg = event['message']['text']
                if "!add_group:" in msg:
                    try:
                        group_role = msg.split(":")[1].strip()
                        group_id = event['source'].get('groupId')
                        if group_role == 'play_room':
                            status = 'closed'
                            game_status = 'Y'
                        elif group_role =='bank_room':
                            status = 'balance'
                            game_status =''
                        elif group_role=='admin_room':
                            status = ''
                            game_status =''
                        if group_id:
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                # Check if `group_id` exists
                                cursor.execute('SELECT 1 FROM focus_group WHERE group_id = ?', (group_id,))
                                exists = cursor.fetchone()

                                if exists:
                                    # Update the existing record
                                    cursor.execute('''
                                        UPDATE focus_group
                                        SET role = ?, status = ? ,game_status= ?
                                        WHERE group_id = ?
                                    ''', (group_role, status, game_status,group_id))
                                else:
                                    # Insert a new record
                                    cursor.execute('''
                                        INSERT INTO focus_group (group_id, role, status,game_status)
                                        VALUES (?, ?, ?,?)
                                    ''', (group_id, group_role, status,game_status))
                                
                                conn.commit()
                            reply_message = f"Group {group_id} added with role: {group_role}"
                        else:
                            reply_message = "Error: Group ID not found."

                    except Exception as e:
                        reply_message = f"Error adding group: {str(e)}"

                    send_reply(reply_token, reply_message)
                    return '200'
            
                elif "!add_admin:" in msg:
                    game_id = msg.split(':')[1]
                    with sqlite3.connect(db_name) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''SELECT user_id,display_name FROM user_profiles WHERE id = ?''',(game_id,))
                        u_id = cursor.fetchone()
                        if u_id:
                            user_name = u_id[1]
                            u_id = u_id[0]
                        cursor.execute('SELECT user_id FROM admin_group WHERE user_id = ?', (u_id,))
                        existing_user = cursor.fetchone()

                        if existing_user:
                            # Update the existing user record
                            print('user_exits')
                            cursor.execute('''
                                UPDATE admin_group
                                SET role = ?
                                WHERE user_id = ?
                            ''', ('admin', u_id))
                        else:
                            # Insert a new user record
                            pass
                        conn.commit()
                        reply_message = f"ตั้งให้ {user_name}เป็นแอดมิน เรียบร้อย"
                        send_reply(reply_token,reply_message)
                    return '200'
                elif "!rm_admin:" in msg:
                    game_id = msg.split(':')[1]
                    with sqlite3.connect(db_name) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''SELECT user_id,display_name FROM user_profiles WHERE id = ?''',(game_id,))
                        u_id = cursor.fetchone()
                        if u_id:
                            user_name = u_id[1]
                            u_id = u_id[0]
                        cursor.execute('SELECT user_id FROM admin_group WHERE user_id = ?', (u_id,))
                        existing_user = cursor.fetchone()

                        if existing_user:
                            # Update the existing user record
                            print('user_exits')
                            cursor.execute('''
                                UPDATE admin_group
                                SET role = ?
                                WHERE user_id = ?
                            ''', ('user', u_id))
                        else:
                            # Insert a new user record
                            pass
                        conn.commit()
                        reply_message = f"ตั้งให้ {user_name}เป็นยูสเซอร์ เรียบร้อย"
                        send_reply(reply_token,reply_message)
                    return '200'
                        
            if status[1] == 'play_room':
                
                if role and role[0] == 'admin':

                    msg = event['message']['text']
                    
                    if '$' in msg:
                        try:
                            operation = '+' if '+' in msg else '-'
                            parts = msg.replace('$', '').replace('+', ' ').replace('-', ' ').split()
                            uid = parts[0]
                            amount = float(parts[1])
                           
                            new_balance = update_balance(uid, amount, operation,user_id)
                            try:
                                reply_message = new_balance['reply']
                                send_reply(reply_token, reply_message)
                                return '200'
                            except:
                                pass
                            if new_balance is not None:
                                reply_message = f'User ID: {uid} \nNew Balance: {new_balance:.2f} ฿'
                            else:
                                reply_message = 'User ID not found.'
                        except Exception as e:
                            reply_message = f'Error processing the request: {str(e)}'
                        send_reply(reply_token, reply_message)
                        return '200'
                                 
                    elif 'A' == msg:
                        try:
                            # Fetch the current round from the database
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT round,sub_round,bet_ratio,max_bet FROM round ORDER BY id DESC LIMIT 1')
                                current_round = cursor.fetchone()
                                if current_round:
                                    round_value = current_round[0]
                                    sub_round = current_round[1]
                                    bet_ratio = current_round[2]
                                    max_bet = current_round[3]
                                    bet_setting = bet_ratio+'/'+str(max_bet)
                                else:
                                    reply_message = "ไม่พบข้อมูลในรอบนี้"
                                    send_reply(reply_token, reply_message)
                                    return '200'

                            # Retrieve all bets for the current round
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    SELECT user_profiles.id, user_profiles.display_name , play.user_play, play.amount_play,play.chicken
                                    FROM play
                                    JOIN user_profiles ON play.user_id = user_profiles.user_id
                                    WHERE play.round = ? AND play.sub_round = ?
                                ''', (round_value,sub_round))
                                bets = cursor.fetchall()

                            # Split bets into chunks of 20 for each bubble
                            grouped_bets = {}
                            for bet in bets:
                                user_id = bet[0]
                                display_name = bet[1]
                                user_play = bet[2]
                                amount_play = bet[3]
                                chicken = bet[4]
                                if user_id not in grouped_bets:
                                    grouped_bets[user_id] = {
                                        "id": user_id,
                                        "display_name": display_name,
                                        "user_play": [user_play],
                                        "amount_play": [amount_play],
                                        "chicken":chicken
                                    }
                                else:
                                    grouped_bets[user_id]["user_play"].append(user_play)
                                    grouped_bets[user_id]["amount_play"].append(amount_play)

                            # Convert grouped bets to a list of tuples
                            grouped_bets_list = [
                                (bet_data["id"], bet_data["display_name"], bet_data["user_play"], bet_data["amount_play"],bet_data["chicken"])
                                for bet_data in grouped_bets.values()
                            ]
                            if grouped_bets_list ==[]:
                                reply_message = 'ยังไม่มียอดแทง'
                                send_reply(reply_token,reply_message)
                                return '200'
                            # Split bets into chunks of 20 for each bubble
                            # reply_message,grouped_bets_list,bet_setting,round_value = get_current_sub_round_bet()

                            # if reply_message:
                            #     send_reply(reply_token,reply_message)
                            #     return '200'
                            
                            # print(grouped_bets_list)
                            chunk_size = 20
                            bet_chunks = [grouped_bets_list[i:i + chunk_size] for i in range(0, len(grouped_bets_list), chunk_size)]

                            bubbles = []
                            for chunk in bet_chunks:
                                bubbles.append(create_bet_bubble(chunk, round_value,bet_setting))

                            flex_message = {
                                "type": "carousel",
                                "contents": bubbles
                            }

                            send_flex_reply(reply_token, f"รอบที่ {round_value} ยอดแทง:", flex_message)

                        except Exception as e:
                            reply_message = f"ยังไม่พบข้อมูลผู้เล่น"
                            send_reply(reply_token,reply_message)
                            print(reply_message)
                            return '200'
                            
                    elif msg[0]=='ด' or msg[0]=='ง' or msg[0]=='ส':
                        try:
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT status,role,game_status FROM focus_group WHERE group_id = ?', (group_id,))
                                status = cursor.fetchone()
                                if status[2] == 'P':
                                    mess = msg
                                    data = mess.split('/')
                                    if len(data) ==4:
                                        try:
                                            with sqlite3.connect(db_name) as conn:
                                                cursor = conn.cursor()
                                                cursor.execute('SELECT status,game_status FROM focus_group WHERE group_id =?',(group_id,))
                                                status_group = cursor.fetchone()
                                                cursor.execute(
                                                    'UPDATE focus_group SET status = "closed", game_status = "X" WHERE group_id = ?',
                                                    (group_id,)
                                                )
                                                conn.commit()
                                            reply_message = "ปิดรอบ"
                                            #pic_close = f"{domain}/pictures/close.jpg"
                                            pic_close = f"{domain}/{close_pic}"
                                            with sqlite3.connect(db_name) as conn:
                                                cursor = conn.cursor()
                                                cursor.execute('SELECT round,sub_round,bet_ratio,max_bet FROM round ORDER BY id DESC LIMIT 1')
                                                current_round = cursor.fetchone()
                                                if current_round:
                                                    round_value = current_round[0]
                                                    sub_round = current_round[1]
                                                    bet_ratio = current_round[2]
                                                    max_bet = current_round[3]
                                                    bet_setting = bet_ratio+'/'+str(max_bet)
                                                else:
                                                    reply_message = "Error: No round information available."
                                                    send_reply(reply_token, reply_message)
                                                    return '200'

                                            # Retrieve all bets for the current round
                                            with sqlite3.connect(db_name) as conn:
                                                cursor = conn.cursor()
                                                cursor.execute('''
                                                    SELECT user_profiles.id, user_profiles.display_name , play.user_play, play.amount_play,play.chicken
                                                    FROM play
                                                    JOIN user_profiles ON play.user_id = user_profiles.user_id
                                                    WHERE play.round = ? AND play.sub_round = ?
                                                ''', (round_value,sub_round))
                                                bets = cursor.fetchall()
                                            
                                            if not bets:
                                                send_msg_pic(reply_token,'ปิดรอบไม่มียอดแทง',pic_close)
                                                return '200'
                                            # Split bets into chunks of 20 for each bubble
                                            grouped_bets = {}
                                            for bet in bets:
                                                user_id = bet[0]
                                                display_name = bet[1]
                                                user_play = bet[2]
                                                amount_play = bet[3]
                                                chicken = bet[4]
                                                if user_id not in grouped_bets:
                                                    grouped_bets[user_id] = {
                                                        "id": user_id,
                                                        "display_name": display_name,
                                                        "user_play": [user_play],
                                                        "amount_play": [amount_play],
                                                        "chicken":chicken
                                                    }
                                                else:
                                                    grouped_bets[user_id]["user_play"].append(user_play)
                                                    grouped_bets[user_id]["amount_play"].append(amount_play)

                                            # Convert grouped bets to a list of tuples
                                            grouped_bets_list = [
                                                (bet_data["id"], bet_data["display_name"], bet_data["user_play"], bet_data["amount_play"],bet_data["chicken"])
                                                for bet_data in grouped_bets.values()
                                            ]
                                            if grouped_bets_list ==[]:
                                                reply_message = 'ยังไม่มียอดแทง'
                                                send_reply(reply_token,reply_message)
                                                return '200'
                                            
                                            # Split bets into chunks of 20 for each bubble
                                            chunk_size = 20
                                            bet_chunks = [grouped_bets_list[i:i + chunk_size] for i in range(0, len(grouped_bets_list), chunk_size)]

                                            bubbles = []
                                            for chunk in bet_chunks:
                                                bubbles.append(create_bet_bubble(chunk, round_value,bet_setting,color='red'))
                                            round_value,sub_round = get_present_round(sub_round=1)
                                            with sqlite3.connect(db_name) as conn:
                                                cursor=conn.cursor()
                                                cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ? AND sub_round = ?', (round_value,sub_round))
                                                records = cursor.fetchall()
                                            if not records:
                                                reply_message= 'คุณยังไม่ได้แทงในรอบนี้'
                                                send_reply(reply_token,reply_message)
                                                return '200'

                                            user_totals = {'ด': 0, 'ง': 0}

                                            for record in records:

                                                user_id, chicken, bet_ratio, amount_play = record
                                                amount = float(amount_play)

                                                # Split and convert bet ratios
                                                # parts = bet_ratio.split('/')
                                                parts = bet_ratio.split('/')
                                                bet1= float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
                                                bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)

                                                main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
                                                if main_score == 'ส':
                                                    main_score=='ด'
                                                sp = 1.0
                                                sp2 = 1.0
                                                reward_main_score = bet2/bet1
                                                lose_main_score = 1
                                                reward_second_score = 1 
                                                lose_second_score = (bet1+0.2)/bet2
                                                if bet1 == 0.9 and bet2 == 0.9:
                                                    reward_main_score = 0.9
                                                    reward_second_score = 0.9
                                                    lose_second_score = 1
                                                elif bet1 ==1 and bet2 ==0.1:
                                                    lose_second_score = 0.1/(bet1-0.5)
                                                elif bet1 ==1 and bet2 == 0.9:
                                                    lose_second_score = 1
                                                elif bet1 ==1 and bet2 ==0.95:
                                                    lose_second_score= 1
                                                elif bet1 ==1 and bet2 ==0.85:
                                                    lose_second_score =1
                                                elif bet1 > 1 and bet2 ==0.1:
                                                    lose_second_score = 0.1/(bet1-0.5)

                                                # Predict for 'ด' and 'ง'
                                                for result_score in ['ด', 'ง']:
                                                    reward_or_penalty = 0
                                                    if chicken == main_score:
                                                        if result_score == chicken:
                                                            # Case 1: Reward when the bet matches the main score
                                                            reward_or_penalty = amount * reward_main_score
                                                        else:
                                                            # Case 1: Penalty when the bet loses with the main score
                                                            reward_or_penalty = -amount
                                                    else:
                                                        if result_score == chicken:
                                                            # Case 2: Reward when the result matches but not the main score
                                                            reward_or_penalty = amount * reward_second_score
                                                        else:
                                                            # Case 2: Penalty when neither the bet nor the result matches
                                                            reward_or_penalty = -amount * lose_second_score

                                                    # Accumulate the profit or loss for the result
                                                    user_totals[result_score] += reward_or_penalty

                                            user_totals['ด'] = user_totals['ด']*(-1)
                                            user_totals['ง'] = user_totals['ง']*(-1)
                                            color_d = '#FF0000'
                                            color_b = '#FF0000'
                                            sp1 = ""
                                            sp2 =""
                                            if user_totals['ด']<0:
                                                sp1 = "## "
                                            if user_totals['ง']<0:
                                                sp2 = "## "

                                            current_utc_time = datetime.utcnow()
                                            thailand_time = current_utc_time + timedelta(hours=7)
                                            thailand_time_str = thailand_time.strftime('%H:%M:%S')
                                            send_line_notify(f"\nคำนวณได้เสีย\nรอบที่ {round_value}\nฝั่งแดง #{sp1}{user_totals['ด']}\nฝั่งน้ำเงิน #{sp2}{user_totals['ง']}\nTime:{thailand_time_str}")
                                        except Exception as e:
                                            reply_message = f"Error closing round: {str(e)}"
                                            print(reply_message)
                                        send_close_msg_pic(reply_token, reply_message,pic_close,bubbles)
                                        socketio.emit('status',{'status':'close'})
                                        return '200'
                                    pass
                                elif status[2] =='O':
                                    pass
                                elif status[2]=='Y':
                                    reply_message = 'เพิ่งทำการคิดเงินไปกรุณา กด O เพื่อเริ่มรอบใหม่'
                                    send_reply(reply_token,reply_message)
                                    return '200'
                                elif status[0] != 'closed':
                                    reply_message ='ยังไม่ได้ปิดรอบ ปิดรอบก่อนนะ'
                                    send_reply(reply_token,reply_message)
                                    return '200'
                                elif status[2]=='X':
                                    pass
                                elif status[2] != 'O':
                                    reply_message = 'ลำดับการทำงานไม่ถูกต้อง'
                                    send_reply(reply_token,reply_message)
                                    return '200'
                            if msg[0]=='ด':
                                chicken='red'
                                color = '#ff0000'
                                color1 = '#0000ff'
                            elif msg[0]=='ง':
                                chicken='blue'
                                color = '#0000ff'
                                color1 = '#ff0000'
                            elif msg[0]=='ส':
                                chicken='blue'
                                color = '#1DB446'
                                color1 = '#1DB446'
                            mess = msg
                            data = mess.split('/')
                            round = get_present_round()
                            if len(data) ==4:
                                with sqlite3.connect(db_name) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('UPDATE focus_group SET status = ? WHERE group_id = ?', ('play', group_id))
                                    cursor.execute('UPDATE focus_group SET game_status = ? WHERE group_id = ?', ('P', group_id))
                                    cursor.execute('SELECT sub_round FROM round WHERE round = ? ',(round,))
                                    sub_round =cursor.fetchone()[0]
                        
                                    new_sub_round = sub_round+1
                    
                                    cursor.execute('UPDATE round SET sub_round = ? WHERE round = ?', (new_sub_round, round))
                                    conn.commit()
                                store_ratio(msg,round)
                                bet_ratio1 = float(data[1])
                                bet_ratio2 = float(data[2])
                                fix1 = '10'
                                fix2 = '10'
                                sp = 'รอง'
                                sp1 = 0
                                sp2 = 0
                                sp3 = 0
                                if bet_ratio1 == 9 and bet_ratio2 ==9:
                                    sp='ต่อ'
                                    fix2 = '9'
                                    bet_ratio2 = 8
                                    bet_ratio1 = 10
                                    sp2 =1
                                elif bet_ratio1 ==10 and bet_ratio2==1:
                                    bet_ratio2 = 0
                                    sp2 = 10
                                elif bet_ratio1 ==10 and bet_ratio2 ==9:
                                    sp3 =-1
                                elif bet_ratio1 == 10 and bet_ratio2 == 9.5:
                                    sp3 = -1.5
                                elif bet_ratio1 ==10 and bet_ratio2 ==8.5:
                                    sp3 = -0.5
                                elif bet_ratio1 >10 and bet_ratio2 ==1:
                                    fix2 =bet_ratio1-5
                                    sp3 = -bet_ratio2-1

                                display_1 = bet_ratio2+sp2
                                display_4 = bet_ratio2+2+sp3

                                bubble = {
                                    "type": "bubble",
                                    "body": {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                        {
                                            "type": "box",
                                            "layout": "vertical",
                                            "contents": [
                                            {
                                                "type": "text",
                                                "text": msg,
                                                "weight": "bold",
                                                "size": "xl",
                                                "color": "#FFFFFF",
                                                "align": "center"
                                            }
                                            ],
                                            "backgroundColor": color,
                                            "cornerRadius": "md",
                                            "paddingAll": "10px",
                                            "margin": "md"
                                        },
                                        {
                                            "type": "text",
                                            "text": f"ต่อได้ {str(display_1)}  เสีย {str(bet_ratio1)}",
                                            "weight": "bold",
                                            "size": "xl",
                                            "color": color,
                                            "align": "center",
                                            "margin": "lg"
                                        },
                                        {
                                            "type": "text",
                                        "text": f"{sp}ได้ {str(fix2)} เสีย {str(display_4)}",
                                            "weight": "bold",
                                            "size": "xl",
                                            "color": color1,
                                            "align": "center",
                                            "margin": "md"
                                        },
                                        {
                                            "type": "text",
                                            "text": f'จำกัดต่อไม้ไม่เกิน {data[3]} บ.',
                                            "color": color,
                                            "weight": "bold",
                                            "size": "md",
                                            "align": "center",
                                            "margin": "md"
                                        },
                                        {
                                            "type": "text",
                                            "text": f'จำกัดไม่เกิน2ไม้!',
                                            "color": color,
                                            "weight": "bold",
                                            "size": "md",
                                            "align": "center",
                                            "margin": "md"
                                        }
                                        ]
                                    }
                                    }
                                flex_message = {
                                "type": "carousel",
                                "contents": [bubble]
                            }

                                send_flex_reply(reply_token, f"รอบที่ {round} ยอดแทง:", flex_message)
                                
                                # reply_message = 'บันทึกราคาเรียบร้อย เริ่มแทงได้'
                                # send_reply(reply_token,reply_message)
                            else:
                                reply_message = 'ไม่สามารถบันทึกราคาได้ ลองส่งราคามาใหม่'
                                send_reply(reply_token,reply_message)
                            return '200'
                        except Exception as e:
                            print(e)
                            reply_message = f'Error:{e}'
                            return '200'

                    elif msg == 'O':
                        try:
                            # Fetch the current round from the database and increment it by 1
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT game_status FROM focus_group WHERE group_id=?', (group_id,))
                                stat = cursor.fetchone()
                                status = stat[0] if stat else None
                                print(f'this is status: {status}')
                                if status != 'Y':
                                    if status == 'O':
                                        reply_message = 'เปิดรอบไปแล้ว กรุณาส่งราคา'
                                    else:
                                        reply_message = 'ยังไม่ได้กดสรุปยอด Y กรุณาสรุปยอดก่อน'
                                    send_reply(reply_token, reply_message)
                                    return '200'

                                cursor.execute('SELECT round FROM round ORDER BY id DESC LIMIT 1')
                                current_round = cursor.fetchone()
                                # print(f'Current_round:{current_round}')
                                # if current_round:
                                #     cursor.execute('SELECT profit FROM result WHERE round=?',(current_round[0],))
                                #     check_profit  = cursor.fetchone()
                                #     print(f"doing check profit checkprofit = {check_profit}")
                                #     try:
                                #         print(f"doing check profit checkprofit = {check_profit}")
                                #         if check_profit == None:
                                #             reply_message = 'ยังไม่ได้กดสรุปยอด Y กรุณาสรุปยอดก่อน'
                                #             send_reply(reply_token,reply_message)
                                #             return '200'
                                #     except:
                                #         pass
                                #     if not check_profit[0]:
                                #         reply_message = 'ยังไม่ได้กดสรุปยอด Y กรุณาสรุปยอดก่อน'
                                #         send_reply(reply_token,reply_message)
                                #         return '200'
                                if current_round:
                                    new_round_value = current_round[0] + 1
                                else:
                                    new_round_value = 1  # Start from round 1 if no rounds exist
                                cursor.execute('INSERT INTO round (round,sub_round) VALUES (?,?)', (new_round_value,0))
                                cursor.execute('UPDATE focus_group SET game_status = "O" WHERE group_id = ?', (group_id,))
                                conn.commit()

                            socketio.emit('status', {'status': 'open'})
                            reply_message = f"เริ่มรอบใหม่ รอบที่ {new_round_value}"
                            #pic_open = f"{domain}/pictures/open.jpg"
                            pic_open = f"{domain}/{open_pic}"
                            # send_reply_with_picture(reply_token, reply_message, pic_open, "ประวัติ", flex_contents)
                            send_msg_pic(reply_token,reply_message,pic_open)
                            return '200'

                        except Exception as e:
                            reply_message = f"Error starting new round: {str(e)}"
                            send_reply(reply_token, reply_message)
                            return '200'

                    elif msg.lower() == 'ck':
                        with sqlite3.connect(db_name) as conn:
                            cursor = conn.cursor()
                            cursor.execute('SELECT game_status FROM focus_group WHERE group_id =?',(group_id,))
                            status_group = cursor.fetchone()
                            if status_group:
                                status = status_group[0]
                            if status == 'O':
                                reply_msg = 'ขณะนี้กำลังเปิดรอบ ให้ทำการออกราคาได้เลย'
                            elif status =='P':
                                reply_msg = 'ขณะนี้ออกราคาไปแล้ว กด ปด เพื่อปิดราคานี้' 
                            elif status =='X':
                                reply_msg ='ขณะนี้ปิดรอบไปแล้ว สามารถออกราคาใหม่ หรือสามารถออกผลได้เลย'
                            elif status == 'R':
                                reply_msg = 'ขณะนี้ได้ทำการออกผลแล้ว หากต้องการยืนยันผลสามารกด Y ได้เลย'
                            elif status == 'Y':
                                reply_msg = 'ขณะนี้ได้ทำการคิดเงินแล้ว สามารถกด O เพื่อเปิดรอบใหม่ได้เลย'
                            else:
                                reply_msg = 'ไม่พบข้อมูล'
                            send_reply(reply_token,reply_msg)
                            return '200'
                    
                    elif 'c' == msg.lower()[0]:
                        try:
                            game_id = int(msg.lower().replace('c',''))
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT user_id FROM user_profiles WHERE id =?',(game_id,))
                                u_id = cursor.fetchone()
                                cursor.execute('SELECT game_status FROM focus_group WHERE group_id = ?',(group_id,))
                                game_status = cursor.fetchone()[0]
                                if u_id:
                                    u_id = u_id[0]
                        
                            bets = get_bets_user(u_id)
                            if bets and game_status != 'Y':
                                flex_data = create_bet_bubble1(bets,u_id)
                                send_flex_reply(reply_token,'ยอดเล่น',flex_data)
                                return '200'
                            else:
                                data = get_balance(u_id,pic=1)
                                bubble = create_user_balance_bubble(data[0],data[1],data[2],data[3])
                                flex_contents = {
                            "type": "carousel",
                            "contents": [bubble]
                        } 
                                send_flex_reply(reply_token,'balance',flex_contents)
                                return '200'
                  
                                
                        except Exception as e:
                            print(f'Error in MENU C : {e}')
                            return '200'

                    elif msg=='ปด':    
                        try:
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT status,game_status FROM focus_group WHERE group_id =?',(group_id,))
                                status_group = cursor.fetchone()
                                if status_group:
                                    if status_group[0]!='play':
                                        reply_message = 'ยังไม่ได้ออกราคา กรุณาออกราคาก่อน '
                                        send_reply(reply_token,reply_message)
                                        return '200'
                                    if status_group[1]!= 'P':
                                        reply_message = 'ยังไม่ได้ออกราคา กรุณาออกราคาก่อน '
                                        send_reply(reply_token,reply_message)
                                        return '200'
                                cursor.execute(
                                    'UPDATE focus_group SET status = "closed", game_status = "X" WHERE group_id = ?',
                                    (group_id,)
                                )
                                conn.commit()
                            reply_message = "ปิดรอบ"
                            #pic_close = f"{domain}/pictures/close.jpg"
                            pic_close = f"{domain}/{close_pic}"
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT round,sub_round,bet_ratio,max_bet FROM round ORDER BY id DESC LIMIT 1')
                                current_round = cursor.fetchone()
                                if current_round:
                                    round_value = current_round[0]
                                    sub_round = current_round[1]
                                    bet_ratio = current_round[2]
                                    max_bet = current_round[3]
                                    bet_setting = bet_ratio+'/'+str(max_bet)
                                else:
                                    reply_message = "Error: No round information available."
                                    send_reply(reply_token, reply_message)
                                    return '200'

                            # Retrieve all bets for the current round
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    SELECT user_profiles.id, user_profiles.display_name , play.user_play, play.amount_play,play.chicken
                                    FROM play
                                    JOIN user_profiles ON play.user_id = user_profiles.user_id
                                    WHERE play.round = ? AND play.sub_round = ?
                                ''', (round_value,sub_round))
                                bets = cursor.fetchall()
                            
                            if not bets:
                                send_msg_pic(reply_token,'ปิดรอบไม่มียอดแทง',pic_close)
                                bubbles = ''
                                pass
                            else:
                                grouped_bets = {}
                                for bet in bets:
                                    user_id = bet[0]
                                    display_name = bet[1]
                                    user_play = bet[2]
                                    amount_play = bet[3]
                                    chicken = bet[4]
                                    if user_id not in grouped_bets:
                                        grouped_bets[user_id] = {
                                            "id": user_id,
                                            "display_name": display_name,
                                            "user_play": [user_play],
                                            "amount_play": [amount_play],
                                            "chicken":chicken
                                        }
                                    else:
                                        grouped_bets[user_id]["user_play"].append(user_play)
                                        grouped_bets[user_id]["amount_play"].append(amount_play)

                                # Convert grouped bets to a list of tuples
                                grouped_bets_list = [
                                    (bet_data["id"], bet_data["display_name"], bet_data["user_play"], bet_data["amount_play"],bet_data["chicken"])
                                    for bet_data in grouped_bets.values()
                                ]
                                if grouped_bets_list ==[]:
                                    reply_message = 'ยังไม่มียอดแทง'
                                    send_reply(reply_token,reply_message)
                                    return '200'
                            
                            # Split bets into chunks of 20 for each bubble
                                chunk_size = 20
                                bet_chunks = [grouped_bets_list[i:i + chunk_size] for i in range(0, len(grouped_bets_list), chunk_size)]

                                bubbles = []
                                for chunk in bet_chunks:
                                    bubbles.append(create_bet_bubble(chunk, round_value,bet_setting,color='red'))
                            
                            ########################################################
                            round_value,sub_round = get_present_round(sub_round=1)
                            with sqlite3.connect(db_name) as conn:
                                cursor=conn.cursor()
                                cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ? ', (round_value,))
                                records = cursor.fetchall()
                            if not records:
                                reply_message= 'คุณยังไม่ได้แทงในรอบนี้'
                                send_reply(reply_token,reply_message)
                                return '200'

                            user_totals = {'ด': 0, 'ง': 0}

                            for record in records:

                                user_id, chicken, bet_ratio, amount_play = record
                                amount = float(amount_play)

                                # Split and convert bet ratios
                                parts = bet_ratio.split('/')
                                bet1= float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
                                bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)

                                main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
                                if main_score =='ส':
                                    main_score =='ด'
                                sp = 1.0
                                sp2 = 1.0
                                reward_main_score = bet2/bet1
                                lose_main_score = 1
                                reward_second_score = 1 
                                lose_second_score = (bet2+0.2)/bet1
                                if bet1 == 0.9 and bet2 == 0.9:
                                    reward_main_score = 0.9
                                    reward_second_score = 0.9
                                    lose_second_score = 1
                                elif bet1 ==1 and bet2 ==0.1:
                                    lose_second_score = 0.1/(bet1-0.5)
                                elif bet1 ==1 and bet2 == 0.9:
                                    lose_second_score = 1
                                elif bet1 ==1 and bet2 ==0.95:
                                    lose_second_score= 1
                                elif bet1 ==1 and bet2 ==0.85:
                                    lose_second_score =1
                                elif bet1 > 1 and bet2 ==0.1:
                                    lose_second_score = 0.1/(bet1-0.5)

                                # Predict for 'ด' and 'ง'
                                for result_score in ['ด', 'ง']:
                                    reward_or_penalty = 0
                                    if chicken == main_score:
                                        if result_score == chicken:
                                            # Case 1: Reward when the bet matches the main score
                                            reward_or_penalty = amount * reward_main_score
                                        else:
                                            # Case 1: Penalty when the bet loses with the main score
                                            reward_or_penalty = -amount
                                    else:
                                        if result_score == chicken:
                                            # Case 2: Reward when the result matches but not the main score
                                            reward_or_penalty = amount * reward_second_score
                                        else:
                                            # Case 2: Penalty when neither the bet nor the result matches
                                            reward_or_penalty = -amount * lose_second_score

                                    # Accumulate the profit or loss for the result
                                    user_totals[result_score] += reward_or_penalty

                            user_totals['ด'] = user_totals['ด']*(-1)
                            user_totals['ง'] = user_totals['ง']*(-1)
                            color_d = '#FF0000'
                            color_b = '#FF0000'
                            sp1 = ""
                            sp2 =""
                            if user_totals['ด']<0:
                                sp1 = "## "
                            if user_totals['ง']<0:
                                sp2 = "## "
                            current_utc_time = datetime.utcnow()
                            thailand_time = current_utc_time + timedelta(hours=7)
                            thailand_time_str = thailand_time.strftime('%H:%M:%S')
                            send_line_notify(f"\nคำนวณได้เสีย\nรอบที่ {round_value}\nฝั่งแดง #{sp1}{user_totals['ด']}\nฝั่งน้ำเงิน #{sp2}{user_totals['ง']}\nTime:{thailand_time_str}")
                            print('LINE NOTIFY SEND')
                        except Exception as e:
                            reply_message = f"Error closing round: {str(e)}"
                            print(reply_message)
                        if bubbles:    
                            send_close_msg_pic(reply_token, reply_message,pic_close,bubbles)
                        socketio.emit('status',{'status':'close'})
                        return '200'
                    
                    elif msg=='X':
                        try:
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT status,game_status FROM focus_group WHERE group_id =?',(group_id,))
                                status_group = cursor.fetchone()
                                if status_group:
                                    
                                    if status_group[1]!= 'X':
                                        reply_message = 'ยังไม่ได้ออกราคา กรุณาออกราคาก่อน '
                                        send_reply(reply_token,reply_message)
                                        return '200'
                                cursor.execute(
                                    'UPDATE focus_group SET status = "closed", game_status = "XX" WHERE group_id = ?',
                                    (group_id,)
                                )
                                conn.commit()
                            round_value = get_present_round()
                            reply_message = f"ปิดรอบ ##{round_value}"
                            #pic_close = f"{domain}/pictures/close.jpg"
                            pic_close = f"{domain}/{close_pic}"
                            send_msg_pic(reply_token,reply_message,pic_close)
                        except Exception as e:
                            reply_message = f"Error closing round: {str(e)}"
                            print(reply_message)
                        return '200'
                    
                    elif msg == 'FO':
                        try:
                            # Fetch the current round from the database and increment it by 1
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT game_status FROM focus_group WHERE group_id=?', (group_id,))
                                stat = cursor.fetchone()
                                status = stat[0] if stat else None
                                print(f'this is status: {status}')

                                cursor.execute('SELECT round FROM round ORDER BY id DESC LIMIT 1')
                                current_round = cursor.fetchone()
                                if current_round:
                                    new_round_value = current_round[0] + 1
                                else:
                                    new_round_value = 1  # Start from round 1 if no rounds exist
                                cursor.execute('INSERT INTO round (round,sub_round) VALUES (?,?)', (new_round_value,0))
                                cursor.execute('UPDATE focus_group SET game_status = "O" WHERE group_id = ?', (group_id,))
                                conn.commit()
                            socketio.emit('status', {'status': 'open'})
                            reply_message = f"เริ่มรอบใหม่ รอบที่ {new_round_value}"
                            #pic_open = f"{domain}/pictures/open.jpg"
                            pic_open = f"{domain}/{open_pic}"
                            send_msg_pic(reply_token,reply_message,pic_open)
                            return '200'

                        except Exception as e:
                            reply_message = f"Error starting new round: {str(e)}"
                            send_reply(reply_token, reply_message)
                            return '200'
                    
                    elif msg.lower().startswith('s'):
                        try:
                            # Remove the 'r' prefix and strip any whitespace
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT game_status FROM focus_group WHERE group_id =?',(group_id,))
                                status_group = cursor.fetchone()
                                if status_group:
                                    if status_group[0] == 'R':
                                        pass
                                    elif status_group[0]!='XX':
                                        reply_message = 'ยังไม่ได้ปิดรอบ จะไม่สามารถออกผลได้'
                                        send_reply(reply_token,reply_message)
                                        return '200'
                            data = msg[1:].strip()
                            
                            if data =='ง':
                                chicken ='น้ำเงิน'
                               #pic_c_path = f'{domain}/pictures/blue.jpg'
                                pic_c_path = f'{domain}/{blue_win}'
                            elif data == 'ด':
                                chicken ='แดง'
                               # pic_c_path = f'{domain}/pictures/red.jpg'
                                pic_c_path = f'{domain}/{red_win}'
                            elif data =='ส':
                                chicken ='เสมอ'
                               # pic_c_path = f'{domain}/pictures/tie.jpg'
                                pic_c_path = f'{domain}/{tie}'
                            else:
                                reply_message = 'ออกผลผิดกรุณาออกผลใหม่'
                                send_reply(reply_token,reply_message)
                                return '200'
                            # Fetch the current round from the database
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT round FROM round ORDER BY id DESC LIMIT 1')
                                current_round = cursor.fetchone()
                                if current_round:
                                    round_value = current_round[0]
                                else:
                                    reply_message = "Error: No round information available."
                                    send_reply(reply_token, reply_message)
                                    return '200'

                                cursor.execute('SELECT * FROM result WHERE round = ?', (round_value,))
                                existing_row = cursor.fetchone()

                                if existing_row:
                                    # Update the existing row
                                    cursor.execute('''
                                        UPDATE result
                                        SET chicken= ?
                                        WHERE round = ?
                                    ''', (data, round_value))
                                else:
                                    # Insert a new row
                                    cursor.execute('''
                                        INSERT INTO result (round,chicken)
                                        VALUES (?, ?)
                                    ''', (round_value, data))
                                cursor.execute('UPDATE focus_group SET game_status = "R" WHERE group_id = ?', (group_id,))
                                conn.commit()
                                
                                reply_message = f'ไก่ที่ชนะคือ {chicken}\nยืนยันผลสรุปยอดกด Y'
                                #send_reply(reply_token,reply_message)
                                send_msg_pic(reply_token,reply_message,pic_c_path)
                                return '200'
                        except Exception as e:
                            print(e)
                            reply_message = f"Error processing results: {str(e)}"
                        send_reply(reply_token, reply_message)
                        return '200'
                    
                    elif 'Y' == msg:
                        # Calculate rewards and update balances
                        try:
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT round FROM round ORDER BY id DESC LIMIT 1')
                                current_round = cursor.fetchone()
                                cursor.execute('SELECT profit FROM result WHERE round =? ',(current_round[0],))
                                profit = cursor.fetchone()
                            if profit:
                                print('there is profit')
                                try:
                                    if profit[0]:
                                        reply_message = 'คิดเงินรอบนี้ไปเรียบร้อยแล้ว'
                                        send_reply(reply_token,reply_message)
                                        return '200'
                                except:
                                    pass
                            if current_round:
                                round_value = current_round[0]
                            # rewards_summarys =  calculate_and_update_rewards_hilo(round_value) 
                            print('check1')
                            rewards_summarys = calculate_and_update_rewards(round_value)
                            print(rewards_summarys)
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT game_status FROM focus_group WHERE group_id =?',(group_id,))
                                game_stat = cursor.fetchone()
                                if game_stat:
                                    game_status = game_stat[0]
                                    if game_status != 'R':
                                        reply_message = 'ยังไม่ได้ออกผล ไม่สามารถคิดเงินได้กรุณาออกผลก่อน'
                                        send_reply(reply_token,reply_message)
                                        return '200'
                                    else:
                                        cursor.execute('UPDATE focus_group SET game_status = "Y" WHERE group_id = ?',(group_id,))       
                                        conn.commit()
                            if rewards_summarys == "No result found":
                                reply_message = "ยังไม่ได้ออกผลว่าไก่ตัวไหนชนะ"
                                send_reply(reply_token,reply_message)
                                return '200'
                            if rewards_summarys == "No records found for this round.":
                                reply_message = "ยังไม่มีคนแทงตัวไหนเลย"
                                send_reply(reply_token,reply_message)
                                return '200'
                            
                            #rewards_summarys.split('\n')
                            bb_contents = []
                            for rewards in rewards_summarys.split('\n'):
                                name_id = rewards.split('|')[0]
                                prize = rewards.split('|')[1]
                                bb_content = {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": name_id},
                                    {"type": "text", "text": prize,"align": "end"},

                                    ]
                                    }
                                bb_contents.append(bb_content)
                            
                            bubble = {
                                "type": "bubble",
                                "size":"giga",
                                "hero": {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                        {"type": "text", "text": game_name, "align": "center", "size": "xxl", "color": "#FFFFFF", "weight": "bold"},
                                        {"type": "text", "text": f"สรุปยอดเงิน รอบ{current_round[0]}", "align": "center", "size": "xl", "color": "#FFFFFF", "weight": "bold"}
                                    ],
                                    "backgroundColor": "#0000FF"
                                },
                                "body": {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": bb_contents
                                }
                            }
                            flex_contents = {
                                "type": "carousel",
                                "contents": [bubble]
                            }
                            # with sqlite3.connect(db_name) as conn:
                            #     cursor = conn.cursor()
                            #     cursor.execute('SELECT profit FROM result WHERE round = ?',(round_value,))
                            #     profit = cursor.fetchone()
                            # if profit:
                            #     amount_profit = profit[0]

                            #     if int(amount_profit) > 0 :
                            #         msg = f"\nคู่ที่{round_value}\nกำไร : {amount_profit} บาท"
                            #     elif int(amount_profit)<0:
                            #         msg = f"\nคู่ที่{round_value}\nขาดทุน :{amount_profit} บาท"
                            #     else:
                            #         msg = f"\nคู่ที่{round_value} ผล: เสมอ"

                            # with sqlite3.connect(db_name) as conn:
                            #     cursor = conn.cursor()
                            #     cursor.execute('UPDATE focus_group SET game_status = "Y" WHERE group_id = ?',(group_id,))     
                            #     cursor.execute('SELECT profit FROM result')  
                            #     profits = cursor.fetchall()
                            #     conn.commit()
                            # data = ""
                            # for profit in profits:
                            #     if profit[0] > 0:
                            #         sp = 'กำไร'
                            #     elif profit[0] < 0:
                            #         sp = 'ขาดทุน'
                            #     else:
                            #         sp = ''
                            #     data += f"คู่ที่ {profit[1]} {sp} {profit[0]} บาท\n"
                            # send_line_notify(data)
                            send_flex_reply(reply_token,'สรุปรอบ',flex_contents)
                            
                            round_value =get_present_round()
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT profit FROM result WHERE round =?',(round_value,))
                                profit = cursor.fetchone()

                            notify_message = f"\nสรุปกำไร\nคู่ที่{round_value}:{profit[0]} บาท"
                            print(notify_message)
                            send_line_notify(notify_message)
                            return '200'
                        except Exception as e:
                            print(f'Error menu Y: {e}')
                            return '200'
                        
                    elif 'ห้องฝาก' == msg:
                        reply_message = link_acc_room
                        send_reply(reply_token,reply_message)
                        return '200'
                    
                    elif '!return' == msg:
                        with sqlite3.connect(db_name) as conn:
                            cursor.execute('SELECT game_status FROM focus_group WHERE group_id =?',(group_id,))
                            g_status = cursor.fetchone()
                            if g_status:
                                game_status = g_status[0]
                                if game_status == 'Y':
                                    reply_message = 'มีคำสั่งคิดเงินผิด โปรดเปิดรอบใหม่ก่อนแล้วพิมพ์ว่า !return'
                                    send_reply(reply_token,reply_message)
                                    return '200'
                        PWD_return = generate_order_id(k=4)
                        reply_message = f'ถ้าต้องการยืนยัน ย้อนผลให้พิมพ์ว่า !{PWD_return} \n หมายเหตุ โปรดใช้ในกรณีที่ออกผลผิดเท่านั้น'
                        reply_message2 = f"!{PWD_return}"
                        send_reply2(reply_token,reply_message,reply_message2)
                        return '200'
                    
                    elif f'!{PWD_return}'== msg:
                        with sqlite3.connect(db_name) as conn:
                            cursor = conn.cursor()
                            
                            cursor.execute('DELETE FROM round WHERE id = (SELECT MAX(id) FROM round)')
                            cursor.execute('UPDATE focus_group SET status = "closed", game_status = "XX" WHERE group_id = ?',(group_id,))
                            conn.commit()
                        current_round = get_present_round()
                        x= recalculate_and_update_rewards(current_round)
                        print(x)
                        with sqlite3.connect(db_name) as conn:
                            cursor = conn.cursor()
                            cursor.execute('UPDATE focus_group SET status = "closed", game_status = "XX" WHERE group_id = ?',(group_id,))
                            cursor.execute('UPDATE result SET profit = ? WHERE round = ?',(None,current_round))
                            conn.commit()
                        reply_message = 'ย้อนผลเรียบร้อยกรุณาออกผล และ คิดเงินใหม่อีกครั้ง'
                        send_reply(reply_token,reply_message)
                        return '200'

                elif status and role[0]== 'user':
                    with sqlite3.connect(db_name) as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT id,display_name FROM user_profiles WHERE user_id = ?', (user_id,))
                        data = cursor.fetchone()
                        game_id = data[0]
                        u_name = data[1]

                    message = event['message']['text']
                    # if 'C' == message or 'c'==message:
                    #     data = get_balance(user_id)
                    #     reply_message = f'ID:{data[0]} {data[1]}\nยอดเงินคงเหลือ {data[2]}$'
                    #     send_reply(reply_token, reply_message)
                    #     return '200'
                    if 'ห้องฝาก' == message:
                        reply_message = """ห้องฝาก-ถอน\nhttps://line.me/R/ti/g/1maFZhj2pv\n👈จิ้มเลย ลิ้งเข้าห้องฝาก"""
                        reply_message = link_acc_room
                        send_reply(reply_token,reply_message)
                        return '200'
                    
                    elif 'บช' == message or 'บช.' == message or 'บัญชี'== message or 'ฝาก' in message:
                        message = acc_number
                        #msg1 = acc_number
                        #pic_path = f"{domain}/pictures/ac5.jpg"
                        msg1 = acc_number
                        pic_path = f"{domain}/{acc_pic}"
                        msg2 = ac_msg
                        # pic_path1 = f"{domain}/pictures/ac1.jpg"
                        print(msg1)
                        print(pic_path)
                        print(msg2)
                        send_msg_pic_msg1(reply_token,msg1,pic_path,msg2)
                        return '200'
                    
                    elif 'ว' ==message:
                        #reply_message = 'แสดงวิธีการแทง'
                        #send_reply(reply_token,reply_message)
                        text = msg_how_to_play
                        pic = f"{domain}/{how_to_play_pic}"
                        print(pic)
                        print('########################')
                        send_msg_pic(reply_token,text,pic)
                    
                    if status[0] == 'play':
                        # msg_id = event['message']['id']
                        # timestamp = event['timestamp']

                        if '=' in message  or '-' in message or '.' in message or ':' in message or '_'in message or '/' in message or message[0]=='ด' or message[0]=='ง':
                            #socketio.emit('incoming_data',{'incoming_data':'data'})
                            messages = message.split('\n')
                            messages = [item for item in messages if item.strip()]
                            for message in messages:
                                if message =='' or message ==' ':
                                    continue
                                notwork=0
                                try:
                                    # Fetch the current round from the database
                                    with sqlite3.connect(db_name) as conn:
                                        cursor = conn.cursor()
                                        cursor.execute('SELECT round FROM round ORDER BY id DESC LIMIT 1')
                                        current_round = cursor.fetchone()
                                        if current_round:
                                            round_value = current_round[0]
                                        else:
                                            reply_message = "Error: No round information available."
                                            print(reply_message)
                                            #send_reply(reply_token, reply_message)
                                            return '200'
                                    
                                    bet_info = analysis_type_bet(message)
                                    if not bet_info:
                                        reply_message =f'{game_id}) {u_name}\nวิธีการแทงไม่ถูกต้องลองแทงมาใหม่น้า'
                                        continue
                                    
                                    amount = bet_info['amount']
                                    normalized_items = []
                                    normalized_items1 = []
                                    notwork = 0
                                    if notwork != 1: 
                                        with sqlite3.connect(db_name) as conn:
                                            cursor = conn.cursor()
                                            cursor.execute('SELECT backup_amount , amount FROM user_profiles WHERE user_id = ?', (user_id,))
                                            user_balance = cursor.fetchone()
                                            user_amount = user_balance[1]
                                            if user_balance:
                                                user_balance = float(user_balance[1]) ##################
                                            else:
                                                reply_message = "Error: User not found."
                                                continue
                                            cursor.execute('SELECT max_bet,sub_round,bet_ratio FROM round WHERE round = ?',(round_value,))
                                            data= cursor.fetchone()
                                            maximum_amount = data[0]
                                            sub_round = data[1]
                                            bet_ratio =data[2]
##########################################################################################################################################################################################
                                        

                                        round_value = get_present_round()

                                        with sqlite3.connect(db_name) as conn:
                                            cursor=conn.cursor()
                                            cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ? AND user_id = ?', (round_value,user_id))
                                            records = cursor.fetchall()    
                                        user_totals = {'ด': 0, 'ง': 0}
                                        new_record =[(user_id,bet_info['chicken'],bet_ratio,bet_info['amount'])]
                                        records += new_record
                    
                                        for record in records:
                                            user_id, chicken, bet_ratio, amount_play = record
                                            amount = float(amount_play)
                                            # Split and convert bet ratios
                                            parts = bet_ratio.split('/')
                                            bet1 = float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
                                            bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)
                                            main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
                                            if main_score =='ส':
                                                main_score =='ด'
                                            sp = 1.0
                                            sp2 = 1.0
                                            reward_main_score = bet2/bet1
                                            lose_main_score = 1
                                            reward_second_score = 1 
                                            lose_second_score = (bet2+0.2)/bet1
                                            if bet1 == 0.9 and bet2 == 0.9:
                                                reward_main_score = 0.9
                                                reward_second_score = 0.9
                                                lose_second_score = 1
                                            elif bet1 ==1 and bet2 ==0.1:
                                                lose_second_score = 0.1/(bet1-0.5)
                                            elif bet1 ==1 and bet2 == 0.9:
                                                lose_second_score = 1
                                            elif bet1 ==1 and bet2 ==0.95:
                                                lose_second_score= 1
                                            elif bet1 ==1 and bet2 ==0.85:
                                                lose_second_score =1
                                            elif bet1 > 1 and bet2 ==0.1:
                                                lose_second_score = 0.1/(bet1-0.5)

                                            # Predict for 'ด' and 'ง'
                                            for result_score in ['ด', 'ง']:
                                                reward_or_penalty = 0
                                                if chicken == main_score:
                                                    if result_score == chicken:
                                                        # Case 1: Reward when the bet matches the main score
                                                        reward_or_penalty = amount * reward_main_score
                                                    else:
                                                        # Case 1: Penalty when the bet loses with the main score
                                                        reward_or_penalty = -amount
                                                else:
                                                    if result_score == chicken:
                                                        # Case 2: Reward when the result matches but not the main score
                                                        reward_or_penalty = amount * reward_second_score
                                                    else:
                                                        # Case 2: Penalty when neither the bet nor the result matches
                                                        reward_or_penalty = -amount * lose_second_score

                                                # Accumulate the profit or loss for the result
                                                user_totals[result_score] += reward_or_penalty    
                                        
                                        if user_totals['ด'] > user_totals['ง']:
                                            max_minus = user_totals['ง']
                                        else:
                                            max_minus = user_totals['ด']
                                        ## #####################################################################################################################################################    
                                        if amount>int(maximum_amount):
                                            amount = int(maximum_amount)
                                            bet_info['amount']= amount
                                            # reply_message = f"รอบนี้เปิดให้แทงได้ไม่เกิน {maximum_amount}บาท"
                                            # send_reply(reply_token,reply_message)

                                            # return'200'
                                        if abs(max_minus)> user_balance:
                                            if user_totals['ด']<0  or user_totals['ง'] <0:
                                                reply_message = f"{game_id}:{u_name} \nยอดเงินไม่พอจ่าย ฿."
                                                #reply_message = f"{game_id}:{u_name} \nยอดเงินไม่พอจ่าย คุณสามารถแทงได้สูงสุด {user_balance:.2f} ฿."
                                                send_reply(reply_token,reply_message)
                                                return '200'
                                        if user_balance <=0 :
                                            reply_message = f"{game_id}:{u_name} \n ยอดเงินไม่พอที่จะจ่ายกรุณาเติมเงินก่อน"
                                            send_reply(reply_token,reply_message)
                                            return'200'
                                        else:
                                            corrected_user_play = f"{bet_info['chicken']}={bet_info['amount']}"
                                            previous_plays = []
                                            with sqlite3.connect(db_name) as conn:
                                                cursor = conn.cursor()
                                                cursor.execute('''
                                                    SELECT user_play, amount_play
                                                    FROM play 
                                                    WHERE user_id = ? AND round = ? AND sub_round =?
                                                ''', (user_id, round_value,sub_round))
                                                previous_plays = cursor.fetchall()
                                            current_ratio = get_current_bet_ratio(round_value)
                                            with sqlite3.connect(db_name) as conn:
                                                cursor = conn.cursor()
                                                cursor.execute('''
                                                    SELECT COUNT(*)
                                                    FROM play
                                                    WHERE user_id = ? AND round = ? AND sub_round = ?
                                                ''', (user_id, round_value, sub_round))

                                                # Fetch the count result
                                                count_result = cursor.fetchone()[0]
                                                if count_result >=2:
                                                    reply_message = 'สามารถแทงได้ไม่เกิน2ครั้ง/1 รอบ'
                                                    send_reply(reply_token,reply_message)
                                                    return '200'
                                            store_play(user_id, round_value, corrected_user_play, bet_info,current_ratio,sub_round ,amount)
                                            
                                            new_balance = user_balance - amount
                                            with sqlite3.connect(db_name) as conn:
                                                cursor = conn.cursor()
                                                cursor.execute('UPDATE user_profiles SET backup_amount = ? WHERE user_id = ?', (new_balance, user_id))
                                                conn.commit()
                                            
                                            # Format the bet items for display
                                            bet_items_display = corrected_user_play

                                            # Format the previous plays for display
                                            previous_plays_display = ''
                                            for play in previous_plays:
                                                previous_plays_display = previous_plays_display+str(play[0])+'\n'

                                            if previous_plays_display:
                                                previous_plays_display += ''

                                            #reply_message = f"{game_id}){u_name} แทง ✅:{bet_ratio}/{maximum_amount}\n{previous_plays_display}{bet_items_display} \n💰{user_amount}"
                                            reply_message = f"{game_id}){u_name}\n{previous_plays_display}{bet_items_display} ติด ✅ \nคงเหลือ{user_amount}💰"
                                except Exception as e:
                                    print(e)
                                    reply_message = f"{game_id}:{u_name} \n ลองแทงมาใหม่นะ: {str(e)}"
                            send_reply(reply_token, reply_message)
                            return '200'
                        
                        elif 'dl' == message.lower():
                            try:
                                # Fetch the current round from the database
                                
                                current_round,sub_round = get_present_round(sub_round=1)
                                if current_round:
                                    round_value = current_round
                                else:
                                    reply_message = "Error: No round information available."
                                    send_reply(reply_token, reply_message)
                                    return '200'

                                # Fetch the user's last bet in the current round
                                with sqlite3.connect(db_name) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('''
                                        SELECT id, amount_play, round, bet_ratio
                                        FROM play
                                        WHERE user_id = ? AND round = ? AND sub_round =?
                                        ORDER BY id DESC LIMIT 1
                                    ''', (user_id, round_value,sub_round))
                                    last_bet = cursor.fetchone()
                                print('test1')
                                present_ratio = get_current_bet_ratio(round_value)
                                print('test2')
                                if last_bet:
                                    bet_id, bet_amount, bet_round,bet_ratio = last_bet[0],last_bet[1],last_bet[2],last_bet[3]
                                    # print(present_ratio)

                                    # print('###########')

                                    # print(bet_ratio)
                                    if present_ratio == bet_ratio:
                                        with sqlite3.connect(db_name) as conn:
                                            cursor = conn.cursor()
                                            cursor.execute('DELETE FROM play WHERE id = ?', (bet_id,))
                                            conn.commit()
                                    #     bet_summary = {
                                    #             "round_value": bet_round,
                                                
                                    #             'data': {
                                    #                 "p1": last_bet[3],
                                    #                 "p2": last_bet[4],
                                    #                 "p3": last_bet[5],
                                    #                 "p4": last_bet[6],
                                    #                 'amount':bet_amount
                                    #             }
                                    #         }
                                    #     # socketio.emit('delete', bet_summary)
                                    #     print('*******************remove******************')
                                    #     print(bet_summary)
                                    # # Update the user's balance
                                        with sqlite3.connect(db_name) as conn:
                                            cursor = conn.cursor()
                                            cursor.execute('SELECT backup_amount, amount FROM user_profiles WHERE user_id = ?', (user_id,))
                                            user_balance = cursor.fetchone()
                                            user_amount = user_balance[1]
                                            if user_balance:
                                                user_balance = float(user_balance[0])
                                                new_balance = user_balance + float(bet_amount)
                                                cursor.execute('UPDATE user_profiles SET backup_amount = ? WHERE user_id = ?', (new_balance, user_id))
                                                conn.commit()
                                            # Format the reply message
                                            with sqlite3.connect(db_name) as conn:
                                                cursor = conn.cursor()
                                                cursor.execute('''
                                                    SELECT user_play, amount_play
                                                    FROM play 
                                                    WHERE user_id = ? AND round = ?
                                                ''', (user_id, round_value))
                                                previous_plays = cursor.fetchall()

                                            previous_plays_display = '\n'.join([f"{play[0].split('=')[0]} = {play[1]}" for play in previous_plays])
                                            bet_items_display = ' + '.join([f"{play[0].split('=')[0]}" for play in previous_plays])
                                            if not previous_plays_display:
                                                if not bet_items_display:
                                                    reply_message = f"{game_id}) {u_name} รอบที่ {bet_round}:\n{user_amount}฿"
                                            else:
                                                reply_message = f"{game_id}) {u_name} รอบที่ {bet_round}:\n{previous_plays_display}\n{user_amount} ฿"


                                    else:
                                        reply_message = 'ไม่สามารถยกเลิกได้เนื่องจากปิดรอบไปแล้ว'
                                else:
                                    reply_message = "Error: ไม่พบยอดให้ยกเลิก"

                            except Exception as e:
                                
                                reply_message = f"Error canceling the last bet: {str(e)}"
                                print(reply_message)
                                return '200'
                            send_reply(reply_token, reply_message)
                            return '200'

                        elif 'C' == message or 'c'==message:
                            try:
                                with sqlite3.connect(db_name) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('SELECT game_status FROM focus_group WHERE group_id = ?',(group_id,))
                                    gms = cursor.fetchone()
                                    if gms:
                                        game_status= gms[0]
                                bets = get_bets_user(user_id)
                                if bets and game_status != 'Y':
                                    flex_data = create_bet_bubble1(bets,user_id)
                                    send_flex_reply(reply_token,'ยอดเล่น',flex_data)
                                    return '200'
                                else:
                                    data = get_balance(user_id,pic=1)
                                    bubble = create_user_balance_bubble(data[0],data[1],data[2],data[3])
                                    flex_contents = {
                                "type": "carousel",
                                "contents": [bubble]
                            } 
                                    send_flex_reply(reply_token,'balance',flex_contents)
                                    return '200'
                            except Exception as e:
                                print(f'Error in MENU C : {e}')
                                return '200'
                        
                        elif message.lower() == 'cc':
                            round_value = get_present_round()
                            with sqlite3.connect(db_name) as conn:
                                cursor=conn.cursor()
                                cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ? AND user_id = ?', (round_value,user_id))
                                records = cursor.fetchall()
                                cursor.execute('SELECT id,display_name,picture_url FROM user_profiles WHERE user_id = ?',(user_id,))
                                profile = cursor.fetchone()
                            if not records:
                                reply_message= 'คุณยังไม่ได้แทงในรอบนี้'
                                send_reply(reply_token,reply_message)
                                return '200'
                            with sqlite3.connect(db_name) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('SELECT game_status FROM focus_group WHERE group_id = ?',(group_id,))
                                    gms = cursor.fetchone()
                                    if gms:
                                        game_status= gms[0]
                            if game_status == 'Y':
                                reply_message= 'คุณยังไม่ได้แทงในรอบนี้'
                                send_reply(reply_token,reply_message)
                                return '200'

                            user_totals = {'ด': 0, 'ง': 0}

                            for record in records:
    
                                user_id, chicken, bet_ratio, amount_play = record
                                amount = float(amount_play)

                                # Split and convert bet ratios
                                parts = bet_ratio.split('/')
                                bet1 = float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
                                bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)
                                main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
                                if main_score =='ส':
                                    main_score =='ด'
                                sp = 1.0
                                sp2 = 1.0
                                reward_main_score = bet2/bet1
                                lose_main_score = 1
                                reward_second_score = 1 
                                lose_second_score = (bet2+0.2)/bet1
                                if bet1 == 0.9 and bet2 == 0.9:
                                    reward_main_score = 0.9
                                    reward_second_score = 0.9
                                    lose_second_score = 1
                                elif bet1 ==1 and bet2 ==0.1:
                                    lose_second_score = 0.1/(bet1-0.5)
                                elif bet1 ==1 and bet2 == 0.9:
                                    lose_second_score = 1
                                elif bet1 ==1 and bet2 ==0.95:
                                    lose_second_score= 1
                                elif bet1 ==1 and bet2 ==0.85:
                                    lose_second_score =1
                                elif bet1 > 1 and bet2 ==0.1:
                                    lose_second_score = 0.1/(bet1-0.5)

                                # Predict for 'ด' and 'ง'
                                for result_score in ['ด', 'ง']:
                                    reward_or_penalty = 0
                                    if chicken == main_score:
                                        if result_score == chicken:
                                            # Case 1: Reward when the bet matches the main score
                                            reward_or_penalty = amount * reward_main_score
                                        else:
                                            # Case 1: Penalty when the bet loses with the main score
                                            reward_or_penalty = -amount
                                    else:
                                        if result_score == chicken:
                                            # Case 2: Reward when the result matches but not the main score
                                            reward_or_penalty = amount * reward_second_score
                                        else:
                                            # Case 2: Penalty when neither the bet nor the result matches
                                            reward_or_penalty = -amount * lose_second_score

                                    # Accumulate the profit or loss for the result
                                    user_totals[result_score] += reward_or_penalty
                                    # print(user_totals)
                                    # print("@@@@@@@@@@@@@@@@@@")
                                #print(user_totals)
                                color_d = '#FF0000'
                                color_b = '#FF0000'
                                if float(user_totals['ด']) >= 0:
                                    color_d = '#00FF00'
                                if float(user_totals['ง']) >= 0:
                                    color_b = '#00FF00'
                                bubble = {
                                "type": "bubble",
                                'size': 'hecto',
                                "header": {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                    {
                                        "type": "text",
                                        "text": f"คำนวณล่วงหน้า คู่ที่{round_value}",
                                        "weight": "bold",
                                        "size": "lg",
                                        "align": "center"
                                    }
                                    ]
                                },
                                "hero": {
                                    "type": "image",
                                    "url": profile[2],
                                    "size": "lg",
                                    "aspectRatio": "1:1",
                                    "aspectMode": "cover"
                                },
                                "body": {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                        {
                                            "type": "text",
                                            "text": "น้ำเงินชนะ",
                                            "color": "#0000FF",
                                            "weight": "bold",
                                            "size": "md",
                                            "align": "center"
                                        },
                                        {
                                            "type": "text",
                                            "text": str(user_totals['ง']),
                                            "color": color_b,
                                            "weight": "bold",
                                            "size": "lg",
                                            "align": "center"
                                        }
                                        ],
                                        "backgroundColor": "#E0F7FA",
                                        "cornerRadius": "10px",
                                        "borderWidth": "2px",
                                        "borderColor": "#0000FF",
                                        "margin": "sm",
                                        "paddingAll": "10px"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                        {
                                            "type": "text",
                                            "text": "แดงชนะ",
                                            "color": "#FF0000",
                                            "weight": "bold",
                                            "size": "md",
                                            "align": "center"
                                        },
                                        {
                                            "type": "text",
                                            "text": str(user_totals["ด"]),
                                            "color": color_d,
                                            "weight": "bold",
                                            "size": "lg",
                                            "align": "center"
                                        }
                                        ],
                                        "backgroundColor": "#FFEBEE",
                                        "cornerRadius": "10px",
                                        "borderWidth": "2px",
                                        "borderColor": "#FF0000",
                                        "margin": "sm",
                                        "paddingAll": "10px"
                                    }
                                    ],
                                    "spacing": "md",
                                    "justifyContent": "space-between"
                                }
                                }
                            flex_message = {
                            "type": "carousel",
                            "contents": [bubble]
                        }

                            send_flex_reply(reply_token, f"รอบที่ {round_value} ยอดแทง:", flex_message)
                            return '200'

                    elif status[0] =='closed':
                        if '=' in message:
                            reply_message =f"{game_id}:{u_name} ปิดรับการแทงแล้ว\n กรุณาแทงใหม่ในรอบหน้านะค่ะ"
                            send_reply(reply_token, reply_message)
                        elif '-' in message:
                            reply_message =f"{game_id}:{u_name} ปิดรับการแทงแล้ว\n กรุณาแทงใหม่ในรอบหน้านะค่ะ"
                            send_reply(reply_token, reply_message)
                        elif '.' in message:
                            reply_message =f"{game_id}:{u_name} ปิดรับการแทงแล้ว\n กรุณาแทงใหม่ในรอบหน้านะค่ะ"
                            send_reply(reply_token, reply_message)
                        elif ':' in message:
                            reply_message =f"{game_id}:{u_name} ปิดรับการแทงแล้ว\n กรุณาแทงใหม่ในรอบหน้านะค่ะ"
                            send_reply(reply_token, reply_message)
                        elif '_' in message:
                            reply_message =f"{game_id}:{u_name} ปิดรับการแทงแล้ว\n กรุณาแทงใหม่ในรอบหน้านะค่ะ"
                            send_reply(reply_token, reply_message)
                        elif '/' in message:
                            reply_message =f"{game_id}:{u_name} ปิดรับการแทงแล้ว\n กรุณาแทงใหม่ในรอบหน้านะค่ะ"
                            send_reply(reply_token, reply_message)
                        elif '+' in message:
                            reply_message =f"{game_id}:{u_name} ปิดรับการแทงแล้ว\n กรุณาแทงใหม่ในรอบหน้านะค่ะ"
                            send_reply(reply_token, reply_message)
                        elif ',' in message:   
                            reply_message =f"{game_id}:{u_name} ปิดรับการแทงแล้ว\n กรุณาแทงใหม่ในรอบหน้านะค่ะ"
                            send_reply(reply_token, reply_message) 
                            return '200'
                        elif 'X' in message:
                            reply_message = 'ไม่สามารถยกเลิกยอดได้เนื่องจากปิดรอบไปแล้ว'
                            send_reply(reply_token, reply_message) 
                            return '200'
                        elif 'C' == message or 'c'==message:
                            try:
                                with sqlite3.connect(db_name) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('SELECT game_status FROM focus_group WHERE group_id = ?',(group_id,))
                                    gms = cursor.fetchone()
                                    if gms:
                                        game_status= gms[0]
                                bets = get_bets_user(user_id)
                                if bets and game_status != 'Y':
                                    flex_data = create_bet_bubble1(bets,user_id)
                                    send_flex_reply(reply_token,'ยอดเล่น',flex_data)
                                    return '200'
                                else:
                                    data = get_balance(user_id,pic=1)
                                    bubble = create_user_balance_bubble(data[0],data[1],data[2],data[3])
                                    flex_contents = {
                                "type": "carousel",
                                "contents": [bubble]
                            } 
                                    send_flex_reply(reply_token,'balance',flex_contents)
                                    return '200'
                            except Exception as e:
                                print(f'Error in MENU C : {e}')
                                return '200'
                        elif message.lower() == 'cc':
                            round_value = get_present_round()
                            with sqlite3.connect(db_name) as conn:
                                cursor=conn.cursor()
                                cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ? AND user_id = ?', (round_value,user_id))
                                records = cursor.fetchall()
                                cursor.execute('SELECT id,display_name,picture_url FROM user_profiles WHERE user_id = ?',(user_id,))
                                profile = cursor.fetchone()
                            if not records:
                                reply_message= 'คุณยังไม่ได้แทงในรอบนี้'
                                send_reply(reply_token,reply_message)
                                return '200'
                            with sqlite3.connect(db_name) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('SELECT game_status FROM focus_group WHERE group_id = ?',(group_id,))
                                    gms = cursor.fetchone()
                                    if gms:
                                        game_status= gms[0]
                            if game_status == 'Y':
                                reply_message= 'คุณยังไม่ได้แทงในรอบนี้'
                                send_reply(reply_token,reply_message)
                                return '200'

                            user_totals = {'ด': 0, 'ง': 0}

                            for record in records:
                                user_id, chicken, bet_ratio, amount_play = record
                                amount = float(amount_play)
                                # Split and convert bet ratios
                                parts = bet_ratio.split('/')
                                bet1= float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
                                bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)

                                main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
                                if main_score =='ส':
                                    main_score =='ด'
                                sp = 1.0
                                sp2 = 1.0
                                reward_main_score = bet2/bet1
                                lose_main_score = 1
                                reward_second_score = 1 
                                lose_second_score = (bet2+0.2)/bet1
                                if bet1 == 0.9 and bet2 == 0.9:
                                    reward_main_score = 0.9
                                    reward_second_score = 0.9
                                    lose_second_score = 1
                                elif bet1 ==1 and bet2 ==0.1:
                                    lose_second_score = 0.1/(bet1-0.5)
                                elif bet1 ==1 and bet2 == 0.9:
                                    lose_second_score = 1
                                elif bet1 ==1 and bet2 ==0.95:
                                    lose_second_score= 1
                                elif bet1 ==1 and bet2 ==0.85:
                                    lose_second_score =1
                                elif bet1 > 1 and bet2 ==0.1:
                                    lose_second_score = 0.1/(bet1-0.5)

                                # Predict for 'ด' and 'ง'
                                for result_score in ['ด', 'ง']:
                                    reward_or_penalty = 0
                                    if chicken == main_score:
                                        if result_score == chicken:
                                            # Case 1: Reward when the bet matches the main score
                                            reward_or_penalty = amount * reward_main_score
                                        else:
                                            # Case 1: Penalty when the bet loses with the main score
                                            reward_or_penalty = -amount
                                    else:
                                        if result_score == chicken:
                                            # Case 2: Reward when the result matches but not the main score
                                            reward_or_penalty = amount * reward_second_score
                                        else:
                                            # Case 2: Penalty when neither the bet nor the result matches
                                            reward_or_penalty = -amount * lose_second_score

                                    # Accumulate the profit or loss for the result
                                    user_totals[result_score] += reward_or_penalty
                                    print(user_totals)
                                    print("@@@@@@@@@@@@@@@@@@")
                                #print(user_totals)
                                color_d = '#FF0000'
                                color_b = '#FF0000'
                                if float(user_totals['ด']) >= 0:
                                    color_d = '#00FF00'
                                if float(user_totals['ง']) >= 0:
                                    color_b = '#00FF00'
                                bubble = {
                                "type": "bubble",
                                'size': 'hecto',
                                "header": {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                    {
                                        "type": "text",
                                        "text": f"คำนวณล่วงหน้า คู่ที่{round_value}",
                                        "weight": "bold",
                                        "size": "lg",
                                        "align": "center"
                                    }
                                    ]
                                },
                                "hero": {
                                    "type": "image",
                                    "url": profile[2],
                                    "size": "lg",
                                    "aspectRatio": "1:1",
                                    "aspectMode": "cover"
                                },
                                "body": {
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                        {
                                            "type": "text",
                                            "text": "น้ำเงินชนะ",
                                            "color": "#0000FF",
                                            "weight": "bold",
                                            "size": "md",
                                            "align": "center"
                                        },
                                        {
                                            "type": "text",
                                            "text": str(user_totals['ง']),
                                            "color": color_b,
                                            "weight": "bold",
                                            "size": "lg",
                                            "align": "center"
                                        }
                                        ],
                                        "backgroundColor": "#E0F7FA",
                                        "cornerRadius": "10px",
                                        "borderWidth": "2px",
                                        "borderColor": "#0000FF",
                                        "margin": "sm",
                                        "paddingAll": "10px"
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [
                                        {
                                            "type": "text",
                                            "text": "แดงชนะ",
                                            "color": "#FF0000",
                                            "weight": "bold",
                                            "size": "md",
                                            "align": "center"
                                        },
                                        {
                                            "type": "text",
                                            "text": str(user_totals["ด"]),
                                            "color": color_d,
                                            "weight": "bold",
                                            "size": "lg",
                                            "align": "center"
                                        }
                                        ],
                                        "backgroundColor": "#FFEBEE",
                                        "cornerRadius": "10px",
                                        "borderWidth": "2px",
                                        "borderColor": "#FF0000",
                                        "margin": "sm",
                                        "paddingAll": "10px"
                                    }
                                    ],
                                    "spacing": "md",
                                    "justifyContent": "space-between"
                                }
                                }
                            flex_message = {
                            "type": "carousel",
                            "contents": [bubble]
                        }

                            send_flex_reply(reply_token, f"รอบที่ {round_value} ยอดแทง:", flex_message)
                            return '200'

                    elif status[1] == 'balance':
                        message = event['message']['text']
                        if 'C' == message or 'c'==message:
                            data = get_balance(user_id)
                            reply_message = f'ID:{data[0]} {data[1]}\nยอดเงินคงเหลือ {data[2]}$'
                            send_reply(reply_token, reply_message)
                            return '200'
                        elif'บช'== message:
                            message = acc_number
                            #msg1 = acc_number
                            #pic_path = f"{domain}/pictures/ac5.jpg"
                            msg1 = acc_msg
                            pic_path = f"{domain}/{acc_pic}"
                            msg2 = ac_msg
                            # pic_path1 = f"{domain}/pictures/ac1.jpg"
                            send_msg_pic_msg1(reply_token,msg1,pic_path,msg2)
                            return '200'
                        else:
                            with sqlite3.connect('rewards.db') as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT id, display_name, amount FROM reward WHERE user_id =? ', (user_id,))
                                data = cursor.fetchone()
                            if data:
                                reply_message = f'ID: {data[0]} {data[1]}\nเงินคงเหลือ= {data[2]} ฿' 
                                send_reply(reply_token,reply_message)
                                return '200'
                            else:
                                reply_message ='ยังไม่มีข้อมูล ขอ user นี้ในระบบ'
                                send_reply(reply_token,reply_message)
                                return '200'
                    
                    else:
                        return '200'
            
            elif status[1] =='bank_room':
                if role and role[0] == 'admin':
                    msg = event['message']['text']
                    if '$' in msg:
                        # try:
                            
                        operation = '+' if '+' in msg else '-'
                        parts = msg.replace('$', '').replace('+', ' ').replace('-', ' ').split()
                        uid = parts[0]
                        amount = float(parts[1])
                        new_balance = update_balance(uid, amount, operation,admin_id = user_id)
                        try:
                            reply_message = new_balance['reply']
                            send_reply(reply_token, reply_message)
                            return '200'
                        except:
                            pass
                        if new_balance is not None:
                            reply_message = f'User ID: {uid} \nNew Balance: {new_balance:.2f} ฿'
                        else:
                            reply_message = 'User ID not found.'
                        # except Exception as e:
                        #     reply_message = f'Error processing the request: {str(e)}'
                        send_reply(reply_token, reply_message)
                        continue
                    
                    elif 'A' == msg:
                        try:
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT round,sub_round,bet_ratio,max_bet FROM round ORDER BY id DESC LIMIT 1')
                                current_round = cursor.fetchone()
                                if current_round:
                                    round_value = current_round[0]
                                    sub_round = current_round[1]
                                    bet_ratio = current_round[2]
                                    max_bet = current_round[3]
                                    bet_setting = bet_ratio+'/'+str(max_bet)
                                else:
                                    reply_message = "Error: No round information available."
                                    send_reply(reply_token, reply_message)
                                    return '200'

                            # Retrieve all bets for the current round
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    SELECT user_profiles.id, user_profiles.display_name , play.user_play, play.amount_play,play.chicken
                                    FROM play
                                    JOIN user_profiles ON play.user_id = user_profiles.user_id
                                    WHERE play.round = ? AND play.sub_round = ?
                                ''', (round_value,sub_round))
                                bets = cursor.fetchall()

                            # Split bets into chunks of 20 for each bubble
                            grouped_bets = {}
                            for bet in bets:
                                user_id = bet[0]
                                display_name = bet[1]
                                user_play = bet[2]
                                amount_play = bet[3]
                                chicken = bet[4]
                                if user_id not in grouped_bets:
                                    grouped_bets[user_id] = {
                                        "id": user_id,
                                        "display_name": display_name,
                                        "user_play": [user_play],
                                        "amount_play": [amount_play],
                                        "chicken":chicken
                                    }
                                else:
                                    grouped_bets[user_id]["user_play"].append(user_play)
                                    grouped_bets[user_id]["amount_play"].append(amount_play)

                            # Convert grouped bets to a list of tuples
                            grouped_bets_list = [
                                (bet_data["id"], bet_data["display_name"], bet_data["user_play"], bet_data["amount_play"],bet_data["chicken"])
                                for bet_data in grouped_bets.values()
                            ]
                            if grouped_bets_list ==[]:
                                reply_message = 'ยังไม่มียอดแทง'
                                send_reply(reply_token,reply_message)
                                return '200'
                            
                            # Split bets into chunks of 20 for each bubble
                            chunk_size = 20
                            bet_chunks = [grouped_bets_list[i:i + chunk_size] for i in range(0, len(grouped_bets_list), chunk_size)]

                            bubbles = []
                            for chunk in bet_chunks:
                                bubbles.append(create_bet_bubble(chunk, round_value,bet_setting))

                            flex_message = {
                                "type": "carousel",
                                "contents": bubbles
                            }

                            send_flex_reply(reply_token, f"รอบที่ {round_value} ยอดแทง:", flex_message)

                        except Exception as e:
                            reply_message = f"Error fetching bets summary: {str(e)}"
                            print(reply_message)
                            return '200'
                    
                    elif 'c' == msg.lower()[0]:
                            game_id = int(msg.lower().replace('c',''))
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('SELECT user_id FROM user_profiles WHERE id =?',(game_id,))
                                u_id = cursor.fetchone()
                                if u_id:
                                    u_id = u_id[0]
                            try:
                                bets = get_bets_user(u_id)
                                if not bets:
                                    data = get_balance(u_id,pic=1)
                                    bubble = create_user_balance_bubble(data[0],data[1],data[2],data[3])
                                    flex_contents = {
                                "type": "carousel",
                                "contents": [bubble]
                            } 
                                    send_flex_reply(reply_token,'balance',flex_contents)
                                    return '200'
                                else:
                                    flex_data = create_bet_bubble1(bets,u_id)
                                    send_flex_reply(reply_token,'ยอดเล่น',flex_data)
                                    return '200'
                            except Exception as e:
                                print(f'Error in MENU C : {e}')
                                return '200'

                    elif 'บช' == msg or 'บช.' == msg or 'บัญชี'== msg or 'ฝาก' in msg:
                        message = acc_number
                        #msg1 = acc_number
                        #pic_path = f"{domain}/pictures/ac5.jpg"
                        msg1 = acc_msg
                        pic_path = f"{domain}/{acc_pic}"
                        msg2 = ac_msg
                        # pic_path1 = f"{domain}/pictures/ac1.jpg"
                        send_msg_pic_msg1(reply_token,msg1,pic_path,msg2)
                        return '200'
                    
                    elif 'ล'== msg or 'ห้องเล่น' == msg:
                        reply_message = link_play_room
                        send_reply(reply_token,reply_message)
                        return '200'                  
                    
                    # elif 'ห้องเล่น' == msg:
                    #     reply_message = link_play_room
                    #     send_reply(reply_token,reply_message)
                    #     return '200'
                    
                elif status and role[0]== 'user':
                    with sqlite3.connect(db_name) as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT id,display_name FROM user_profiles WHERE user_id = ?', (user_id,))
                        data = cursor.fetchone()
                        game_id = data[0]
                        u_name = data[1]

                    message = event['message']['text']
                    if 'C' == message or 'c'==message:
                        data = get_balance(user_id,pic=1)
                        bubble = create_user_balance_bubble(data[0],data[1],data[2],data[3])
                        flex_contents = {
                            "type": "carousel",
                            "contents": [bubble]
                        } 
                        send_flex_reply(reply_token,'balance',flex_contents)
                        # reply_message = f'ID:{data[0]} {data[1]}\nยอดเงินคงเหลือ {data[2]}$'
                        # send_reply(reply_token, reply_message)
                        return '200'
                    elif 'ถอน' in message:
                        data = get_balance(user_id,pic=1)
                        bubble = create_user_balance_bubble(data[0],data[1],data[2],data[3])
                        flex_contents = {
                            "type": "carousel",
                            "contents": [bubble]
                        } 
                        send_flex_reply(reply_token,'balance',flex_contents)
                        return '200'
                    elif 'บช' == message or 'บช.' == message or 'บัญชี'== message or 'ฝาก' in message:
                        # message = acc_number
                        # pic_path = f"{domain}/pictures/qr.jpg"
                        # pic_path1 = f"{domain}/pictures/qr.jpg"
                        # send_msg_pic1(reply_token,message,pic_path,pic_path1)
                        message = acc_number
                        #msg1 = acc_number
                        #pic_path = f"{domain}/pictures/ac5.jpg"
                        msg1 = acc_msg
                        pic_path = f"{domain}/{acc_pic}"
                        msg2 = ac_msg
                        # pic_path1 = f"{domain}/pictures/ac1.jpg"
                        send_msg_pic_msg1(reply_token,msg1,pic_path,msg2)
                        return '200'
                    elif 'ห้องเล่น' == message:
                        reply_message = link_play_room
                        send_reply(reply_token,reply_message)
                        return '200'

                    elif status[1] == 'balance':
                        message = event['message']['text']
                        if 'C' == message or 'c'==message:
                            data = get_balance(user_id,pic=1)
                            bubble = create_user_balance_bubble(data[0],data[1],data[2],data[3])
                            flex_contents = {
                                "type": "carousel",
                                "contents": [bubble]
                            } 
                            send_flex_reply(reply_token,'balance',flex_contents)
                            # reply_message = f'ID:{data[0]} {data[1]}\nยอดเงินคงเหลือ {data[2]}$'
                            # send_reply(reply_token, reply_message)
                            return '200'

                    else:
                        return '200'

            elif status[1]=='admin_room':
                if role and role[0] == 'admin':
                    if role and role[0] == 'admin':
                   
                        if 'u' == msg.lower():
                            round_value = get_present_round()
                            with sqlite3.connect(db_name) as conn:
                                cursor=conn.cursor()
                                cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ?', (round_value,))
                                records = cursor.fetchall()
                            if not records:
                                reply_message= 'ไม่พบยอดแทง'
                                send_reply(reply_token,reply_message)
                                return '200'

                            user_totals = {'ด': 0, 'ง': 0}

                            for record in records:
    
                                user_id, chicken, bet_ratio, amount_play = record
                                amount = float(amount_play)
                                parts = bet_ratio.split('/')
                                bet1= float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
                                bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)
                                main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
                                if main_score =='ส':
                                    main_score =='ด'
                                # Set special multipliers
                                sp = 1.0
                                sp2 = 1.0
                                reward_main_score = bet2/bet1
                                lose_main_score = 1
                                reward_second_score = 1 
                                lose_second_score = (bet2+0.2)/bet1
                                if bet1 == 0.9 and bet2 == 0.9:
                                    reward_main_score = 0.9
                                    reward_second_score = 0.9
                                    lose_second_score = 1
                                elif bet1 ==1 and bet2 ==0.1:
                                    lose_second_score = 0.1/(bet1-0.5)
                                elif bet1 ==1 and bet2 == 0.9:
                                    lose_second_score = 1
                                elif bet1 ==1 and bet2 ==0.95:
                                    lose_second_score= 1
                                elif bet1 ==1 and bet2 ==0.85:
                                    lose_second_score =1
                                elif bet1 > 1 and bet2 ==0.1:
                                    lose_second_score = 0.1/(bet1-0.5)

                                for result_score in ['ด', 'ง']:
                                    reward_or_penalty = 0
                                    if chicken == main_score:
                                        if result_score == chicken:
                                            # Case 1: Reward when the bet matches the main score
                                            reward_or_penalty = amount * reward_main_score
                                        else:
                                            # Case 1: Penalty when the bet loses with the main score
                                            reward_or_penalty = -amount
                                    else:
                                        if result_score == chicken:
                                            # Case 2: Reward when the result matches but not the main score
                                            reward_or_penalty = amount * reward_second_score
                                        else:
                                            # Case 2: Penalty when neither the bet nor the result matches
                                            reward_or_penalty = -amount * lose_second_score


                                    # Accumulate the profit or loss for the result
                                    user_totals[result_score] += reward_or_penalty
                                #print(user_totals)
                               
                            user_totals['ด'] = user_totals['ด']*(-1)
                            user_totals['ง'] = user_totals['ง']*(-1)
                            color_d = '#FF0000'
                            color_b = '#FF0000'
                            if float(user_totals['ด']) >= 0:
                                color_d = '#0000ff'
                            if float(user_totals['ง']) >= 0:
                                color_b = '#0000ff'
                            bubble = {
                            "type": "bubble",
                            'size': 'mega',
                            "header": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": f"คำนวณล่วงหน้า คู่ที่{round_value}",
                                    "weight": "bold",
                                    "size": "lg",
                                    "align": "center"
                                }
                                ]
                            },

                            "body": {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                    {
                                        "type": "text",
                                        "text": "น้ำเงินชนะ",
                                        "color": "#0000FF",
                                        "weight": "bold",
                                        "size": "md",
                                        "align": "center"
                                    },
                                    {
                                        "type": "text",
                                        "text": str(user_totals['ง']),
                                        "color": color_b,
                                        "weight": "bold",
                                        "size": "lg",
                                        "align": "center"
                                    }
                                    ],
                                    "backgroundColor": "#E0F7FA",
                                    "cornerRadius": "10px",
                                    "borderWidth": "2px",
                                    "borderColor": "#0000FF",
                                    "margin": "sm",
                                    "paddingAll": "10px"
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                    {
                                        "type": "text",
                                        "text": "แดงชนะ",
                                        "color": "#FF0000",
                                        "weight": "bold",
                                        "size": "md",
                                        "align": "center"
                                    },
                                    {
                                        "type": "text",
                                        "text": str(user_totals["ด"]),
                                        "color": color_d,
                                        "weight": "bold",
                                        "size": "lg",
                                        "align": "center"
                                    }
                                    ],
                                    "backgroundColor": "#FFEBEE",
                                    "cornerRadius": "10px",
                                    "borderWidth": "2px",
                                    "borderColor": "#FF0000",
                                    "margin": "sm",
                                    "paddingAll": "10px"
                                }
                                ],
                                "spacing": "md",
                                "justifyContent": "space-between"
                            }
                            }
                            flex_message = {
                            "type": "carousel",
                            "contents": [bubble]
                        }

                            send_flex_reply(reply_token, f"รอบที่ {round_value} ยอดแทง:", flex_message)
                            return '200'

                        elif 'x'==msg.lower(): 
                            round_value,sub_round = get_present_round(sub_round=1)
                            with sqlite3.connect(db_name) as conn:
                                cursor=conn.cursor()
                                cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ? AND sub_round = ?', (round_value,sub_round))
                                records = cursor.fetchall()
                            if not records:
                                reply_message= 'คุณยังไม่ได้แทงในรอบนี้'
                                send_reply(reply_token,reply_message)
                                return '200'

                            user_totals = {'ด': 0, 'ง': 0}

                            for record in records:
    
                                user_id, chicken, bet_ratio, amount_play = record
                                amount = float(amount_play)

                                # Split and convert bet ratios
                                parts = bet_ratio.split('/')
                                bet1 = float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
                                bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)
                                main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
                                if main_score =='ส':
                                    main_score =='ด'
                                # Set special multipliers
                                sp = 1.0
                                sp2 = 1.0
                                reward_main_score = bet2/bet1
                                lose_main_score = 1
                                reward_second_score = 1 
                                lose_second_score = (bet2+0.2)/bet1
                                if bet1 == 0.9 and bet2 == 0.9:
                                    reward_main_score = 0.9
                                    reward_second_score = 0.9
                                    lose_second_score = 1
                                elif bet1 ==1 and bet2 ==0.1:
                                    lose_second_score = 0.1/(bet1-0.5)
                                elif bet1 ==1 and bet2 == 0.9:
                                    lose_second_score = 1
                                elif bet1 ==1 and bet2 ==0.95:
                                    lose_second_score= 1
                                elif bet1 ==1 and bet2 ==0.85:
                                    lose_second_score =1
                                elif bet1 > 1 and bet2 ==0.1:
                                    lose_second_score = 0.1/(bet1-0.5)

                                for result_score in ['ด', 'ง']:
                                    reward_or_penalty = 0
                                    if chicken == main_score:
                                        if result_score == chicken:
                                            # Case 1: Reward when the bet matches the main score
                                            reward_or_penalty = amount * reward_main_score
                                        else:
                                            # Case 1: Penalty when the bet loses with the main score
                                            reward_or_penalty = -amount
                                    else:
                                        if result_score == chicken:
                                            # Case 2: Reward when the result matches but not the main score
                                            reward_or_penalty = amount * reward_second_score
                                        else:
                                            # Case 2: Penalty when neither the bet nor the result matches
                                            reward_or_penalty = -amount * lose_second_score


                                    # Accumulate the profit or loss for the result
                                    user_totals[result_score] += reward_or_penalty

                            user_totals['ด'] = user_totals['ด']*(-1)
                            user_totals['ง'] = user_totals['ง']*(-1)
                            color_d = '#FF0000'
                            color_b = '#FF0000'
                            if float(user_totals['ด']) >= 0:
                                color_d = '#0000ff'
                            if float(user_totals['ง']) >= 0:
                                color_b = '#0000ff'
                            bubble = {
                            "type": "bubble",
                            'size': 'mega',
                            "header": {
                                "type": "box",
                                "layout": "vertical",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": f"คำนวณล่วงหน้า คู่ที่{round_value}",
                                    "weight": "bold",
                                    "size": "lg",
                                    "align": "center"
                                }
                                ]
                            },

                            "body": {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                    {
                                        "type": "text",
                                        "text": "น้ำเงินชนะ",
                                        "color": "#0000FF",
                                        "weight": "bold",
                                        "size": "md",
                                        "align": "center"
                                    },
                                    {
                                        "type": "text",
                                        "text": str(user_totals['ง']),
                                        "color": color_b,
                                        "weight": "bold",
                                        "size": "lg",
                                        "align": "center"
                                    }
                                    ],
                                    "backgroundColor": "#E0F7FA",
                                    "cornerRadius": "10px",
                                    "borderWidth": "2px",
                                    "borderColor": "#0000FF",
                                    "margin": "sm",
                                    "paddingAll": "10px"
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                    {
                                        "type": "text",
                                        "text": "แดงชนะ",
                                        "color": "#FF0000",
                                        "weight": "bold",
                                        "size": "md",
                                        "align": "center"
                                    },
                                    {
                                        "type": "text",
                                        "text": str(user_totals["ด"]),
                                        "color": color_d,
                                        "weight": "bold",
                                        "size": "lg",
                                        "align": "center"
                                    }
                                    ],
                                    "backgroundColor": "#FFEBEE",
                                    "cornerRadius": "10px",
                                    "borderWidth": "2px",
                                    "borderColor": "#FF0000",
                                    "margin": "sm",
                                    "paddingAll": "10px"
                                }
                                ],
                                "spacing": "md",
                                "justifyContent": "space-between"
                            }
                            }
                            flex_message = {
                            "type": "carousel",
                            "contents": [bubble]
                        }

                            send_flex_reply(reply_token, f"รอบที่ {round_value} ยอดแทง:", flex_message)
                            return '200'

                        elif 'm'==msg.lower():
                            with sqlite3.connect(db_name) as conn:
                                cursor=conn.cursor()
                                cursor.execute("SELECT profit FROM result")
                                all_profit = cursor.fetchall()
                                total_profit = sum(int(profit[0]) for profit in all_profit if profit[0] is not None)
                            reply_message = f"กำไร/ขาดทุน ทั้งหมดของวันนี้: {total_profit}"
                            send_reply(reply_token,reply_message)
                            return '200'
                        
                        elif 'lc'==msg.lower():
                            rewards_summarys = calculate_rewards()
                            print(rewards_summarys)
                            if not rewards_summarys :
                                reply_message = 'ยังไม่พบยอดเล่นของลูกค้า'
                                send_reply(reply_token,reply_message)
                                return '200'

                            bb_contents = []
                            for rewards in rewards_summarys.split('\n'):
                                #print(rewards)
                                name_id = rewards.split('|')[0]
                                prize = rewards.split('|')[1]
                                bb_content = {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {"type": "text", "text": name_id},
                                    {"type": "text", "text": prize,"align": "end"},

                                    ]
                                    }
                                bb_contents.append(bb_content)
                            
                            bubble = {
                                "type": "bubble",
                                "size":"giga",
                                "hero": {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": [
                                        {"type": "text", "text": game_name, "align": "center", "size": "xxl", "color": "#FFFFFF", "weight": "bold"},
                                        {"type": "text", "text": f"สรุปยอดเงิน ทั้งหมด", "align": "center", "size": "xl", "color": "#FFFFFF", "weight": "bold"}
                                    ],
                                    "backgroundColor": "#0000FF"
                                },
                                "body": {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": bb_contents
                                }
                            }
                            flex_contents = {
                                "type": "carousel",
                                "contents": [bubble]
                            }
                            send_flex_reply(reply_token,'สรุปรอบ',flex_contents)
                            return '200'
                        
                        elif 'ใหม่'==msg or 'เริ่มใหม่'==msg or 'Reset'==msg:
                            PWD = generate_order_id(k=4)
                            reply_message = f'ถ้าต้องการยืนยัน เริ่มรอบใหม่ให้พิมพ์ว่า !{PWD} \n หมายเหตุ เมื่อทำการเริ่มรอบหน้าข้อมูลที่ถูกกรอกมาทั้งหมดจะหายไป'
                            reply_message2 = f"!{PWD}"
                            send_reply2(reply_token,reply_message,reply_message2)
                            return '200'
                        
                        elif f'!{PWD}' == msg:
                            print('!password Corrected')
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute('DROP TABLE IF EXISTS round')
                                cursor.execute('''
                                    CREATE TABLE IF NOT EXISTS round(
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        round INT,
                                        bet_ratio TEXT,
                                        max_bet INT,
                                        sub_round INT )
                                            ''')
                                                            
                                # Drop and recreate the 'combined_lotto_data' table
                                cursor.execute('DROP TABLE IF EXISTS play')
                                cursor.execute('''
                                    CREATE TABLE IF NOT EXISTS play(
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user_id TEXT,
                                        round INT,
                                        user_play TEXT,
                                        chicken TEXT,
                                        bet_ratio TEXT,
                                        amount_play TEXT,
                                        sub_round INT
                                            )
                            ''')
                                cursor.execute('DROP TABLE IF EXISTS result')
                                cursor.execute('''
                                    CREATE TABLE IF NOT EXISTS result(
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        chicken TEXT,
                                        round INT,
                                        profit INT
                                                    )
                            ''')
                                cursor.execute('DROP TABLE IF EXISTS log_add_remove_balance')
                                cursor.execute("""
                                    CREATE TABLE IF NOT EXISTS log_add_remove_balance (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user_id TEXT ,
                                        admin_id TEXT,
                                        amount TEXT,
                                        datetime TEXT
                                )
                            """)
                                cursor.execute('INSERT INTO round (round) VALUES (?)', (0,))
                                # Commit changes to the database
                                conn.commit()
                            print('Done Reset')
                            reply_message = 'ทำการเริ่มรอบใหม่เรียบร้อย'
                            send_reply(reply_token,reply_message)
                            PWD = generate_order_id(k=15)
                            return '200'
                        
                        elif 'cm' == msg.lower():
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute("SELECT id, display_name, backup_amount FROM user_profiles")
                                all_account = cursor.fetchall()

                            if not all_account:
                                send_reply(reply_token, "No accounts found.")
                                return '200'

                            # Initialize Flex Message contents
                            flex_contents = []

                            # Generate Flex Message contents for each account
                            for account in all_account:
                                user_id, display_name, backup_amount = account
                                flex_contents.append({
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": f"{user_id}) {display_name}",
                                            "size": "sm",
                                            "color": "#555555",
                                            "flex": 2
                                        },
                                        {
                                            "type": "text",
                                            "text": f"฿{backup_amount}",
                                            "size": "sm",
                                            "color": "#1DB446",
                                            "align": "end",
                                            "flex": 2
                                        }
                                    ]
                                })

                            # Wrap contents in a Flex Message
                            flex_message = {
                                "type": "bubble",
                                "body": {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": flex_contents
                                }
                            }

                            # Send the Flex Message reply
                            send_flex_reply(reply_token, 'All account', flex_message)
                        
                        elif f'!{PWD_cr}'== msg:
                            print('password CR filled')
                            with sqlite3.connect(db_name) as conn:
                                cursor = conn.cursor()
                                cursor.execute("UPDATE user_profiles SET amount = 0, backup_amount = 0")
                                conn.commit()
                                cursor.execute("SELECT id, display_name, backup_amount FROM user_profiles")
                                all_account = cursor.fetchall()

                            if not all_account:
                                send_reply(reply_token, "No accounts found.")
                                return '200'

                            # Initialize Flex Message contents
                            flex_contents = []

                            # Generate Flex Message contents for each account
                            for account in all_account:
                                user_id, display_name, backup_amount = account
                                flex_contents.append({
                                    "type": "box",
                                    "layout": "horizontal",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": f"{user_id}) {display_name}",
                                            "size": "sm",
                                            "color": "#555555",
                                            "flex": 2
                                        },
                                        {
                                            "type": "text",
                                            "text": f"฿{backup_amount}",
                                            "size": "sm",
                                            "color": "#1DB446",
                                            "align": "end",
                                            "flex": 2
                                        }
                                    ]
                                })

                            # Wrap contents in a Flex Message
                            flex_message = {
                                "type": "bubble",
                                "body": {
                                    "type": "box",
                                    "layout": "vertical",
                                    "contents": flex_contents
                                }
                            }

                            # Send the Flex Message reply
                            send_flex_reply(reply_token, 'All account', flex_message)
                            return '200'
                        
                        elif 'cr' == msg.lower():
                            PWD_cr = generate_order_id(k=4)
                            reply_message = f'ถ้าต้องการเคลียยอดเงินทั้งหมดให้ พิมพ์ !{PWD_cr} \n หมายเหตุ ยอดเงินนี้ไม่สามารถนำกลับมาได้ กรุณาเช็คว่าทุก user ถอนเงินหมดแล้ว'
                            reply_message2 = f"!{PWD_cr}"
                            send_reply2(reply_token,reply_message,reply_message2)
                            return '200'
                        
                        elif 'c' == msg.lower()[0]:
                            try:
                                game_id = int(msg.lower().replace('c',''))
                                with sqlite3.connect(db_name) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute('SELECT user_id FROM user_profiles WHERE id =?',(game_id,))
                                    u_id = cursor.fetchone()
                                    if u_id:
                                        u_id = u_id[0]
                           
                                bets = get_bets_user(u_id)
                                if not bets:
                                    data = get_balance(u_id,pic=1)
                                    bubble = create_user_balance_bubble(data[0],data[1],data[2],data[3])
                                    flex_contents = {
                                "type": "carousel",
                                "contents": [bubble]
                            } 
                                    send_flex_reply(reply_token,'balance',flex_contents)
                                    return '200'
                                else:
                                    flex_data = create_bet_bubble1(bets,u_id)
                                    send_flex_reply(reply_token,'ยอดเล่น',flex_data)
                                    return '200'
                            except Exception as e:
                                print(f'Error in MENU C : {e}')
                                return '200'

                else:
                    print('you have no access')
                
        return '200 OK'
    else:
        return '200 OK'

@app.route('/get_data', methods=['GET'])
def get_data():
    round_value = get_present_round()
    if not round_value:
        return jsonify({"error": "No round information available"}), 400

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(play.namtao), SUM(play.poo), SUM(play.pla), SUM(play.kai), SUM(play.goong), SUM(play.suer),SUM(play.high) ,SUM(play.low)
            FROM play
            WHERE play.round = ?
        ''', (round_value,))
        aggregated_bets = cursor.fetchone()
        cursor.execute('''
            SELECT status FROM focus_group WHERE role = ?
        ''', ('play_room',))
        status = cursor.fetchone()[0]
        if status == 'play':
            ss = 'open'
        elif status == 'closed':
            ss = 'reward'
        else:
            ss = 0
        cursor.execute('SELECT namtao, poo, pla, kai, goong, suer,high,low FROM result WHERE round = ?', (round_value,))
        result = cursor.fetchone()
        if not result:
            result_dict = {}
        else:
            result_dict = {
                'น้ำเต้า': result[0],
                'ปู': result[1],
                'ปลา': result[2],
                'ไก่': result[3],
                'กุ้ง': result[4],
                'เสือ': result[5],
                'สูง': result[6],
                'ต่ำ':result[7]
            }
            
    if aggregated_bets:
        bet_summary = {
            "round_value": round_value,
            'status':ss,
            'data':{
            "namtao": aggregated_bets[0],
            "poo": aggregated_bets[1],
            "pla": aggregated_bets[2],
            "kai": aggregated_bets[3],
            "goong": aggregated_bets[4],
            "suer": aggregated_bets[5],
            "high": aggregated_bets[6],
            "low": aggregated_bets[7],
            },
            'result':result_dict
        }
    else:
        bet_summary = {
            "round_value": round_value,
            'status':ss,
            'data':{
            "namtao": 0,
            "poo": 0,
            "pla": 0,
            "kai": 0,
            "goong": 0,
            "suer": 0,
            "high":0,
            "low":0},
            'result':result_dict
        }

    return jsonify(bet_summary)


@app.route('/get_admin_data',methods=['GET'])
def get_admin_data():
    send_data={
        'username': 'admin',
        'profile_pic':''
    }
    all_data = {
        "data":send_data,
        "status": 200

    }
    return jsonify(all_data)

@app.route('/get_conclude_bet', methods=['GET'])
def get_conclude_bet():
    round_value = request.args.get('round', None)
    
    # Get pagination parameters from the request (default to page 1 and limit 10 if not provided)
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    
    # Calculate the offset based on the page and limit
    offset = (page - 1) * limit
    
    # Fetch data with pagination (modify your data-fetching logic accordingly)
    data = calculate_rewards1(type_data='56', round=round_value, limit=limit, offset=offset)
    
    datas = data.get('data', None)
    
    if datas:
        send_datas = []
        for record in datas:
            send_data = {
                'id': record.get('game_id'),
                'username': record.get('username'),
                'investment': float(record.get('amount_play')),
                'win_loss': float(record.get('reward')),
                'available': float(record.get('balance')),
                'detail': '#'
            }
            send_datas.append(send_data)
        
        # Create the response with paginated data
        pagination = data.get('pagination','')
        if pagination:
            total_record = pagination['total_records']
        all_data = {
            'data': send_datas,
            'status': '200',
            'pagination': {
                'page': page,
                'limit': limit,
                'total_records': total_record,  # Assuming your API response includes a total count
                "total_pages": math.ceil(total_record/limit)
            }
        }
        return jsonify(all_data)
    else:
        return jsonify({'data': '', 'status': '401'})

@app.route('/check_role', methods=['GET'])
def check_role():
    try:
        data = request.args.get('data', '')
        decoded_data = base64.b64decode(data).decode('utf-8')
        timestamp_str = decoded_data.split('|')[0]
        id = decoded_data.split('|')[1]
        timestamp = datetime.fromtimestamp(int(timestamp_str) / 1000)
        current_time = datetime.now()
        time_difference = current_time - timestamp
        if time_difference > timedelta(minutes=5):
            return 'Error Timestamp', 405
        if id == 'U435043c0b72fcf707f2592be6987ac11':
            return_data = {'role':'admin'}
            return jsonify(return_data)
        if id: 
            with sqlite3.connect(db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT role FROM admin_group WHERE user_id = ?', (id,))
                role = cursor.fetchone()[0]
                return_data = {'role':role}
            return jsonify(return_data)
        
        else:
            return 'Error', 405
    except Exception as e:
        print(f"An error occurred: {e}")  # Log the error for debugging
        return 'Error', 200

@app.route('/get_profit', methods=['GET'])
def get_profit():
    # Retrieve pagination parameters (defaults: page 1, limit 10)
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    
    # Calculate the offset
    offset = (page - 1) * limit
    
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

        # Get the total number of records for pagination
        cursor.execute('SELECT COUNT(*) FROM result')
        total_records = cursor.fetchone()[0]

        # Fetch profit data with pagination
        cursor.execute('''
            SELECT profit, round FROM result
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        datas = cursor.fetchall()

        if datas:
            send_datas = []
            profit = 0 
            withdraw = 0
            deposit = 0
            sum_deposit_withdraw = 0
            sum_user_balance = 0

            # Calculate profit
            for data in datas:
                if not data[0]:
                    continue
                profit += data[0]
                
            # Fetch log records for deposit and withdraw amounts
            cursor.execute('SELECT user_id, admin_id, amount FROM log_add_remove_balance')
            records = cursor.fetchall()
            for record in records:
                if record[1] != 'game' and record[1] != 'recall':
                    amount = record[2]
                    if '+' in amount:
                        amount = amount.replace('+', '')
                        amt_type = 'deposit'
                    elif '-' in amount:
                        amount = amount.replace('-', '')
                        amt_type = 'withdraw'
                    if amt_type == 'deposit':
                        deposit += float(amount)
                    elif amt_type == 'withdraw':
                        withdraw += float(amount)
            sum_deposit_withdraw = deposit - withdraw

            # Calculate sum of user balances
            cursor.execute('SELECT amount FROM user_profiles')
            user_profile_record = cursor.fetchall()
            if user_profile_record:
                for user in user_profile_record:
                    sum_user_balance += float(user[0])

            # Prepare the response data
            all_data = {
                'data': {
                    'deposit': deposit,
                    'withdraw': withdraw,
                    'sum_deposit_withdraw': sum_deposit_withdraw,
                    'sum_user_balance': sum_user_balance,
                    'profit': profit
                },
                'status': '200',
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_records': total_records,
                    "total_pages": math.ceil(total_records/limit)
                }
            }
            return jsonify(all_data)
        else:
            return jsonify({'status': '205'})  # No data found
        
@app.route('/get_deposit', methods=['GET'])
def get_deposit():
    # Retrieve pagination parameters (defaults: page 1, limit 10)
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))

    # Calculate the offset for pagination
    offset = (page - 1) * limit

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

        # Get the total number of deposit records for pagination
        cursor.execute('''
            SELECT COUNT(*) 
            FROM log_add_remove_balance
            WHERE admin_id != 'game' AND admin_id != 'recall' AND amount LIKE '+%'
        ''')
        total_records = cursor.fetchone()[0]

        # Fetch deposit records with pagination
        cursor.execute('''
            SELECT user_id, admin_id, amount, datetime 
            FROM log_add_remove_balance
            WHERE admin_id != 'game' AND admin_id != 'recall' AND amount LIKE '+%'
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        deposit_records = cursor.fetchall()

        if deposit_records:
            deposit_details = []  # To store deposits in the required format

            for record in deposit_records:
                user_id, admin_id, amount, timestamp = record
                amount = float(amount.replace('+', ''))  # Extract deposit amount

                # Fetch the username (display_name) for the user_id
                cursor.execute('''
                    SELECT id, display_name 
                    FROM user_profiles 
                    WHERE id = ?
                ''', (user_id,))
                user_info = cursor.fetchone()

                if user_info:
                    game_id, username = user_info
                    deposit_details.append({
                        'game_id': game_id,
                        'username': username,
                        'deposit': amount,
                        'time': timestamp
                    })

            # Prepare the response with paginated data
            all_data = {
                'data': deposit_details,
                'status': '200',
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_records': total_records,
                    "total_pages": math.ceil(total_records/limit)
                }
            }
            return jsonify(all_data)
        else:
            return jsonify({'status': '205'})  # No deposit records found
        

@app.route('/get_withdraw', methods=['GET'])
def get_withdraw():
    # Retrieve pagination parameters (defaults: page 1, limit 10)
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))

    # Calculate the offset for pagination
    offset = (page - 1) * limit

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

        # Get the total number of withdraw records for pagination
        cursor.execute('''
            SELECT COUNT(*) 
            FROM log_add_remove_balance
            WHERE admin_id != 'game' AND admin_id != 'recall' AND amount LIKE '-%'
        ''')
        total_records = cursor.fetchone()[0]

        # Fetch withdraw records with pagination
        cursor.execute('''
            SELECT user_id, admin_id, amount, datetime 
            FROM log_add_remove_balance
            WHERE admin_id != 'game' AND admin_id != 'recall' AND amount LIKE '-%'
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        withdraw_records = cursor.fetchall()

        if withdraw_records:
            withdraw_details = []  # To store withdraw records in the required format

            for record in withdraw_records:
                user_id, admin_id, amount, timestamp = record
                amount = float(amount.replace('-', ''))  # Extract withdraw amount

                # Fetch the username (display_name) for the user_id
                cursor.execute('''
                    SELECT id, display_name 
                    FROM user_profiles 
                    WHERE id = ?
                ''', (user_id,))
                user_info = cursor.fetchone()

                if user_info:
                    game_id, username = user_info
                    withdraw_details.append({
                        'game_id': game_id,
                        'username': username,
                        'withdraw': amount,
                        'time': timestamp
                    })

            # Prepare the response with paginated data
            all_data = {
                'data': withdraw_details,
                'status': '200',
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_records': total_records,
                    "total_pages": math.ceil(total_records/limit)
                }
            }
            return jsonify(all_data)
        else:
            return jsonify({'status': '205'})  # No withdraw records found
        
@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    # Get page and limit parameters from the request, with defaults
    page = request.args.get('page', default=1, type=int)
    limit = request.args.get('limit', default=10, type=int)

    # Calculate the offset for SQL query
    offset = (page - 1) * limit

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

        # Fetch the total number of users for pagination metadata
        cursor.execute('SELECT COUNT(*) FROM user_profiles')
        total_users = cursor.fetchone()[0]

        if total_users == 0:
            return jsonify({"status": "404", "error": "No users found"}), 404

        # Fetch paginated users with their balances
        cursor.execute('''
            SELECT id, display_name, amount, user_id 
            FROM user_profiles
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        user_records = cursor.fetchall()

        result = []

        for user_id, username, amount, line_id in user_records:
            # Calculate win amounts
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(CASE WHEN admin_id = 'game' AND amount LIKE '+%' THEN CAST(REPLACE(amount, '+', '') AS REAL) ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN admin_id = 'recall' AND amount LIKE '-%' THEN CAST(REPLACE(amount, '-', '') AS REAL) ELSE 0 END), 0)
                FROM log_add_remove_balance
                WHERE user_id = ?
            ''', (user_id,))
            win = cursor.fetchone()[0]

            # Calculate loss amounts
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(CASE WHEN admin_id = 'game' AND amount LIKE '-%' THEN CAST(REPLACE(amount, '-', '') AS REAL) ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN admin_id = 'recall' AND amount LIKE '+%' THEN CAST(REPLACE(amount, '+', '') AS REAL) ELSE 0 END), 0)
                FROM log_add_remove_balance
                WHERE user_id = ?
            ''', (user_id,))
            lose = cursor.fetchone()[0]

            # Calculate total win/lose
            total_win_lose = win - lose

            # Count rounds played
            cursor.execute('''
                SELECT COUNT(*)
                FROM (
                    SELECT DISTINCT user_id, round
                    FROM play
                    WHERE user_id = ?
                ) AS unique_round
            ''', (line_id,))
            round_play = cursor.fetchone()[0]

            # Append user data to results
            result.append({
                "id": user_id,
                "username": username,
                "amount": float(amount),
                "win": float(win),
                "lose": float(lose),
                "total_win_lose": float(total_win_lose),
                "round_play": round_play,
                "status": 0,
                "turn_over": float(abs(win) + abs(lose))
            })

        # Pagination metadata
        total_pages = (total_users + limit - 1) // limit  # Calculate total pages

        return jsonify({
            "data": result,
            "status": "200",
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_users": total_users,
                "count":total_users,
                "limit": limit
            }
        })

@app.route('/get_amount_data', methods=['GET'])
def get_amount_data():

    round_value = get_present_round()
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT namtao, poo, pla, kai, goong, suer, high, low, amount_play
            FROM play
            WHERE round = ?
        ''', (round_value,))
        bets = cursor.fetchall()

        total_bets = {
            'namtao': 0,
            'poo': 0,
            'pla': 0,
            'kai': 0,
            'goong': 0,
            'suer': 0,
            'high': 0,
            'low': 0
        }

        for bet in bets:
            user_bet = {
                'namtao': bet[0],
                'poo': bet[1],
                'pla': bet[2],
                'kai': bet[3],
                'goong': bet[4],
                'suer': bet[5],
                'high': bet[6],
                'low': bet[7]
            }
            amount_play = float(bet[8])
            bet_items = [item for item, amount in user_bet.items() if amount > 0]
            
            for item, amount in user_bet.items():
                if len(bet_items) == 1:
                    total_bets[item] += amount * amount_play
                elif len(bet_items) == 2:
                    total_bets[item] += amount * amount_play / 2
                elif len(bet_items) == 3:
                    total_bets[item] += amount * amount_play / 3

        return jsonify(total_bets)

@app.route('/get_round_price', methods=['GET'])
def get_round_price():
    round_value = request.args.get('round', None)
    if not round_value:
        return jsonify({'error': 'Need some Round', 'status': 401}), 401

    # Retrieve pagination parameters (defaults: page 1, limit 10)
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))

    # Calculate the offset
    offset = (page - 1) * limit

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

        # Get the total number of records for pagination
        cursor.execute('''
            SELECT COUNT(DISTINCT sub_round) 
            FROM play 
            WHERE round = ?
        ''', (round_value,))
        total_records = cursor.fetchone()[0]

        # Fetch paginated data
        cursor.execute('''
            SELECT sub_round, round, bet_ratio
            FROM play
            WHERE round = ?
            GROUP BY sub_round
            LIMIT ? OFFSET ?
        ''', (round_value, limit, offset))
        datas = cursor.fetchall()

        send_datas = []
        for data in datas:
            if 'ง' in data[2]:
                bet_ratio = data[2].replace('ง', 'น้ำเงินต่อ')
            elif 'ด' in data[2]:
                bet_ratio = data[2].replace('ด', 'แดงต่อ')
            else:
                bet_ratio = data[2]
            send_data = {
                'sub_round': data[0],
                'bet_ratio': bet_ratio
            }
            send_datas.append(send_data)

        # Prepare response with paginated data
        all_data = {
            "data": send_datas,
            "status": 200,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": math.ceil(total_records/limit)
            }
        }
        return jsonify(all_data)
    
@app.route('/get_sround_bet', methods=['GET'])
def get_sround_bet():
    sub_round = request.args.get('sub_round', '')
    round_value = request.args.get('round', '')

    if not sub_round or not round_value:
        return jsonify({"error": "sub_round and round are required", "status": 400}), 400

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

        # Use SQL JOIN to fetch data from `play` and `user_profiles` in one query
        cursor.execute('''
            SELECT 
                p.user_id, 
                up.display_name, 
                p.chicken, 
                p.amount_play
            FROM play p
            JOIN user_profiles up ON p.user_id = up.user_id
            WHERE p.round = ? AND p.sub_round = ?
        ''', (round_value, sub_round))

        # Fetch all results
        datas = cursor.fetchall()

        # Prepare the response data
        send_datas = []
        for data in datas:
            if data[2] == 'ง':
                chicken = 'น้ำเงิน'
            elif data[2]=='ด':
                chicken ='แดง'
            send_data = {
                'user_name': data[1],  # display_name from user_profiles
                'chicken': chicken,   # chicken from play
                'amount': int(data[3])     # amount_play from play
            }
            send_datas.append(send_data)

        # Return the JSON response
        all_data = {
            "data": send_datas,
            "status": 200
        }
        return jsonify(all_data)
    
@app.route('/login', methods=['POST'])
def login():
    """
    Simulates login and returns an access token.
    """
    data = request.get_json()

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({
            'status': 400,
            'message': 'Username and password are required'
        }), 400

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM user_pass WHERE username = ?", (username,))
        pw = cursor.fetchone()

    if pw:
        if password == pw[0]:  # This should use a hashed password check
            access_token = create_access_token(identity=username, expires_delta=False)
            return jsonify({
                'status': 200,
                'message': 'Login successful',
                'data': {'bearer_token': f'Bearer {access_token}'}
            }), 200
        else:
            return jsonify({
                'status': 401,
                'message': 'Invalid username or password'
            }), 401
    else:
        return jsonify({
            'status': 404,
            'message': 'Username not found'
        }), 404
    
@app.route('/change_password', methods=['POST'])
def change_password():
    data = request.get_json()

    username = data.get('username')
    old_pass = data.get('old_password')
    new_pass = data.get('new_password')
    
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        # Fetch the current password for the username
        cursor.execute("SELECT password FROM user_pass WHERE username = ?", (username,))
        pw = cursor.fetchone()

        if pw:
            if old_pass == pw[0]:
                # Update the password
                cursor.execute("UPDATE user_pass SET password = ? WHERE username = ?", (new_pass, username))
                conn.commit()  # Commit the transaction
                return {"data":"","status": 200, "message": "Password updated successfully."}
            else:
                return {"data":"","status": 400, "message": "Old password is incorrect."}
        else:
            return {"status": "error", "message": "User not found."}, 404
        

@app.route('/is_login', methods=['GET'])
@jwt_required()  # This decorator ensures the request has a valid access token
def is_login():
    """
    Checks if the user is logged in and returns user details if valid.
    """
    current_user = get_jwt_identity()  # Get user identity from token
    if current_user:
        # Convert identity (dictionary) to a JSON string before creating a new token
        access_token = create_access_token(identity=current_user, expires_delta=False)
        data = {
            'data': {'access_token': f'Bearer {access_token}'},
            'message': {
                'code': 0,
                'message': 'User is logged in.'
            },
            'status': {
                'code': 200,
                'message': 'success'
            },
        }
        return jsonify(data)
    else:
        data = {
            'data': None,
            'message': {
                'code': 1,  # Use a different code to indicate access denied
                'message': 'Access denied, user not logged in'
            },
            'status': {
                'code': 401,
                'message': 'unauthorized'
            }
        }
        return jsonify(data), 401


@app.route('/edit_sql',methods=['GET'])
def settings():
    return send_from_directory('login')


@app.route('/get_chicken_bet',methods=['GET'])
def get_chicken_bet():
    round_value = get_present_round()
    with sqlite3.connect(db_name) as conn:
        cursor=conn.cursor()
        cursor.execute('SELECT user_id, chicken, bet_ratio, amount_play FROM play WHERE round = ?', (round_value,))
        records = cursor.fetchall()
    if not records:
        send_data = {
            'data':{'red':0,'blue':0,'round':round_value},
            'status':'200'
        }
        return jsonify(send_data)
    user_totals = {'ด': 0, 'ง': 0}

    for record in records:

        user_id, chicken, bet_ratio, amount_play = record
        amount = float(amount_play)

        # Split and convert bet ratios
        parts = bet_ratio.split('/')
        bet1 = float(parts[1]) / 10  # Convert to decimal format (e.g., 2 -> 0.2)
        bet2 = float(parts[2]) / 10  # Convert to decimal format (e.g., 4 -> 0.4)
        main_score = parts[0][0]  # The first character is the main score ('ด' or 'ง')
        if main_score =='ส':
            main_score =='ด'
        # Set special multipliers
        sp = 1.0
        sp2 = 1.0
        reward_main_score = bet2/bet1
        lose_main_score = 1
        reward_second_score = 1 
        lose_second_score = (bet2+0.2)/bet1
        if bet1 == 0.9 and bet2 == 0.9:
            reward_main_score = 0.9
            reward_second_score = 0.9
            lose_second_score = 1
        elif bet1 ==1 and bet2 ==0.1:
            lose_second_score = 0.1/(bet1-0.5)
        elif bet1 ==1 and bet2 == 0.9:
            lose_second_score = 1
        elif bet1 ==1 and bet2 ==0.95:
            lose_second_score= 1
        elif bet1 ==1 and bet2 ==0.85:
            lose_second_score =1
        elif bet1 > 1 and bet2 ==0.1:
            lose_second_score = 0.1/(bet1-0.5)

        for result_score in ['ด', 'ง']:
            reward_or_penalty = 0
            if chicken == main_score:
                if result_score == chicken:
                    # Case 1: Reward when the bet matches the main score
                    reward_or_penalty = amount * reward_main_score
                else:
                    # Case 1: Penalty when the bet loses with the main score
                    reward_or_penalty = -amount
            else:
                if result_score == chicken:
                    # Case 2: Reward when the result matches but not the main score
                    reward_or_penalty = amount * reward_second_score
                else:
                    # Case 2: Penalty when neither the bet nor the result matches
                    reward_or_penalty = -amount * lose_second_score


            # Accumulate the profit or loss for the result
            user_totals[result_score] += reward_or_penalty
        red = user_totals['ด']
        blue = user_totals["ง"]
        if user_totals['ด'] ==0:
            red = 0
        if user_totals['ง'] ==0:
            blue =0

    send_data = {
        'data':{
            'red':red*-1,
            'blue':blue*-1,
            'round':round_value
        },
        'status':'200'
    }
    return jsonify(send_data)

@app.route('/get_result', methods=['GET'])
def get_result():
    # Retrieve pagination parameters (defaults: page 1, limit 10)
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))

    # Calculate the offset for pagination
    offset = (page - 1) * limit

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()

        # Get the total number of records for pagination
        cursor.execute('SELECT COUNT(*) FROM result')
        total_records = cursor.fetchone()[0]

        # Fetch paginated results
        cursor.execute('''
            SELECT chicken, round, profit
            FROM result
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        datas = cursor.fetchall()

        if datas:
            send_datas = []
            for data in datas:
                if data[0] == 'ด':
                    chicken = 'แดง'
                elif data[0] == 'ง':
                    chicken = 'น้ำเงิน'
                else:
                    chicken = 'ส'

                send_data = {
                    'chicken': chicken,
                    'round': data[1],
                    'profit': data[2]
                }
                send_datas.append(send_data)

            # Prepare response with paginated data
            final_data = {
                'data': send_datas,
                'status': 200,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_records': total_records,
                    "total_pages": math.ceil(total_records/limit)
                    
                }
            }
        else:
            # No data found for the query
            final_data = {
                'data': [],
                'status': 200,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_records': total_records,
                    "total_pages": math.ceil(total_records/limit)
                    
                }
            }

    return jsonify(final_data)

@app.route('/get_setting')
def get_setting():
    client_ip = request.remote_addr
    print("Connected client IP:", client_ip)
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT min_bet,max_bet_total,max_auto_close,max_round FROM settings WHERE ID=1')
        data = cursor.fetchone()
        if data: 
            send_data = {
                'data':{
                    'min_bet':data[0],
                    'max_bet_total':data[1],
                    'max_auto_close':data[2],
                    'max_round':data[3]
                },
                'status':'success',
                'code':'200'
            }
            return jsonify(send_data)
        else:
            send_data = {
                'data':{
                    'min_bet':0,
                    'max_bet_total':0,
                    'max_auto_close':0,
                    'max_round':0
                },
                'status':'success',
                'code':'200'
            }
            return jsonify(send_data)

@app.route('/change_setting', methods=['POST'])
def change_setting():
    try:
        data = request.get_json()
        min_bet = data.get('min_bet')
        max_bet_total = data.get('max_bet_total')  # Maximum total bet amount
        max_auto_close = data.get('max_auto_close')  # Maximum auto-close value
        max_round = data.get('max_round')  # Maximum number of rounds

        # Validate input data
        if None in [min_bet, max_bet_total, max_auto_close, max_round]:
            return jsonify({"error": "All settings (min_bet, max_bet_total, max_auto_close, max_round) are required"}), 400

        # Database connection and query
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            # Update or insert settings
            cursor.execute("""
                INSERT INTO settings (id, min_bet, max_bet_total, max_auto_close, max_round)
                VALUES (1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                min_bet = excluded.min_bet,
                max_bet_total = excluded.max_bet_total,
                max_auto_close = excluded.max_auto_close,
                max_round = excluded.max_round
            """, (min_bet, max_bet_total, max_auto_close, max_round))
            conn.commit()

        return jsonify({"success": "Settings updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

def save_file(file, upload_folder):
    """
    Helper function to save a file and return its file path.
    """
    random_string = generate_random_string()
    file_path = os.path.join(upload_folder, f"upload_{random_string}.png")
    file.save(file_path)
    return f'{request.url_root}{file_path}'


@app.route('/get_pic_setting', methods=['GET'])
def get_pic_setting():
    try:
        # Connect to the database
        with sqlite3.connect(db_name) as conn:
            conn.row_factory = sqlite3.Row  # To access rows as dictionaries
            cursor = conn.cursor()

            # Query all saved settings
            cursor.execute("SELECT * FROM settings2")
            settings = cursor.fetchall()

            # Convert the data to a list of dictionaries
            result = [dict(row) for row in settings]
            
        return jsonify({"status": 200, "data": result[0]}), 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"status": 401, "message": str(e)}), 500


@app.route('/save_setting', methods=['POST'])
def save_setting():
    try:
        # Directory to save uploaded pictures
        UPLOAD_FOLDER = 'pic'
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Collect form data
        data = request.form
        link_acc_room = data.get('link_acc_room')
        link_play_room = data.get('link_play_room')
        acc_num = data.get('acc_num')
        game_name = data.get('game_name')
        ac_msg = data.get('ac_msg')
        msg_how_to_play = data.get('msg_how_to_play')

        # Variables for file paths (decoded images)
        acc_pic = decode_and_save_image(data.get('acc_pic'), UPLOAD_FOLDER, 'acc_pic') if data.get('acc_pic') else None
        open_pic = decode_and_save_image(data.get('open_pic'), UPLOAD_FOLDER, 'open_pic') if data.get('open_pic') else None
        close_pic = decode_and_save_image(data.get('close_pic'), UPLOAD_FOLDER, 'close_pic') if data.get('close_pic') else None
        red_win = decode_and_save_image(data.get('red_win'), UPLOAD_FOLDER, 'red_win') if data.get('red_win') else None
        blue_win = decode_and_save_image(data.get('blue_win'), UPLOAD_FOLDER, 'blue_win') if data.get('blue_win') else None
        tie = decode_and_save_image(data.get('tie'), UPLOAD_FOLDER, 'tie') if data.get('tie') else None
        how_to_play_pic = decode_and_save_image(data.get('how_to_play'), UPLOAD_FOLDER, 'how_to_play') if data.get('how_to_play') else None

        # Save data to SQLite
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE settings2
                SET link_acc_room = ?, link_play_room = ?, acc_num = ?, acc_pic = ?, 
                    game_name = ?, ac_msg = ?, open_pic = ?, close_pic = ?, 
                    red_win = ?, blue_win = ?, tie = ?, how_to_play_pic = ?, msg_how_to_play = ?
                WHERE id = 1
            """, (
                link_acc_room, link_play_room, acc_num, acc_pic,
                game_name, ac_msg, open_pic, close_pic,
                red_win, blue_win, tie, how_to_play_pic, msg_how_to_play
            ))
            conn.commit()
        get_img_setting()
        return jsonify({"status": 200, "message": "Settings and files saved successfully!"})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"status": 401, "message": str(e)})


def decode_and_save_image(base64_string, upload_folder, prefix):

    try:
        header, encoded = base64_string.split(',', 1)  # Split Base64 header and data
        file_data = base64.b64decode(encoded)
        ext = header.split('/')[1].split(';')[0]  # Extract file extension (e.g., png, jpg)
        filename = f"{prefix}_{generate_random_string()}.{ext}"  # Unique filename
        file_path = os.path.join(upload_folder, filename)

        with open(file_path, 'wb') as f:
            f.write(file_data)

        return file_path.replace('pic' , "pictures",1)
    except Exception as e:
        raise ValueError(f"Failed to decode and save image: {e}")

@socketio.on('connect')
def handle_connect():
    try:
        # Simulate a connection check
        socketio.emit('connected')
        print('connected')
    except Exception as e:
        print(f"Error during connection: {str(e)}")

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    socketio.emit('disconnect',{'status':'disconnect'})

if __name__ == '__main__':
    
    #from waitress import serve
    print('sv_start !!!!!')
 
    init_db()
    get_img_setting(d=1)

    app.run(host='0.0.0.0',port = 7040)    
    # socketio.run(app,host ='0.0.0.0', port=7020)
    #socketio.run(app, host='0.0.0.0', port=4000, debug=True)
    #serve(app, host='0.0.0.0', port=4000,threads =8)
     # This patches standard Python modules to be compatible with eventlet
    #init_db()
