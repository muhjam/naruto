import cv2
import mediapipe as mp
import math

class NarutoDetector:
    def __init__(self, mode=False, max_hands=2, detection_con=0.7, track_con=0.7):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(static_image_mode=mode, 
                                        max_num_hands=max_hands,
                                        min_detection_confidence=detection_con, 
                                        min_tracking_confidence=track_con)
        
        # Face Mesh for eye tracking
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(static_image_mode=mode,
                                                 max_num_faces=1,
                                                 min_detection_confidence=0.5,
                                                 min_tracking_confidence=0.5)
        
        self.mp_draw = mp.solutions.drawing_utils
        self.tip_ids = [4, 8, 12, 16, 20]

    def find_all(self, img, draw=True):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.hand_results = self.hands.process(img_rgb)
        self.face_results = self.face_mesh.process(img_rgb)
        
        if self.hand_results.multi_hand_landmarks and draw:
            for hand_lms in self.hand_results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(img, hand_lms, self.mp_hands.HAND_CONNECTIONS)
        
        return img

    def get_hand_info(self, img):
        hands_info = []
        if self.hand_results.multi_hand_landmarks:
            for hand_type, hand_lms in zip(self.hand_results.multi_handedness, self.hand_results.multi_hand_landmarks):
                lm_list = []
                for id, lm in enumerate(hand_lms.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lm_list.append([cx, cy])
                
                # Check which fingers are up
                fingers = []
                label = hand_type.classification[0].label # "Left" or "Right"
                
                # Thumb
                if label == "Left":
                    if lm_list[self.tip_ids[0]][0] > lm_list[self.tip_ids[0] - 1][0]:
                        fingers.append(1)
                    else:
                        fingers.append(0)
                else:
                    if lm_list[self.tip_ids[0]][0] < lm_list[self.tip_ids[0] - 1][0]:
                        fingers.append(1)
                    else:
                        fingers.append(0)

                # 4 Fingers
                for id in range(1, 5):
                    if lm_list[self.tip_ids[id]][1] < lm_list[self.tip_ids[id] - 2][1]:
                        fingers.append(1)
                    else:
                        fingers.append(0)
                
                hands_info.append({"label": label, "lm_list": lm_list, "fingers": fingers})
        return hands_info

    def get_eye_info(self, img):
        if self.face_results.multi_face_landmarks:
            face_lms = self.face_results.multi_face_landmarks[0]
            h, w, _ = img.shape
            
            # Left eye center (landmark 159)
            # Right eye center (landmark 386)
            left_eye = face_lms.landmark[159]
            right_eye = face_lms.landmark[386]
            
            return [
                (int(left_eye.x * w), int(left_eye.y * h)),
                (int(right_eye.x * w), int(right_eye.y * h))
            ]
        return None

    def detect_seal(self, hands_info):
        if not hands_info:
            return None
        
        # We check each hand for specific patterns (Dog, Horse, Ram)
        # Using more lenient rules (finger counts and key positions)
        for hand in hands_info:
            f = hand["fingers"]
            f_sum = sum(f)
            
            # Ram: Peace sign (2nd and 3rd fingers up)
            if 2 <= f_sum <= 3 and f[1] == 1:
                return "ram"
            
            # Dog: Thumb and Pinky are key
            if f[0] == 1 and f[4] == 1 and f_sum <= 4:
                return "dog"

            # Horse: Most fingers up
            if f_sum >= 4:
                return "horse"
                
        return None
