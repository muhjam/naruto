import cv2
import numpy as np
from hand_detector import NarutoDetector
from visual_effects import VisualEffects

def main():
    camera_index = 0
    # Try multiple indices for camera
    cap = None
    for idx in range(3):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            camera_index = idx
            break
            
    if cap is None or not cap.isOpened():
        print("Error: Could not open any webcam.")
        return

    def change_camera(current_index):
        new_index = (current_index + 1) % 5
        print(f"Switching to camera index: {new_index}")
        new_cap = cv2.VideoCapture(new_index)
        if not new_cap.isOpened():
            print(f"Camera index {new_index} not available, resetting to {current_index}")
            return cv2.VideoCapture(current_index), current_index
        return new_cap, new_index

    detector = NarutoDetector()
    effects = VisualEffects("seals-image", "jutsu")
    
    current_jutsu = None
    jutsu_step = 0
    jutsu_list = {
        '1': {'name': 'Rasengan', 'sequence': ['ram', 'horse'], 'duration': None}, 
        '2': {'name': 'Chidori', 'sequence': ['dog', 'ram'], 'duration': None}, 
        '3': {'name': 'Fire Ball', 'sequence': ['dog', 'horse'], 'duration': None}, 
        '4': {'name': 'Sharingan', 'sequence': ['ram'], 'duration': None}
    }
    
    active_jutsu = None
    jutsu_timer = 0
    jutsu_frame_count = 0
    last_detected_seal = None
    seal_hold_frames = 0
    REQUIRED_HOLD = 1 
    mirror_view = True # Default mirror aktif
    seal_cooldown = 0 # Jeda antar segel

    print("--- Naruto Vision Started ---")
    print("Press 1-4: Select Jutsu")
    print("Press c: Cycle Camera (untuk ganti ke OBS)")
    print("Press m: Toggle Mirror View")
    print("Press q: Quit")

    while True:
        success, img = cap.read()
        if not success:
            cap.release()
            cap = cv2.VideoCapture(camera_index)
            cv2.waitKey(1000)
            continue
            
        if mirror_view:
            img = cv2.flip(img, 1) # Mirror effect
            
        img = detector.find_all(img, draw=True)
        hands_info = detector.get_hand_info(img)
        eye_info = detector.get_eye_info(img)
        detected_seal = detector.detect_seal(hands_info)
        
        # DEBUG: Tampilkan status di layar
        mirror_status = "ON" if mirror_view else "OFF"
        cooldown_status = f" | CD: {seal_cooldown}" if seal_cooldown > 0 else ""
        debug_text = f"Detected: {detected_seal} | Total Hands: {len(hands_info)} | Mirror: {mirror_status}{cooldown_status}"
        cv2.putText(img, debug_text, (img.shape[1]-550, img.shape[0]-40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        # Buffer seal detection
        if detected_seal == last_detected_seal and detected_seal is not None:
            seal_hold_frames += 1
        else:
            last_detected_seal = detected_seal
            seal_hold_frames = 0
            
        confirmed_seal = last_detected_seal if seal_hold_frames >= REQUIRED_HOLD else None
        
        # Kelola cooldown
        if seal_cooldown > 0:
            seal_cooldown -= 1
            confirmed_seal = None # Abaikan input selama cooldown
        
        # Handle Keyboard Input
        key_code = cv2.waitKey(1) & 0xFF
        key_char = chr(key_code)
        
        if key_char in jutsu_list:
            current_jutsu = jutsu_list[key_char]
            jutsu_step = 0
            # Ensure audio stops if switching
            effects.stop_audio()
            active_jutsu = None
            seal_cooldown = 0
            print(f"Selected Jutsu: {current_jutsu['name']}")
        elif key_char == 'c':
            cap.release()
            cap, camera_index = change_camera(camera_index)
        elif key_char == 'm':
            mirror_view = not mirror_view
            print(f"Mirror View: {'ON' if mirror_view else 'OFF'}")
        elif key_char == 'q':
            effects.stop_audio()
            break

        # Jutsu State Machine
        if current_jutsu and not active_jutsu:
            target_seal = current_jutsu['sequence'][jutsu_step]
            effects.draw_guide(img, target_seal)
            effects.draw_jutsu_info(img, current_jutsu['name'], jutsu_step, len(current_jutsu['sequence']))
            
            if confirmed_seal == target_seal:
                jutsu_step += 1
                seal_cooldown = 30 # Jeda 1 detik (asumsi 30fps)
                print(f"Seal matched: {target_seal}! Next step: {jutsu_step}")
                if jutsu_step >= len(current_jutsu['sequence']):
                    active_jutsu = current_jutsu['name']
                    
                    # Force 10 seconds (300 frames) for specific jutsus
                    if active_jutsu in ['Rasengan', 'Chidori', 'Sharingan']:
                        jutsu_timer = 300
                    else:
                        # Use actual duration from asset for Fire Ball (MP4)
                        asset_duration = effects.get_jutsu_duration(active_jutsu)
                        jutsu_timer = asset_duration if asset_duration > 0 else 300
                        
                    jutsu_frame_count = 0
                    current_jutsu = None
                    # Play Audio
                    effects.play_audio(active_jutsu)
                    print(f"JUTSU ACTIVATED: {active_jutsu}")
        
        # Draw Active Jutsu Effect
        if active_jutsu:
            if active_jutsu != 'Fire Ball':
                cv2.putText(img, f"ACTIVE: {active_jutsu}!!!", (20, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            
            if active_jutsu == 'Sharingan':
                if eye_info:
                    effects.draw_gif_effect(img, active_jutsu, eye_info, jutsu_frame_count, mode='eye')
            elif active_jutsu == 'Fire Ball':
                effects.draw_gif_effect(img, active_jutsu, None, jutsu_frame_count, mode='full')
            else: # Rasengan, Chidori
                if hands_info:
                    center = tuple(hands_info[0]["lm_list"][9])
                    effects.draw_gif_effect(img, active_jutsu, [center], jutsu_frame_count, mode='hand')
            
            jutsu_frame_count += 1
            jutsu_timer -= 1
            if jutsu_timer <= 0:
                active_jutsu = None
                effects.stop_audio()
                print("Jutsu ended.")

        # Display Help Text
        cv2.putText(img, "1:Rasengan 2:Chidori 3:FireBall 4:Sharingan q:Quit", (10, img.shape[0]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("Naruto Vision", img)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
