# Import required libraries
import cv2  # OpenCV for computer vision
import mediapipe as mp  # MediaPipe for pose estimation
import math  # Math functions
import random  # Random number generation
import json  # JSON handling for data storage
import pygame  # Pygame for game interface
import threading  # Threading for parallel processing
import time  # Time functions
import pygame.mixer  # Pygame audio mixer
import os  # Operating system functions
from datetime import datetime, timedelta  # Date and time handling
import matplotlib.pyplot as plt  # For graph generation

# Game configuration
goal_squats = 20  # Target number of squats for progress

# Initialize Pygame
def setup_game():
    pygame.init()
    initialize_music()  # Set up background music

pygame.font.init()  # Initialize font system

# Avatar assets (simple shapes for visualization)
AVATAR_BASE = {
    "head": pygame.Rect(100, 100, 50, 50),  # Head (circle)
    "body": pygame.Rect(120, 150, 10, 50),  # Body (rectangle)
    "arms": pygame.Rect(100, 150, 50, 10),  # Arms (rectangle)
    "legs": pygame.Rect(120, 200, 10, 50),  # Legs (rectangle)
}

# Avatar customization items
AVATAR_ITEMS = {
    "hat": pygame.Rect(90, 80, 70, 20),  # Hat (rectangle)
    "glasses": pygame.Rect(110, 120, 30, 10),  # Glasses (rectangle)
    "shirt": pygame.Rect(100, 140, 50, 30),  # Shirt (rectangle)
    "shoes": pygame.Rect(110, 250, 30, 10),  # Shoes (rectangle)
}

# Screen dimensions
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Exercise Tracker Game")

# Color definitions
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GOLD = (255, 215, 0)

# Font settings
font = pygame.font.Font(None, 36)  # Main font
small_font = pygame.font.Font(None, 24)  # Secondary font

# Game state variables
running = True  # Main game loop control
webcam_active = False  # Webcam status
coin_x, coin_y = 0.5, 0.5  # Normalized coin coordinates (0-1)
coin_radius = 15  # Coin display size
coins_collected = 0  # Coin collection counter
squats_count = 0  # Squat counter
is_squatting = False  # Current squat state
was_squatting = False  # Previous squat state
exercise_type = None  # Current exercise mode
current_user = None  # Currently logged in user
last_exercise_date = None  # Last exercise date tracking
squat_state = "standing"  # Squat state machine
walking_bursts = 0  # Walking burst counter
walking_state = "Standing"  # Current walking state
last_walking_state = "Standing"  # Previous walking state
center_history = []  # Movement tracking history
still_counter = 0  # Stationary frame counter
background_music_playing = True  # Music playback state
music_file = "background_music.mp3"  # Music file path
sit_count = 0  # Chair sit counter
calibrated = False  # Posture calibration status
initial_leg_height = None  # Baseline leg position
is_sitting = False  # Current sitting state
was_sitting = False  # Previous sitting state
posture_status = "Calibrating..."  # Posture feedback message

# User data file path
USER_DATA_FILE = "user_data.json"

def load_user_data():
    """Load user data from JSON file with initialization checks"""
    try:
        with open(USER_DATA_FILE, "r") as file:
            data = json.load(file)
            # Ensure required fields exist for all users
            for user in data:
                if 'squats_history' not in data[user]:
                    data[user]['squats_history'] = {}
            return data
    except FileNotFoundError:
        return {}  # Return empty dict if file doesn't exist

def save_user_data(data):
    """Save user data to JSON file"""
    with open(USER_DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Load existing user data
user_data = load_user_data()

# Initialize MediaPipe pose estimation
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils  # For drawing pose landmarks

# Webcam capture object
cap = None

# Thread synchronization lock
data_lock = threading.Lock()

def calculate_angle(x1, y1, x2, y2, x3, y3):
    """Calculate angle between three points"""
    angle = math.degrees(math.atan2(y3 - y2, x3 - x2) - math.atan2(y1 - y2, x1 - x2))
    return abs(angle) if abs(angle) <= 180 else 360 - abs(angle)

def generate_edge_coin_position():
    """Generate random coin position on screen edges"""
    edge = random.choice(["left", "center", "right"])
    if edge == "left":
        return 0.05, 0.5  # Left edge
    elif edge == "center":
        return 0.5, 0.05  # Top center
    else:  # right edge
        return 0.95, 0.5  # Right edge

def get_current_edge(x, y):
    """Determine which screen edge a coin is on"""
    if abs(x - 0.5) < 0.1 and y <= 0.1:
        return "center"
    elif x <= 0.1:
        return "left"
    elif x >= 0.9:
        return "right"
    else:
        return "center"  # fallback

def get_text_input(prompt):
    """Display text input dialog and return user input"""
    global running
    input_text = ""
    input_active = True
    
    while input_active and running:
        # Draw input screen
        screen.fill(WHITE)
        prompt_surface = font.render(prompt, True, BLACK)
        screen.blit(prompt_surface, (50, 150))
        
        # Draw input box
        pygame.draw.rect(screen, BLACK, (50, 200, 700, 50), 2)
        text_surface = font.render(input_text, True, BLACK)
        screen.blit(text_surface, (60, 210))
        
        # Draw instructions
        instruction = small_font.render("Press ENTER to confirm", True, BLACK)
        screen.blit(instruction, (50, 270))
        
        pygame.display.flip()
        
        # Handle input events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    input_text += event.unicode
    
    return input_text

def select_existing_user():
    """Display user selection screen"""
    global current_user, running
    
    if not user_data:
        show_message("No existing users found. Please register first.")
        return False
    
    selected_index = 0
    users_list = list(user_data.keys())
    selecting = True
    
    while selecting and running:
        # Draw user selection screen
        screen.fill(WHITE)
        title = font.render("Select User", True, BLACK)
        screen.blit(title, (320, 50))
        
        # Draw user list
        for i, user in enumerate(users_list):
            color = BLUE if i == selected_index else BLACK
            user_text = font.render(f"{user} (Age: {user_data[user]['age']})", True, color)
            screen.blit(user_text, (150, 150 + i * 50))
        
        # Add Back option
        back_text = font.render("Back", True, BLUE if selected_index == len(users_list) else BLACK)
        screen.blit(back_text, (150, 150 + len(users_list) * 50))
        
        # Draw instructions
        instruction = small_font.render("UP/DOWN to navigate, ENTER to select, ESC to go back", True, BLACK)
        screen.blit(instruction, (250, 500))
        
        pygame.display.flip()
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_index = max(0, selected_index - 1)
                elif event.key == pygame.K_DOWN:
                    selected_index = min(len(users_list), selected_index + 1)
                elif event.key == pygame.K_RETURN:
                    if selected_index == len(users_list):  # Back option
                        selecting = False
                    else:
                        current_user = users_list[selected_index]
                        selecting = False
                elif event.key == pygame.K_ESCAPE:
                    selecting = False
    
    return True

def register_user():
    """Handle new user registration"""
    global current_user, running
    
    # Get user name
    user_name = get_text_input("Enter Name")
    if user_name is None:
        return False
    
    if not user_name:
        show_message("Name cannot be empty.")
        return False
    
    # Get user age
    user_age = get_text_input("Enter Age")
    if user_age is None:
        return False
    
    # Validate age
    try:
        age = int(user_age)
        if age <= 0:
            show_message("Age must be a positive number.")
            return False
    except ValueError:
        show_message("Age must be a number.")
        return False
    
    # Check for existing user or create new
    if user_name in user_data:
        show_message(f"User {user_name} already exists.")
        current_user = user_name
    else:
        # Initialize new user data
        user_data[user_name] = {
            "age": user_age,
            "coins": 0,
            "progress": 0,
            "squats_history": {},
            "walking_history": {},
            "last_exercise_date": None,
            "inventory": []
        }
        save_user_data(user_data)
        current_user = user_name
    
    return True

def show_message(message, duration=2000):
    """Display a temporary message on screen"""
    global running
    start_time = pygame.time.get_ticks()
    
    while pygame.time.get_ticks() - start_time < duration and running:
        screen.fill(WHITE)
        text_surface = font.render(message, True, BLACK)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
        screen.blit(text_surface, text_rect)
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return

def select_exercise():
    """Display exercise selection menu"""
    global exercise_type, running
    selecting = True
    selected_index = 0
    options = ["Hand Exercise", "Squatting", "Walking", "Chair Sit", "Back"]
    
    while selecting and running:
        # Draw exercise selection screen
        screen.fill(WHITE)
        title = font.render(f"Welcome, {current_user}! Select Exercise Type", True, BLACK)
        screen.blit(title, (200, 100))
        
        # Draw exercise options
        for i, option in enumerate(options):
            color = BLUE if i == selected_index else BLACK
            option_text = font.render(option, True, color)
            screen.blit(option_text, (320, 200 + i * 50))
        
        # Draw instructions
        instruction = small_font.render("UP/DOWN to navigate, ENTER to select", True, BLACK)
        screen.blit(instruction, (250, 500))
        
        pygame.display.flip()
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_index = max(0, selected_index - 1)
                elif event.key == pygame.K_DOWN:
                    selected_index = min(len(options) - 1, selected_index + 1)
                elif event.key == pygame.K_RETURN:
                    if options[selected_index] == "Back":
                        return False  # Return to main menu
                    else:
                        # Set exercise type based on selection
                        if selected_index == 0:
                            exercise_type = "hand"
                        elif selected_index == 1:
                            exercise_type = "squat"
                        elif selected_index == 2:
                            exercise_type = "walking"
                        elif selected_index == 3:
                            exercise_type = "chair_sit"
                        
                        selecting = False
                        return True  # Exercise selected
    
    return False

def view_avatar():
    """Display user's avatar with collected items"""
    global current_user, running
    
    if current_user is None:
        show_message("Please login first!")
        return
    
    viewing = True
    
    while viewing and running:
        # Draw avatar screen
        screen.fill(WHITE)
        title = font.render(f"{current_user}'s Avatar", True, BLACK)
        screen.blit(title, (320, 50))
        
        # Draw base avatar parts
        pygame.draw.ellipse(screen, BLACK, AVATAR_BASE["head"])  # Head
        pygame.draw.rect(screen, BLACK, AVATAR_BASE["body"])  # Body
        pygame.draw.rect(screen, BLACK, AVATAR_BASE["arms"])  # Arms
        pygame.draw.rect(screen, BLACK, AVATAR_BASE["legs"])  # Legs
        
        # Draw purchased items
        if 'inventory' in user_data[current_user]:
            for item in user_data[current_user]['inventory']:
                if item.lower() in AVATAR_ITEMS:
                    item_rect = AVATAR_ITEMS[item.lower()]
                    pygame.draw.rect(screen, BLUE, item_rect)
        
        # Draw instructions
        instruction = small_font.render("Press ESC to go back", True, BLACK)
        screen.blit(instruction, (320, 500))
        
        pygame.display.flip()
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    viewing = False

def marketplace():
    """Display marketplace for avatar items"""
    global user_data, current_user, running
    
    if current_user is None:
        show_message("Please login first!")
        return
    
    # Marketplace items
    items = [
        {"name": "Hat", "price": 50, "description": "A stylish hat for your avatar"},
        {"name": "Glasses", "price": 30, "description": "Cool glasses for your avatar"},
        {"name": "Shirt", "price": 70, "description": "A trendy shirt for your avatar"},
        {"name": "Shoes", "price": 40, "description": "Comfortable shoes for your avatar"},
        {"name": "Back", "price": 0, "description": "Return to the main menu"}
    ]
    
    selected_index = 0
    shopping = True
    
    while shopping and running:
        # Draw marketplace screen
        screen.fill(WHITE)
        title = font.render("Marketplace", True, BLACK)
        screen.blit(title, (320, 50))
        
        # Display user's coin balance
        coins_text = font.render(f"Your Coins: {user_data[current_user]['coins']}", True, BLUE)
        screen.blit(coins_text, (320, 100))
        
        # Draw item list
        for i, item in enumerate(items):
            color = GREEN if i == selected_index else BLACK
            item_text = font.render(f"{item['name']} - {item['price']} coins", True, color)
            screen.blit(item_text, (150, 180 + i * 70))
            
            desc_text = small_font.render(item['description'], True, BLACK)
            screen.blit(desc_text, (150, 210 + i * 70))
        
        # Draw instructions
        instruction1 = small_font.render("UP/DOWN to navigate", True, BLACK)
        instruction2 = small_font.render("ENTER to buy, ESC to exit", True, BLACK)
        screen.blit(instruction1, (320, 480))
        screen.blit(instruction2, (320, 510))
        
        pygame.display.flip()
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_index = max(0, selected_index - 1)
                elif event.key == pygame.K_DOWN:
                    selected_index = min(len(items) - 1, selected_index + 1)
                elif event.key == pygame.K_RETURN:
                    if items[selected_index]['name'] == "Back":
                        shopping = False
                    else:
                        # Handle item purchase
                        selected_item = items[selected_index]
                        if user_data[current_user]['coins'] >= selected_item['price']:
                            user_data[current_user]['coins'] -= selected_item['price']
                            if 'inventory' not in user_data[current_user]:
                                user_data[current_user]['inventory'] = []
                            user_data[current_user]['inventory'].append(selected_item['name'].lower())
                            save_user_data(user_data)
                            show_message(f"Purchased {selected_item['name']}!")
                        else:
                            show_message("Not enough coins!")
                elif event.key == pygame.K_ESCAPE:
                    shopping = False

# Data visualization functions
def generate_hand_exercise_graph():
    """Generate bar chart of hand exercise performance"""
    users = list(user_data.keys())
    coins = [user_data[user]['coins'] for user in users]
    
    plt.bar(users, coins, color='blue')
    plt.title("Hand Exercise Performance (Coins Collected)")
    plt.xlabel("Users")
    plt.ylabel("Coins Collected")
    plt.show()

def generate_squatting_graph():
    """Generate bar chart of squatting performance"""
    users = list(user_data.keys())
    squats = [sum(user_data[user].get('squats_history', {}).values()) for user in users]
    
    plt.bar(users, squats, color='green')
    plt.title("Squatting Performance (Total Squats)")
    plt.xlabel("Users")
    plt.ylabel("Total Squats")
    plt.show()

def generate_walking_graph():
    """Generate bar chart of walking performance"""
    users = list(user_data.keys())
    walking_data = []
    
    for user in users:
        total_bursts = sum(user_data[user].get('walking_history', {}).values())
        walking_data.append(total_bursts)
    
    plt.bar(users, walking_data, color='orange')
    plt.title("Walking Performance (Total Walking Bursts)")
    plt.xlabel("Users")
    plt.ylabel("Total Walking Bursts")
    plt.show()

def generate_chair_sit_graph():
    """Generate bar chart of chair sit performance"""
    users = list(user_data.keys())
    chair_sit_data = []
    
    for user in users:
        total_sits = sum(user_data[user].get('chair_sits_history', {}).values())
        chair_sit_data.append(total_sits)
    
    plt.bar(users, chair_sit_data, color='purple')
    plt.title("Chair Sit Performance (Total Chair Sits)")
    plt.xlabel("Users")
    plt.ylabel("Total Chair Sits")
    plt.show()

def delete_user():
    """Handle user deletion"""
    global user_data, running
    
    if not user_data:
        show_message("No users to delete.")
        return
    
    selected_index = 0
    users_list = list(user_data.keys())
    deleting = True
    
    while deleting and running:
        # Draw user deletion screen
        screen.fill(WHITE)
        title = font.render("Delete User", True, BLACK)
        screen.blit(title, (320, 50))
        
        # Draw user list
        for i, user in enumerate(users_list):
            color = RED if i == selected_index else BLACK
            user_text = font.render(f"{user} (Age: {user_data[user]['age']})", True, color)
            screen.blit(user_text, (150, 150 + i * 50))
        
        # Add Back option
        back_text = font.render("Back", True, RED if selected_index == len(users_list) else BLACK)
        screen.blit(back_text, (150, 150 + len(users_list) * 50))
        
        # Draw instructions
        instruction = small_font.render("UP/DOWN to navigate, ENTER to delete, ESC to cancel", True, BLACK)
        screen.blit(instruction, (200, 500))
        
        pygame.display.flip()
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_index = max(0, selected_index - 1)
                elif event.key == pygame.K_DOWN:
                    selected_index = min(len(users_list), selected_index + 1)
                elif event.key == pygame.K_RETURN:
                    if selected_index == len(users_list):  # Back option
                        deleting = False
                    else:
                        # Delete selected user
                        user_to_delete = users_list[selected_index]
                        del user_data[user_to_delete]
                        save_user_data(user_data)
                        show_message(f"User {user_to_delete} deleted.", 2000)
                        deleting = False
                elif event.key == pygame.K_ESCAPE:
                    deleting = False

def view_graphs():
    """Display graph selection menu"""
    global running
    
    if not user_data:
        show_message("No user data available to generate graphs.")
        return
    
    selecting = True
    selected_index = 0
    options = ["Hand Exercise Performance", "Squatting Performance", "Walking Performance", 
               "Chair Sit Performance", "Back"]
    
    while selecting and running:
        # Draw graph selection screen
        screen.fill(WHITE)
        title = font.render("View Graphs", True, BLUE)
        screen.blit(title, (320, 50))
        
        # Draw graph options
        for i, option in enumerate(options):
            color = BLUE if i == selected_index else BLACK
            option_text = font.render(option, True, color)
            screen.blit(option_text, (280, 150 + i * 50))
        
        # Draw instructions
        instruction = small_font.render("UP/DOWN to navigate, ENTER to select", True, BLACK)
        screen.blit(instruction, (250, 400))
        
        pygame.display.flip()
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_index = max(0, selected_index - 1)
                elif event.key == pygame.K_DOWN:
                    selected_index = min(len(options) - 1, selected_index + 1)
                elif event.key == pygame.K_RETURN:
                    if options[selected_index] == "Hand Exercise Performance":
                        generate_hand_exercise_graph()
                    elif options[selected_index] == "Squatting Performance":
                        generate_squatting_graph()
                    elif options[selected_index] == "Walking Performance":
                        generate_walking_graph()
                    elif options[selected_index] == "Chair Sit Performance":
                        generate_chair_sit_graph()
                    elif options[selected_index] == "Back":
                        selecting = False

def main_menu():
    """Display main menu and handle navigation"""
    global current_user, running
    
    menu_active = True
    selected_index = 0
    options = ["New User", "Existing User", "Marketplace", "View Graphs", "View Avatar", "Delete User", "Quit"]
    
    while menu_active and running:
        # Draw main menu
        screen.fill(WHITE)
        title = font.render("Exercise Tracker Game", True, BLUE)
        screen.blit(title, (280, 50))
        
        # Display current user if logged in
        if current_user:
            user_text = font.render(f"Current User: {current_user}", True, GREEN)
            screen.blit(user_text, (280, 100))
        
        # Draw menu options
        for i, option in enumerate(options):
            color = BLUE if i == selected_index else BLACK
            option_text = font.render(option, True, color)
            screen.blit(option_text, (350, 200 + i * 50))
        
        # Draw music control button
        draw_music_button(screen)
        
        pygame.display.flip()
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_index = max(0, selected_index - 1)
                elif event.key == pygame.K_DOWN:
                    selected_index = min(len(options) - 1, selected_index + 1)
                elif event.key == pygame.K_RETURN:
                    if options[selected_index] == "New User":
                        if register_user():
                            menu_active = False
                    elif options[selected_index] == "Existing User":
                        if select_existing_user():
                            menu_active = False
                    elif options[selected_index] == "Marketplace":
                        marketplace()
                    elif options[selected_index] == "View Graphs":
                        view_graphs()
                    elif options[selected_index] == "View Avatar":
                        view_avatar()
                    elif options[selected_index] == "Delete User":
                        delete_user()
                    elif options[selected_index] == "Quit":
                        running = False
                        return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Handle music button click
                if is_music_button_clicked(event.pos):
                    toggle_music()
    
    return True

# Exercise game functions
def chair_sit_exercise_game():
    """Chair sit exercise game logic"""
    global user_data, current_user, running, webcam_active
    
    # Initialize variables
    with data_lock:
        sit_count = 0
        coins_earned = 0
        posture_status = "Calibrating..."
        calibrated = False
        initial_leg_height = None
        is_sitting = False
        was_sitting = False
        
        # Set current date
        today = datetime.now().strftime("%Y-%m-%d")
        user_data[current_user]['last_exercise_date'] = today
        
        # Initialize chair sits history
        if 'chair_sits_history' not in user_data[current_user]:
            user_data[current_user]['chair_sits_history'] = {}
        
        if today not in user_data[current_user]['chair_sits_history']:
            user_data[current_user]['chair_sits_history'][today] = 0
        
        save_user_data(user_data)
    
    # Start webcam
    webcam_active = True
    start_webcam()
    
    # Ready countdown
    countdown_start = 5
    countdown_font = pygame.font.Font(None, 200)
    
    for countdown in range(countdown_start, 0, -1):
        screen.fill(WHITE)
        countdown_text = countdown_font.render(str(countdown), True, RED)
        countdown_rect = countdown_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(countdown_text, countdown_rect)
        
        ready_instruction = font.render("Get Ready for Chair Sits!", True, BLACK)
        instruction_rect = ready_instruction.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 200))
        screen.blit(ready_instruction, instruction_rect)
        
        pygame.display.flip()
        pygame.time.delay(1000)
    
    # Main game loop
    game_running = True
    start_time = pygame.time.get_ticks()
    game_duration = 60000  # 1 minute
    
    while game_running and running and webcam_active:
        current_time = pygame.time.get_ticks()
        time_left = max(0, game_duration - (current_time - start_time))
        
        # Draw game UI
        screen.fill(WHITE)
        
        # Display stats
        sit_text = font.render(f"Chair Sits: {sit_count}", True, BLACK)
        screen.blit(sit_text, (50, 150))
        
        coins_text = font.render(f"Coins Earned: {coins_earned}", True, GOLD)
        screen.blit(coins_text, (50, 200))
        
        status_text = font.render(f"Status: {posture_status}", True, BLACK)
        screen.blit(status_text, (50, 250))
        
        time_text = font.render(f"Time Left: {time_left // 1000}s", True, BLACK)
        screen.blit(time_text, (650, 50))
        
        # Draw progress bar
        progress_width = int((time_left / game_duration) * 500)
        pygame.draw.rect(screen, BLACK, (150, 450, 500, 20), 2)
        pygame.draw.rect(screen, (0, 180, 255), (150, 450, 500 - progress_width, 20))
        
        # Draw instructions
        instruction = small_font.render("Sit down and stand up to register chair sits. Press ESC to exit.", True, BLACK)
        screen.blit(instruction, (150, 520))
        
        pygame.display.flip()
        
        # Check game end condition
        if time_left <= 0:
            game_running = False
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                game_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_running = False
    
    # Clean up
    webcam_active = False
    stop_webcam()
    
    # Update user data
    with data_lock:
        coins_earned = sit_count * 5
        user_data[current_user]['coins'] += coins_earned
        user_data[current_user]['chair_sits_history'][today] = sit_count
        save_user_data(user_data)
    
    # Show results
    show_message(f"Exercise Complete! You did {sit_count} chair sits and earned {coins_earned} coins.", 3000)

def hand_exercise_game():
    """Hand exercise game logic"""
    global coin_x, coin_y, coins_collected, user_data, current_user, running, webcam_active
    
    # Initialize coin position
    coin_x, coin_y = generate_edge_coin_position()
    
    # Initialize variables
    with data_lock:
        coins_collected = 0
        user_data[current_user]['last_exercise_date'] = datetime.now().strftime("%Y-%m-%d")
        save_user_data(user_data)
    
    # Start webcam
    webcam_active = True
    start_webcam()
    
    # Main game loop
    game_running = True
    start_time = pygame.time.get_ticks()
    game_duration = 120000  # 2 minutes
    current_edge = get_current_edge(coin_x, coin_y)
    
    while game_running and running and webcam_active:
        current_time = pygame.time.get_ticks()
        time_left = max(0, game_duration - (current_time - start_time))
        
        # Draw game UI
        screen.fill(WHITE)
        
        # Display timer
        time_text = font.render(f"Time: {time_left // 1000}s", True, BLACK)
        screen.blit(time_text, (650, 50))
        
        # Display coins collected
        coins_text = font.render(f"Coins: {coins_collected}/15", True, BLACK)
        screen.blit(coins_text, (50, 50))
        
        # Display instructions
        instruction = small_font.render(f"Stretch {current_edge.upper()} to collect the coin", True, BLACK)
        screen.blit(instruction, (250, 520))
        
        pygame.display.flip()
        
        # Check game end conditions
        if time_left <= 0 or coins_collected >= 15:
            game_running = False
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                game_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_running = False
    
    # Clean up
    webcam_active = False
    stop_webcam()
    
    # Update user data
    with data_lock:
        user_data[current_user]['coins'] += coins_collected
        save_user_data(user_data)
    
    # Show results
    show_message(f"Exercise Complete! You collected {coins_collected} coins.", 3000)

def squat_exercise_game():
    """Squat exercise game logic"""
    global squats_count, is_squatting, was_squatting, user_data, current_user, running, webcam_active
    
    # Initialize variables
    with data_lock:
        squats_count = 0
        is_squatting = False
        was_squatting = False
        squat_state = "standing"
        
        # Reset progress
        user_data[current_user]['progress'] = 0
        save_user_data(user_data)
        
        # Check for missed days and apply penalty
        today = datetime.now().strftime("%Y-%m-%d")
        last_date = user_data[current_user].get('last_exercise_date')
        
        if last_date:
            last_date = datetime.strptime(last_date, "%Y-%m-%d")
            today_date = datetime.strptime(today, "%Y-%m-%d")
            days_missed = (today_date - last_date).days - 1
            
            if days_missed > 0:
                reduction = min(100, 10 * days_missed)
                user_data[current_user]['progress'] = max(0, user_data[current_user]['progress'] - reduction)
                show_message(f"You missed {days_missed} days. Progress reduced by {reduction}%", 3000)
        
        user_data[current_user]['last_exercise_date'] = today
        
        # Initialize squats history
        if 'squats_history' not in user_data[current_user]:
            user_data[current_user]['squats_history'] = {}
        
        if today not in user_data[current_user]['squats_history']:
            user_data[current_user]['squats_history'][today] = 0
        
        save_user_data(user_data)
    
    # Start webcam
    webcam_active = True
    start_webcam()
    
    # Ready countdown
    countdown_start = 5
    countdown_font = pygame.font.Font(None, 200)
    
    for countdown in range(countdown_start, 0, -1):
        screen.fill(WHITE)
        countdown_text = countdown_font.render(str(countdown), True, RED)
        countdown_rect = countdown_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(countdown_text, countdown_rect)
        
        ready_instruction = font.render("Get Ready for Squats!", True, BLACK)
        instruction_rect = ready_instruction.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 200))
        screen.blit(ready_instruction, instruction_rect)
        
        pygame.display.flip()
        pygame.time.delay(1000)
    
    # Main game loop
    game_running = True
    start_time = pygame.time.get_ticks()
    game_duration = 120000  # 2 minutes
    
    while game_running and running and webcam_active:
        current_time = pygame.time.get_ticks()
        time_left = max(0, game_duration - (current_time - start_time))
        
        # Draw game UI
        screen.fill(WHITE)
        
        # Display stats
        squats_text = font.render(f"Squats: {squats_count}", True, BLACK)
        screen.blit(squats_text, (50, 480))
        
        time_text = font.render(f"Time: {time_left // 1000}s", True, BLACK)
        screen.blit(time_text, (650, 480))
        
        # Draw progress bar
        progress = user_data[current_user]['progress']
        pygame.draw.rect(screen, BLACK, (200, 480, 300, 30), 2)
        pygame.draw.rect(screen, GREEN, (200, 480, int(3 * progress), 30))
        progress_text = small_font.render(f"Progress: {progress}%", True, BLACK)
        screen.blit(progress_text, (320, 485))
        
        # Draw instructions
        instruction = small_font.render("Do squats to increase progress. Press ESC to exit.", True, BLACK)
        screen.blit(instruction, (250, 520))
        
        # Display squat status
        squat_status = font.render("Squatting" if is_squatting else "Stand Straight", True, RED if is_squatting else BLACK)
        screen.blit(squat_status, (350, 450))
        
        pygame.display.flip()
        
        # Check game end condition
        if time_left <= 0:
            game_running = False
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                game_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_running = False
    
    # Clean up
    webcam_active = False
    stop_webcam()
    
    # Update user data
    with data_lock:
        user_data[current_user]['squats_history'][today] = squats_count
        
        # Calculate progress and coins
        progress_increase = min(100 - user_data[current_user]['progress'], 
                                min(squats_count, goal_squats) * 100 / goal_squats)
        user_data[current_user]['progress'] += progress_increase
        
        coins_earned = min(squats_count, goal_squats) * 5
        user_data[current_user]['coins'] += coins_earned
        
        save_user_data(user_data)
    
    # Show results
    show_message(f"Exercise Complete! You did {squats_count} squats and earned {coins_earned} coins.", 3000)

def walking_exercise_game():
    """Walking exercise game logic"""
    global walking_bursts, walking_state, last_walking_state, center_history, still_counter
    global user_data, current_user, running, webcam_active
    
    # Movement detection constants
    CENTER_MOVE_THRESHOLD = 20
    SMOOTH_FRAMES = 5
    STILL_FRAMES_THRESHOLD = 10
    
    # Initialize variables
    with data_lock:
        walking_bursts = 0
        walking_state = "Standing"
        last_walking_state = "Standing"
        center_history = []
        still_counter = 0
        
        # Set current date
        today = datetime.now().strftime("%Y-%m-%d")
        user_data[current_user]['last_exercise_date'] = today
        save_user_data(user_data)
    
    # Start webcam
    webcam_active = True
    start_webcam()
    
    # Ready countdown
    countdown_start = 5
    countdown_font = pygame.font.Font(None, 200)
    
    for countdown in range(countdown_start, 0, -1):
        screen.fill(WHITE)
        countdown_text = countdown_font.render(str(countdown), True, RED)
        countdown_rect = countdown_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        screen.blit(countdown_text, countdown_rect)
        
        ready_instruction = font.render("Get Ready for Walking!", True, BLACK)
        instruction_rect = ready_instruction.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 200))
        screen.blit(ready_instruction, instruction_rect)
        
        pygame.display.flip()
        pygame.time.delay(1000)
    
    # Main game loop
    game_running = True
    start_time = pygame.time.get_ticks()
    game_duration = 60000  # 1 minute
    
    while game_running and running and webcam_active:
        current_time = pygame.time.get_ticks()
        time_left = max(0, game_duration - (current_time - start_time))
        
        # Draw game UI
        screen.fill(WHITE)
        
        # Display stats
        status_text = font.render(f"Status: {walking_state}", True, GREEN if walking_state == "Walking" else BLACK)
        screen.blit(status_text, (50, 150))
        
        bursts_text = font.render(f"Walking Bursts: {walking_bursts}", True, BLUE)
        screen.blit(bursts_text, (50, 200))
        
        time_text = font.render(f"Time Left: {time_left // 1000}s", True, BLACK)
        screen.blit(time_text, (650, 50))
        
        # Draw progress bar
        progress_width = int((time_left / game_duration) * 500)
        pygame.draw.rect(screen, BLACK, (150, 450, 500, 20), 2)
        pygame.draw.rect(screen, (0, 180, 255), (150, 450, 500 - progress_width, 20))
        
        # Draw instructions
        instruction = small_font.render("Walk in place to register walking bursts. Press ESC to exit.", True, BLACK)
        screen.blit(instruction, (200, 520))
        
        pygame.display.flip()
        
        # Check game end condition
        if time_left <= 0:
            game_running = False
        
        # Handle input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                game_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_running = False
    
    # Clean up
    webcam_active = False
    stop_webcam()
    
    # Update user data
    with data_lock:
        coins_earned = walking_bursts * 10
        user_data[current_user]['coins'] += coins_earned
        
        # Initialize walking history if needed
        if 'walking_history' not in user_data[current_user]:
            user_data[current_user]['walking_history'] = {}
        
        today = datetime.now().strftime("%Y-%m-%d")
        user_data[current_user]['walking_history'][today] = walking_bursts
        
        save_user_data(user_data)
    
    # Show results
    show_message(f"Exercise Complete! You achieved {walking_bursts} walking bursts and earned {coins_earned} coins.", 3000)

# Webcam functions
def start_webcam():
    """Initialize and start webcam capture"""
    global cap
    cap = cv2.VideoCapture(0)
    
    # Start webcam processing thread
    webcam_thread = threading.Thread(target=process_webcam, daemon=True)
    webcam_thread.start()

def stop_webcam():
    """Release webcam resources"""
    global cap
    if cap is not None:
        cap.release()
        cv2.destroyAllWindows()

def process_webcam():
    """Process webcam frames for exercise detection"""
    global cap, coin_x, coin_y, coins_collected, squats_count, is_squatting, was_squatting, running, squat_state, calibrated, sit_count, initial_leg_height, is_sitting, was_sitting, posture_status, still_counter, walking_bursts, walking_state, last_walking_state, center_history
    
    # Track coins by edge
    coins_by_edge = {
        "center": 0,
        "left": 0,
        "right": 0
    }
    
    while webcam_active and cap.isOpened() and running:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.flip(frame, 1)  # Mirror the frame
        frame_height, frame_width, _ = frame.shape
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = pose.process(rgb_frame)
        
        if results.pose_landmarks:
            # Draw pose landmarks
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            # Get landmarks
            landmarks = results.pose_landmarks.landmark
            
            with data_lock:
                if exercise_type == "hand":
                    # Hand exercise logic
                    # Draw coin
                    cv2.circle(frame, 
                               (int(coin_x * frame_width), int(coin_y * frame_height)), 
                               20, GOLD, -1)
                    
                    # Get relevant landmarks
                    left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
                    right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
                    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
                    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
                    
                    # Convert to pixel coordinates
                    left_wrist_x = left_wrist.x
                    left_wrist_y = left_wrist.y
                    right_wrist_x = right_wrist.x
                    right_wrist_y = right_wrist.y
                    
                    # Determine current edge
                    current_edge = get_current_edge(coin_x, coin_y)
                    
                    # Calculate pixel positions
                    coin_pixel_x = int(coin_x * frame_width)
                    coin_pixel_y = int(coin_y * frame_height)
                    
                    left_wrist_pixel_x = int(left_wrist_x * frame_width)
                    left_wrist_pixel_y = int(left_wrist_y * frame_height)
                    right_wrist_pixel_x = int(right_wrist_x * frame_width)
                    right_wrist_pixel_y = int(right_wrist_y * frame_height)
                    
                    # Detection thresholds
                    proximity_threshold = 100
                    angle_threshold = 30
                    
                    # Arm angle calculation
                    def calculate_arm_angle(shoulder_x, shoulder_y, wrist_x, wrist_y):
                        return math.degrees(math.atan2(wrist_y - shoulder_y, wrist_x - shoulder_x))
                    
                    # Calculate arm angles
                    left_arm_angle = calculate_arm_angle(
                        left_shoulder.x * frame_width, 
                        left_shoulder.y * frame_height, 
                        left_wrist_pixel_x, 
                        left_wrist_pixel_y
                    )
                    
                    right_arm_angle = calculate_arm_angle(
                        right_shoulder.x * frame_width, 
                        right_shoulder.y * frame_height, 
                        right_wrist_pixel_x, 
                        right_wrist_pixel_y
                    )
                    
                    # Calculate distances to coin
                    left_hand_distance = math.hypot(
                        left_wrist_pixel_x - coin_pixel_x, 
                        left_wrist_pixel_y - coin_pixel_y
                    )
                    
                    right_hand_distance = math.hypot(
                        right_wrist_pixel_x - coin_pixel_x, 
                        right_wrist_pixel_y - coin_pixel_y
                    )
                    
                    # Edge-specific collection logic
                    collected = False
                    
                    if current_edge == "center":
                        # Center coin - stretch up
                        left_stretched_up = (
                            left_hand_distance < proximity_threshold and
                            abs(left_arm_angle) > 70 and abs(left_arm_angle) < 110
                        )
                        right_stretched_up = (
                            right_hand_distance < proximity_threshold and
                            abs(right_arm_angle) > 70 and abs(right_arm_angle) < 110
                        )
                        
                        collected = left_stretched_up or right_stretched_up
                    
                    elif current_edge == "left":
                        # Left coin - right hand stretched left
                        right_stretched_left = (
                            right_hand_distance < proximity_threshold and
                            right_arm_angle > 160 or right_arm_angle < -160
                        )
                        
                        collected = right_stretched_left
                    
                    elif current_edge == "right":
                        # Right coin - left hand stretched right
                        left_stretched_right = (
                            left_hand_distance < proximity_threshold and
                            abs(left_arm_angle) < 20 or abs(left_arm_angle) > 340
                        )
                        
                        collected = left_stretched_right
                    
                    if collected:
                        coins_collected += 1
                        cv2.circle(frame, (coin_pixel_x, coin_pixel_y), 30, (0, 255, 0), -1)
                        coin_x, coin_y = generate_edge_coin_position()
                        current_edge = get_current_edge(coin_x, coin_y)
                
                elif exercise_type == "squat":
                    # Squat detection logic
                    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
                    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
                    left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
                    right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
                    left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]
                    right_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]
                    
                    # Calculate knee angles
                    left_knee_angle = calculate_angle(
                        left_hip.x, left_hip.y,
                        left_knee.x, left_knee.y,
                        left_ankle.x, left_ankle.y
                    )
                    
                    right_knee_angle = calculate_angle(
                        right_hip.x, right_hip.y,
                        right_knee.x, right_knee.y,
                        right_ankle.x, right_ankle.y
                    )
                    
                    # Determine squat state
                    is_squatting = left_knee_angle < 120 and right_knee_angle < 120
                    
                    # State machine for counting squats
                    if squat_state == "standing" and is_squatting:
                        squat_state = "squatting"
                    elif squat_state == "squatting" and not is_squatting:
                        squat_state = "standing"
                        squats_count += 1
                        
                        # Update progress
                        progress = min(100, (squats_count / goal_squats) * 100)
                        user_data[current_user]['progress'] = progress
                        save_user_data(user_data)
                
                elif exercise_type == "walking":
                    # Walking detection logic
                    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
                    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
                    
                    if left_hip.visibility > 0.5 and right_hip.visibility > 0.5:
                        # Calculate center point
                        center_x = int(((left_hip.x + right_hip.x) / 2) * frame_width)
                        center_history.append(center_x)
                        
                        # Maintain history buffer
                        if len(center_history) > 5:
                            center_history.pop(0)
                        
                        if len(center_history) > 1:
                            # Calculate movement
                            movement = max(center_history) - min(center_history)
                            
                            if movement > 20:
                                walking_state = "Walking"
                                still_counter = 0
                                if last_walking_state == "Standing":
                                    walking_bursts += 1
                            else:
                                still_counter += 1
                                if still_counter > 10:
                                    walking_state = "Standing"
                            
                            last_walking_state = walking_state
                
                elif exercise_type == "chair_sit":
                    # Chair sit detection logic
                    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
                    left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
                    
                    if left_hip.visibility > 0.5 and left_knee.visibility > 0.5:
                        current_leg_height = abs(left_hip.y - left_knee.y)
                        
                        if not calibrated:
                            # Initial calibration
                            initial_leg_height = current_leg_height
                            calibrated = True
                            posture_status = "Calibrated"
                        else:
                            # Detect sitting position
                            if current_leg_height < initial_leg_height * 0.8:
                                is_sitting = True
                                posture_status = "Sitting"
                            else:
                                is_sitting = False
                                posture_status = "Standing"
                            
                            # Count sit transitions
                            if is_sitting and not was_sitting:
                                sit_count += 1
                                cv2.putText(frame, "Sit Detected!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 
                                            2, (0, 255, 0), 3)
                            
                            was_sitting = is_sitting
        
        # Display frame
        cv2.imshow("Exercise Tracker", frame)
        
        # Exit on 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Clean up
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()

# Audio functions
def initialize_music():
    """Initialize background music"""
    global background_music_playing
    
    try:
        pygame.mixer.init()
        if os.path.exists(music_file):
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
            background_music_playing = True
        else:
            print(f"Warning: Music file '{music_file}' not found.")
            background_music_playing = False
    except Exception as e:
        print(f"Error initializing music: {e}")
        background_music_playing = False

def toggle_music():
    """Toggle music playback state"""
    global background_music_playing
    
    if pygame.mixer.get_init():
        if background_music_playing:
            pygame.mixer.music.pause()
            background_music_playing = False
        else:
            pygame.mixer.music.unpause()
            background_music_playing = True

def draw_music_button(screen):
    """Draw music control button"""
    icon_color = GREEN if background_music_playing else RED
    pygame.draw.rect(screen, BLACK, (SCREEN_WIDTH - 50, 10, 40, 40), 2)
    
    if background_music_playing:
        # Speaker icon
        pygame.draw.polygon(screen, icon_color, [(SCREEN_WIDTH - 40, 20), (SCREEN_WIDTH - 40, 40), (SCREEN_WIDTH - 30, 40), (SCREEN_WIDTH - 20, 50), (SCREEN_WIDTH - 20, 10), (SCREEN_WIDTH - 30, 20)])
        # Sound waves
        pygame.draw.arc(screen, icon_color, (SCREEN_WIDTH - 25, 15, 10, 30), -0.5, 0.5, 2)
    else:
        # Muted speaker
        pygame.draw.polygon(screen, icon_color, [(SCREEN_WIDTH - 40, 20), (SCREEN_WIDTH - 40, 40), (SCREEN_WIDTH - 30, 40), (SCREEN_WIDTH - 20, 50), (SCREEN_WIDTH - 20, 10), (SCREEN_WIDTH - 30, 20)])
        # X mark
        pygame.draw.line(screen, RED, (SCREEN_WIDTH - 45, 15), (SCREEN_WIDTH - 15, 45), 2)
    
    music_text = small_font.render("Music", True, BLACK)
    screen.blit(music_text, (SCREEN_WIDTH - 45, 55))

def is_music_button_clicked(pos):
    """Check if music button was clicked"""
    return (SCREEN_WIDTH - 50 <= pos[0] <= SCREEN_WIDTH - 10 and 
            10 <= pos[1] <= 50)

# Main game function
def main():
    """Main game loop"""
    setup_game()
    global running, exercise_type

    while running:
        # Show main menu
        if not main_menu():
            break
        
        # Select exercise
        if not select_exercise():
            break
        
        # Run selected exercise
        if exercise_type == "hand":
            hand_exercise_game()
        elif exercise_type == "squat":
            squat_exercise_game()
        elif exercise_type == "walking":
            walking_exercise_game()
        elif exercise_type == "chair_sit":
            chair_sit_exercise_game()
    
    # Clean up
    stop_webcam()
    pygame.mixer.quit()
    pygame.quit()

# Entry point
if __name__ == "__main__":
    main()
