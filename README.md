FITQUEST – Interactive Fitness Tracker
===================================

FITQUEST is a fun and interactive fitness game that turns your webcam into a workout tracker.
Using AI pose detection and gamification, FITQUEST encourages users to complete real physical
exercises while earning rewards and customizing their avatars.

-----------------------------------
🎮 Key Features:
-----------------------------------
- Tracks 4 core exercises:
  • Hand Stretch
  • Squats
  • Walking in Place
  • Chair Sit
- Real-time feedback using webcam and AI (MediaPipe)
- Earn coins as rewards for exercising
- Customize your avatar with hats, shirts, glasses, shoes
- View performance analytics using graphs
- Support for multiple users with personal progress saved
- Background music and interactive game interface using Pygame

-----------------------------------
🧰 Technologies Used:
-----------------------------------
- Python 3.9 or 3.10 (recommended for full compatibility)
- MediaPipe – for pose detection
- OpenCV – for webcam and image processing
- Pygame – for game UI and music
- Matplotlib – for drawing progress charts

-----------------------------------
🚀 Getting Started:
-----------------------------------
1. Clone the repository:
   git clone https://github.com/yourusername/FITQUEST.git
   cd FITQUEST

2. (Optional) Create a virtual environment:
   python -m venv venv
   venv\Scripts\activate    (on Windows)
   source venv/bin/activate (on Mac/Linux)

3. Install dependencies:
   pip install -r requirements.txt

4. Run the game:
   python FITQUEST.py

-----------------------------------
📦 Requirements.txt content:
-----------------------------------
opencv-python
mediapipe
pygame
matplotlib

-----------------------------------
📝 Notes:
-----------------------------------
- Make sure your webcam is working and allowed.
- Place a file named 'background_music.mp3' in the main folder to enable music.
- All progress and user data is stored in 'user_data.json'.
- Run the game in a well-lit room for best pose detection results.

-----------------------------------
📊 Graphs Available:
-----------------------------------
Inside the game, you can view charts for:
- Hand exercise coins collected
- Squats done over time
- Walking bursts detected
- Chair sits tracked

-----------------------------------
🎨 Avatar Customization:
-----------------------------------
You can spend your earned coins to unlock and equip:
- 👒 Hats
- 👓 Glasses
- 👕 Shirts
- 👟 Shoes

Go to the Marketplace to buy items, and View Avatar to see your character!

-----------------------------------
👩‍💻 About the Creator:
-----------------------------------
Parinita Garg  
Final Year BTech CSE student  
Passionate about consulting, design, and real-world impactful tech.

-----------------------------------
📜 License:
-----------------------------------
MIT License  
Feel free to use, improve, and share this project.
