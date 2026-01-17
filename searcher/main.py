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
import google.generativeai as genai
import PIL.Image

# --- STEP 1: AI CONFIGURATION ---
# Replace 'YOUR_API_KEY' with your actual Gemini API Key
genai.configure(api_key="AIzaSyBcRTBb3IqkSooLBZQPNJi0mqjQDm0DVyhI")
model = genai.GenerativeModel('gemini-2.5-flash')
def ask_ai_about_image(filename):
    """Sends the captured image to Gemini for analysis."""
    print(f"\n[AI] Analyzing capture: {filename}...")
    try:
        img = PIL.Image.open(filename)
        # You can change the prompt below to suit your needs
        prompt = "Describe the most important details inside this box in two short sentences."
        response = model.generate_content([prompt, img])
        
        print("\n" + "="*50)
        print("AI ANALYSIS RESULT:")
        print(response.text.strip())
        print("="*50 + "\n")
    except Exception as e:
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
        self.rect = self.canvas.create_rectangle(0, 0, 0, 0, outline="green", width=3)
        self.label = self.canvas.create_text(0, 0, text="", fill="green", font=("Arial", 14, "bold"), anchor="sw")
        
    def update_box(self, x1, y1, x2, y2, state="moving", countdown="", flash_now=False):
        try:
            self.canvas.coords(self.rect, x1, y1, x2, y2)
            self.canvas.coords(self.label, x1, y1 - 5)
            self.canvas.itemconfig(self.label, text=countdown)
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
capture_requested = False  
is_running = True 
is_locked = False
last_move_time = time.time()
fist_start_time = None
lock_threshold, lock_delay = 20, 3.0

def reset_lock():
    global is_locked, last_move_time
    is_locked = False
    last_move_time = time.time()
    print("Lock Released. Resuming tracking...")

keyboard.add_hotkey('r', reset_lock)
keyboard.add_hotkey('q', lambda: globals().update(is_running=False))

# --- STEP 5: VISION BRAIN ---
screen_w, screen_h = pyautogui.size()
video = cv2.VideoCapture(0)
hands_detector = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.8)

p_t_x, p_t_y, p_i_x, p_i_y = 0, 0, 0, 0
smooth_factor = 0.15

print("AR AI Sniper: ACTIVE")
print("- Freeze for 3s to trigger AI Analysis")
print("- Press 'R' to reset box | 'Q' to Quit")

try:
    while is_running:
        success, img = video.read()
        if not success: break
        
        img = cv2.flip(img, 1)
        result = hands_detector.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        display_text, current_state, flash_effect = "", "moving", False

        if is_locked:
            current_state = "locked"
            display_text = "AI ANALYSIS SENT - Press 'R' to move"
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
                            # Capture and AI Logic
                            x1, y1, x2, y2 = current_box
                            width, height = x2 - x1, y2 - y1
                            if width > 20:
                                region = {"top": int(y1), "left": int(x1), "width": int(width), "height": int(height)}
                                filename = f"ai_cap_{int(time.time())}.png"
                                mss.tools.to_png(sct.grab(region).rgb, sct.grab(region).size, output=filename)
                                # Start AI analysis in background
                                threading.Thread(target=ask_ai_about_image, args=(filename,), daemon=True).start()
                        else:
                            display_text = f"Analyzing in {max(0, int(lock_delay - (time.time() - last_move_time)) + 1)}s..."

                    p_t_x += (tx - p_t_x) * smooth_factor
                    p_t_y += (ty - p_t_y) * smooth_factor
                    p_i_x += (ix - p_i_x) * smooth_factor
                    p_i_y += (iy - p_i_y) * smooth_factor
                    current_box = [int(min(p_t_x, p_i_x)), int(min(p_t_y, p_i_y)), int(max(p_t_x, p_i_x)), int(max(p_t_y, p_i_y))]

        overlay.update_box(*current_box, state=current_state, countdown=display_text, flash_now=flash_effect)
        time.sleep(0.01)

finally:
    video.release()
    overlay.close()
    keyboard.unhook_all()
    sys.exit()