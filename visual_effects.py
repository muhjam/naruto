import cv2
import numpy as np
import os
import math
import pygame

class VisualEffects:
    def __init__(self, seals_dir, jutsu_dir):
        self.seals_dir = seals_dir
        self.jutsu_dir = jutsu_dir
        self.seal_images = {}
        self.jutsu_assets = {} 
        self.audio_files = {}
        
        # Initialize pygame mixer for audio
        try:
            pygame.mixer.init()
        except:
            print("Warning: Pygame mixer could not be initialized.")
            
        self.load_seals()
        self.load_jutsus()

    def load_seals(self):
        if not os.path.exists(self.seals_dir):
            return
        for filename in os.listdir(self.seals_dir):
            if filename.lower().endswith(".png"):
                name = filename.split(".")[0]
                img = cv2.imread(os.path.join(self.seals_dir, filename), cv2.IMREAD_UNCHANGED)
                if img is not None:
                    self.seal_images[name] = img

    def load_jutsus(self):
        if not os.path.exists(self.jutsu_dir):
            return
        
        jutsu_config = {
            'Rasengan': 'rasengan.gif',
            'Chidori': 'cidori.gif',
            'Fire Ball': 'fireball.mp4',
            'Sharingan': 'sharingan.gif'
        }
        
        for name, filename in jutsu_config.items():
            path = os.path.join(self.jutsu_dir, filename)
            if os.path.exists(path):
                frames = []
                cap = cv2.VideoCapture(path)
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    frames.append(frame)
                cap.release()
                
                if frames:
                    self.jutsu_assets[name] = {'frames': frames}
                    
                # Look for corresponding audio
                # For mp4, we check for .mp3 or .wav
                audio_exts = ['.mp3', '.wav', '.m4a']
                base_path = os.path.splitext(path)[0]
                for ext in audio_exts:
                    audio_path = base_path + ext
                    if os.path.exists(audio_path):
                        self.audio_files[name] = audio_path
                        break

    def get_jutsu_duration(self, jutsu_name):
        if jutsu_name in self.jutsu_assets:
            return len(self.jutsu_assets[jutsu_name]['frames'])
        return 300 # Default 10s

    def play_audio(self, jutsu_name):
        if jutsu_name in self.audio_files:
            try:
                pygame.mixer.music.load(self.audio_files[jutsu_name])
                pygame.mixer.music.play()
            except Exception as e:
                print(f"Error playing audio: {e}")

    def stop_audio(self):
        try:
            pygame.mixer.music.stop()
        except:
            pass

    def overlay_transparent(self, background, overlay, x, y, size=None):
        if size:
            if isinstance(size, tuple):
                overlay = cv2.resize(overlay, size)
            else:
                overlay = cv2.resize(overlay, (size, size))
        
        h, w = overlay.shape[:2]
        x1, x2 = max(0, x), min(background.shape[1], x + w)
        y1, y2 = max(0, y), min(background.shape[0], y + h)
        
        overlay_x1, overlay_x2 = max(0, -x), min(w, background.shape[1] - x)
        overlay_y1, overlay_y2 = max(0, -y), min(h, background.shape[0] - y)
        
        if x1 >= x2 or y1 >= y2:
            return background
            
        overlay_chunk = overlay[overlay_y1:overlay_y2, overlay_x1:overlay_x2]
        
        if overlay_chunk.shape[2] < 4:
            gray = cv2.cvtColor(overlay_chunk, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
            mask = mask.astype(float) / 255.0
        else:
            mask = overlay_chunk[:,:,3].astype(float) / 255.0
            overlay_chunk = overlay_chunk[:,:,:3]

        for c in range(0, 3):
            background[y1:y2, x1:x2, c] = (mask * overlay_chunk[:,:,c] +
                                          (1.0 - mask) * background[y1:y2, x1:x2, c])
        return background

    def draw_guide(self, img, seal_name):
        if seal_name in self.seal_images:
            h, w = img.shape[:2]
            guide_size = 150
            x, y = w - guide_size - 20, 20
            self.overlay_transparent(img, self.seal_images[seal_name], x, y, guide_size)
            cv2.putText(img, f"Seal: {seal_name}", (x, y + guide_size + 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    def draw_jutsu_info(self, img, jutsu_name, step, total_steps):
        cv2.putText(img, f"Jutsu: {jutsu_name}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(img, f"Step: {step}/{total_steps}", (20, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    def draw_gif_effect(self, img, jutsu_name, centers, frame_idx, mode='hand'):
        if jutsu_name not in self.jutsu_assets:
            return
        
        asset = self.jutsu_assets[jutsu_name]
        frames = asset['frames']
        current_frame = frames[frame_idx % len(frames)]
        
        if mode == 'full':
            frame_resized = cv2.resize(current_frame, (img.shape[1], img.shape[0]))
            img[:] = frame_resized[:]
        elif mode == 'eye':
            size = 40
            for center in centers:
                x, y = center[0] - size//2, center[1] - size//2
                self.overlay_transparent(img, current_frame, x, y, size)
        else: # hand
            size = 250
            for center in centers:
                x, y = center[0] - size//2, center[1] - size//2
                self.overlay_transparent(img, current_frame, x, y, size)
