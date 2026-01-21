# PointAI: Gesture-Driven AI Vision Bridge

**PointAI** is a real-time, gesture-controlled Augmented Reality (AR) HUD that allows users to interact with their screen content through physical movement. By "locking on" to specific regions with hand gestures, the system captures visual data and utilizes the **Gemini 2.0 Flash API** to provide instant, high-context intelligence on people, code, and environments.



## 🚀 Key Features

* **Touchless Interaction:** Leverages **MediaPipe** landmark detection to track hand movements and trigger "lock-on" events without physical input.
* **Asynchronous HUD:** Implements a **Multi-threaded architecture** to handle high-latency API requests in the background, maintaining a smooth 60 FPS user interface.
* **Cinematic Smoothing:** Uses **Linear Interpolation (Lerp)** to stabilize the HUD, filtering out webcam sensor noise and natural hand tremors.
* **Context-Aware Intelligence:** Custom prompt engineering enables the AI to provide detailed 2-sentence bios for people and 4-line functional breakdowns for computer code.
* **Tactical UI:** A transparent **Tkinter** overlay provides real-time feedback with state-based color changes (Green: Tracking, Orange: Closing, Red: Locked).

## 🛠️ Technical Stack

* **Language:** Python 3.10+
* **Vision:** OpenCV, MediaPipe
* **Intelligence:** Google Gemini 2.0 Flash API
* **System:** MSS (Screen Capture), Keyboard (Global Hotkeys)
* **GUI:** Tkinter (Transparent Canvas)

## 📐 How It Works

1.  **Detection:** The system tracks the distance between the Thumb and Index finger.
2.  **Smoothing:** Landmark coordinates are smoothed using:  
    `Position += (Target - Current) * SmoothFactor`
3.  **Locking:** If the hand remains within a spatial threshold for 2 seconds, a "Lock" is triggered.
4.  **Analysis:** A background thread captures the screen region and dispatches it to the Gemini API.
5.  **Feedback:** The UI provides a "shutter flash" effect and displays the AI intel directly on the HUD.



## 📦 Installation & Setup

1. **Clone the Repository**
   ```bash
   git clone [https://github.com/yourusername/PointAI.git](https://github.com/yourusername/PointAI.git)
   cd PointAI
