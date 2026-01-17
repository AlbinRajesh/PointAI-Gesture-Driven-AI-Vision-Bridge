import cv2
import mediapipe as mp
import pyautogui
import mss
import mss.tools
import ctypes
import tkinter as tk
import keyboard
import time
import sys
import threading
import os
from google import genai # Change the import
import PIL.Image
import PIL.Image

# --- STEP 1: AI CONFIGURATION ---
client = genai.Client(api_key="AIzaSyBcRTBb3IqkSooLBZQPNJi0mjQDm0DVyhI")
MODEL_ID = "gemini-2.5-flash"

# Global variables for the HUD
current_ai_message = ""
lock_start_timestamp = None

def ask_ai_about_image(filename):
    global current_ai_message
    current_ai_message = ">>> ANALYZING DATA..."
    try:
        img = PIL.Image.open(filename)
        prompt = "Provide a tactical summary of this image in 10 words or less."
        
        # New syntax for sending images
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[prompt, img]
        )
        
        current_ai_message = f"INTEL: {response.text.strip().upper()}"
    except Exception as e:
        current_ai_message = ">>> AI OFFLINE / ERROR"
        print(f"AI Error: {e}")

# --- STEP 2: DPI ACCURACY ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# --- STEP 3: OVERLAY UI ---
class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True, "-transparentcolor", "white")
        self.root.config(bg='white')
        self.root.wm_attributes("-disabled", True)
        
        self.canvas = tk.Canvas(self.root, width=self.root.winfo_screenwidth(), 
                               height=self.root.winfo_screenheight(), 
                               bg='white', highlightthickness=0)
        self.canvas.pack()
        
        # UI Elements
        self.rect = self.canvas.create_rectangle(0, 0, 0, 0, outline="green", width=3)
        self.label = self.canvas.create_text(0, 0, text="", fill="green", font=("Arial", 12, "bold"), anchor="sw")
        self.ai_label = self.canvas.create_text(0, 0, text="", fill="cyan", font=("Courier New", 12, "bold"), anchor="nw", width=400)
        self.timer_label = self.canvas.create_text(0, 0, text="", fill="red", font=("Arial", 10, "bold"), anchor="se")

    def update_box(self, x1, y1, x2, y2, state="moving", countdown="", ai_info="", timer_str="", flash_now=False):
        try:
            # Update Box
            self.canvas.coords(self.rect, x1, y1, x2, y2)
            
            # Update Top Label (Locking in... / Locked)
            self.canvas.coords(self.label, x1, y1 - 5)
            self.canvas.itemconfig(self.label, text=countdown)
            
            # Update Bottom HUD (AI Intel)
            self.canvas.coords(self.ai_label, x1, y2 + 5)
            self.canvas.itemconfig(self.ai_label, text=ai_info)
            
            # Update Timer (Inside the box, bottom right)
            if timer_str:
                self.canvas.coords(self.timer_label, x2 - 5, y2 - 5)
                self.canvas.itemconfig(self.timer_label, text=timer_str)
            else:
                self.canvas.itemconfig(self.timer_label, text="")

            # Visual Flash and Colors
            self.canvas.itemconfig(self.rect, fill="white" if flash_now else "")
            color = "red" if state == "locked" else "orange" if state == "closing" else "green"
            self.canvas.itemconfig(self.rect, outline=color)
            self.canvas.itemconfig(self.label, fill=color)
            
            self.root.update()
        except: pass

    def close(self):
        try: self.root.destroy()
        except: pass

overlay = Overlay()
sct = mss.mss()
main_monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]

# --- STEP 4: COORDINATES & FLAGS ---
current_box = [0, 0, 0, 0] 
is_running = True 
is_locked = False
last_move_time = time.time()
fist_start_time = None
lock_threshold, lock_delay = 20, 3.0

def reset_lock():
    global is_locked, last_move_time, current_ai_message, lock_start_timestamp
    is_locked = False
    lock_start_timestamp = None
    current_ai_message = ""
    last_move_time = time.time()
    print("Resetting HUD...")

keyboard.add_hotkey('r', reset_lock)
keyboard.add_hotkey('q', lambda: globals().update(is_running=False))

# --- STEP 5: VISION BRAIN ---
screen_w, screen_h = pyautogui.size()
video = cv2.VideoCapture(0)
hands_detector = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.8)

p_t_x, p_t_y, p_i_x, p_i_y = 0, 0, 0, 0
smooth_factor = 0.15

print("AR AI Sniper HUD: ACTIVE")

try:
    while is_running:
        success, img = video.read()
        if not success: break
        
        img = cv2.flip(img, 1)
        result = hands_detector.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        display_text, current_state, flash_effect, timer_display = "", "moving", False, ""

        if is_locked:
            current_state = "locked"
            display_text = "SURVEILLANCE ACTIVE"
            # Calculate Timer
            if lock_start_timestamp:
                elapsed = time.time() - lock_start_timestamp
                timer_display = f"{int(elapsed)}s"
        else:
            if result.multi_hand_landmarks:
                hand_lms = result.multi_hand_landmarks[0]
                is_fist = all([hand_lms.landmark[i].y > hand_lms.landmark[i-2].y for i in [8, 12, 16, 20]])

                if is_fist:
                    fist_start_time = fist_start_time or time.time()
                    if time.time() - fist_start_time > 2.0: is_running = False
                    display_text, current_state = "EXITING...", "closing"
                else:
                    fist_start_time = None 
                    tx, ty = hand_lms.landmark[4].x * screen_w, hand_lms.landmark[4].y * screen_h
                    ix, iy = hand_lms.landmark[8].x * screen_w, hand_lms.landmark[8].y * screen_h

                    if abs(tx - p_t_x) + abs(ty - p_t_y) > lock_threshold:
                        last_move_time = time.time()
                    else:
                        if time.time() - last_move_time > lock_delay:
                            is_locked, flash_effect = True, True
                            lock_start_timestamp = time.time() # Start the timer
                            x1, y1, x2, y2 = current_box
                            region = {"top": int(y1), "left": int(x1), "width": int(x2-x1), "height": int(y2-y1)}
                            filename = f"ai_cap_{int(time.time())}.png"
                            mss.tools.to_png(sct.grab(region).rgb, sct.grab(region).size, output=filename)
                            threading.Thread(target=ask_ai_about_image, args=(filename,), daemon=True).start()
                        else:
                            display_text = f"LOCKING IN {max(0, int(lock_delay - (time.time() - last_move_time)) + 1)}s"

                    p_t_x += (tx - p_t_x) * smooth_factor
                    p_t_y += (ty - p_t_y) * smooth_factor
                    p_i_x += (ix - p_i_x) * smooth_factor
                    p_i_y += (iy - p_i_y) * smooth_factor
                    current_box = [int(min(p_t_x, p_i_x)), int(min(p_t_y, p_i_y)), int(max(p_t_x, p_i_x)), int(max(p_t_y, p_i_y))]

        overlay.update_box(*current_box, state=current_state, countdown=display_text, 
                           ai_info=current_ai_message, timer_str=timer_display, flash_now=flash_effect)
        time.sleep(0.01)

finally:
    video.release()
    overlay.close()
    keyboard.unhook_all()
    sys.exit()