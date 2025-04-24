import cv2
import mediapipe as mp
import pyautogui
import time
import numpy as np
import util
from pynput.mouse import Button, Controller
mouse = Controller()

# Constants for gesture cooldowns
SCREENSHOT_COOLDOWN = 2.0  # seconds
DOUBLE_CLICK_COOLDOWN = 0.5  # seconds


screen_width, screen_height = pyautogui.size()

mpHands = mp.solutions.hands
hands = mpHands.Hands(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    max_num_hands=1
)


def find_finger_tip(processed):
    if processed.multi_hand_landmarks:
        hand_landmarks = processed.multi_hand_landmarks[0]  # Assuming only one hand is detected
        index_finger_tip = hand_landmarks.landmark[mpHands.HandLandmark.INDEX_FINGER_TIP]
        return index_finger_tip
    return None, None


def move_mouse(index_finger_tip):
    if index_finger_tip is not None:
        x = int(index_finger_tip.x * screen_width)
        y = int(index_finger_tip.y / 2 * screen_height)
        pyautogui.moveTo(x, y)


def is_left_click(landmark_list, thumb_index_dist):
    return (
            util.get_angle(landmark_list[5], landmark_list[6], landmark_list[8]) < 50 and
            util.get_angle(landmark_list[9], landmark_list[10], landmark_list[12]) > 90 and
            thumb_index_dist > 50
    )


def is_right_click(landmark_list, thumb_index_dist):
    return (
            util.get_angle(landmark_list[9], landmark_list[10], landmark_list[12]) < 50 and
            util.get_angle(landmark_list[5], landmark_list[6], landmark_list[8]) > 90  and
            thumb_index_dist > 50
    )


def is_double_click(landmark_list, thumb_index_dist):
    """
    Double click gesture: Bend both index and middle fingers, keep ring finger straight
    - Both index and middle fingers should be bent (angle < 70)
    - Ring finger should be relatively straight (angle > 100)
    - Thumb should not be too close to index finger
    """
    index_bent = util.get_angle(landmark_list[5], landmark_list[6], landmark_list[8]) < 70
    middle_bent = util.get_angle(landmark_list[9], landmark_list[10], landmark_list[12]) < 70
    ring_straight = util.get_angle(landmark_list[13], landmark_list[14], landmark_list[16]) > 100
    thumb_away = thumb_index_dist > 50

    return index_bent and middle_bent and ring_straight and thumb_away


def is_screenshot(landmark_list, _):
    """
    Screenshot gesture: Bend index, middle, and ring fingers, extend pinky finger
    - Index, middle, and ring fingers should be bent (angle < 90) - more lenient
    - Pinky finger should be extended (angle > 90) - more lenient
    - Thumb position doesn't matter anymore

    This is a more lenient version that focuses on the key aspect:
    three bent fingers and an extended pinky

    Note: The second parameter is ignored but kept for compatibility
    """
    # Get the angles
    index_angle = util.get_angle(landmark_list[5], landmark_list[6], landmark_list[8])
    middle_angle = util.get_angle(landmark_list[9], landmark_list[10], landmark_list[12])
    ring_angle = util.get_angle(landmark_list[13], landmark_list[14], landmark_list[16])
    pinky_angle = util.get_angle(landmark_list[17], landmark_list[18], landmark_list[20])

    # Check conditions with more lenient thresholds
    index_bent = index_angle < 90  # More lenient angle
    middle_bent = middle_angle < 90  # More lenient angle
    ring_bent = ring_angle < 90  # More lenient angle
    pinky_straight = pinky_angle > 90  # More lenient angle

    # Debug info - uncomment if needed
    # print(f"Screenshot angles: index={index_angle:.1f}, middle={middle_angle:.1f}, ring={ring_angle:.1f}, pinky={pinky_angle:.1f}")
    # print(f"Screenshot conditions: index_bent={index_bent}, middle_bent={middle_bent}, ring_bent={ring_bent}, pinky_straight={pinky_straight}")

    # Alternative detection method: check if pinky is more extended than other fingers
    pinky_more_extended = (pinky_angle > index_angle + 20) and (pinky_angle > middle_angle + 20) and (pinky_angle > ring_angle + 20)

    # Two ways to detect the gesture:
    # 1. Traditional way: three bent fingers and extended pinky
    traditional_detection = index_bent and middle_bent and ring_bent and pinky_straight

    # 2. Relative way: pinky is significantly more extended than other fingers
    relative_detection = pinky_more_extended and (index_bent or middle_bent or ring_bent)

    # Return true if either detection method works
    return traditional_detection or relative_detection


# State tracking variables
last_gesture = None
last_gesture_time = 0

def detect_gesture(frame, landmark_list, processed):
    global last_gesture, last_gesture_time

    current_time = time.time()

    if len(landmark_list) >= 21:
        index_finger_tip = find_finger_tip(processed)
        thumb_index_dist = util.get_distance([landmark_list[4], landmark_list[8]])  # Distance between thumb and index tip

        # Mouse movement
        if util.get_distance([landmark_list[4], landmark_list[5]]) < 50 and util.get_angle(landmark_list[5], landmark_list[6], landmark_list[8]) > 90:
            move_mouse(index_finger_tip)

        # Left click
        elif is_left_click(landmark_list, thumb_index_dist):
            # Visual feedback
            cv2.putText(frame, "Left Click", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Execute click
            mouse.press(Button.left)
            mouse.release(Button.left)

            last_gesture = "left_click"
            last_gesture_time = current_time

        # Right click
        elif is_right_click(landmark_list, thumb_index_dist):
            # Visual feedback
            cv2.putText(frame, "Right Click", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # Execute click
            mouse.press(Button.right)
            mouse.release(Button.right)

            last_gesture = "right_click"
            last_gesture_time = current_time

        # Double click - with cooldown to prevent multiple double-clicks
        elif is_double_click(landmark_list, thumb_index_dist):
            # Visual feedback for double click gesture
            index_tip_x = int(landmark_list[8][0] * frame.shape[1])
            index_tip_y = int(landmark_list[8][1] * frame.shape[0])
            middle_tip_x = int(landmark_list[12][0] * frame.shape[1])
            middle_tip_y = int(landmark_list[12][1] * frame.shape[0])

            # Draw circles on fingertips
            cv2.circle(frame, (index_tip_x, index_tip_y), 15, (255, 255, 0), -1)  # Yellow circle on index
            cv2.circle(frame, (middle_tip_x, middle_tip_y), 15, (255, 255, 0), -1)  # Yellow circle on middle

            # Execute double-click with cooldown
            if last_gesture != "double_click" or (current_time - last_gesture_time) > DOUBLE_CLICK_COOLDOWN:
                # Visual feedback
                cv2.putText(frame, "Double Click", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

                # Use pynput for more reliable double-click
                mouse.click(Button.left, 2)

                last_gesture = "double_click"
                last_gesture_time = current_time
            else:
                # Show cooldown message
                cv2.putText(frame, "Double Click (Cooldown)", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        # Screenshot - with cooldown to prevent multiple screenshots
        elif is_screenshot(landmark_list, thumb_index_dist):
            # Visual feedback for screenshot gesture
            index_tip_x = int(landmark_list[8][0] * frame.shape[1])
            index_tip_y = int(landmark_list[8][1] * frame.shape[0])
            middle_tip_x = int(landmark_list[12][0] * frame.shape[1])
            middle_tip_y = int(landmark_list[12][1] * frame.shape[0])
            ring_tip_x = int(landmark_list[16][0] * frame.shape[1])
            ring_tip_y = int(landmark_list[16][1] * frame.shape[0])
            pinky_tip_x = int(landmark_list[20][0] * frame.shape[1])
            pinky_tip_y = int(landmark_list[20][1] * frame.shape[0])

            # Draw circles on fingertips with larger, more visible indicators
            cv2.circle(frame, (index_tip_x, index_tip_y), 15, (0, 255, 255), -1)  # Cyan circle on index
            cv2.circle(frame, (middle_tip_x, middle_tip_y), 15, (0, 255, 255), -1)  # Cyan circle on middle
            cv2.circle(frame, (ring_tip_x, ring_tip_y), 15, (0, 255, 255), -1)  # Cyan circle on ring
            cv2.circle(frame, (pinky_tip_x, pinky_tip_y), 20, (255, 255, 255), -1)  # Larger white circle on pinky

            # Draw a line connecting the fingertips to make the gesture more visible
            cv2.line(frame, (index_tip_x, index_tip_y), (middle_tip_x, middle_tip_y), (0, 255, 255), 2)
            cv2.line(frame, (middle_tip_x, middle_tip_y), (ring_tip_x, ring_tip_y), (0, 255, 255), 2)
            cv2.line(frame, (ring_tip_x, ring_tip_y), (pinky_tip_x, pinky_tip_y), (255, 255, 255), 2)

            # Draw text to clearly show the gesture is detected
            cv2.putText(frame, "SCREENSHOT GESTURE DETECTED", (50, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            # Execute screenshot with cooldown
            if last_gesture != "screenshot" or (current_time - last_gesture_time) > SCREENSHOT_COOLDOWN:
                # Show countdown with better visibility
                for i in range(3, 0, -1):
                    temp_frame = frame.copy()
                    # Add a semi-transparent overlay
                    overlay = temp_frame.copy()
                    cv2.rectangle(overlay, (0, 0), (temp_frame.shape[1], temp_frame.shape[0]), (0, 0, 0), -1)
                    cv2.addWeighted(overlay, 0.3, temp_frame, 0.7, 0, temp_frame)

                    # Add countdown text
                    cv2.putText(temp_frame, f"SCREENSHOT IN {i}...", (temp_frame.shape[1]//2 - 150, temp_frame.shape[0]//2),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

                    # Add red border
                    cv2.rectangle(temp_frame, (0, 0), (temp_frame.shape[1], temp_frame.shape[0]), (0, 0, 255), 10)

                    # Show the frame
                    cv2.imshow('Hand Gesture Mouse Control', temp_frame)
                    cv2.waitKey(500)  # 0.5 second delay

                # Take screenshot with a brief pause to allow UI to hide
                cv2.waitKey(200)  # Small delay before taking screenshot
                im1 = pyautogui.screenshot()
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f'screenshot_{timestamp}.png'
                im1.save(filename)

                # Flash the screen white to indicate screenshot was taken
                flash_frame = np.ones_like(frame) * 255
                cv2.putText(flash_frame, "SCREENSHOT TAKEN!", (frame.shape[1]//2 - 150, frame.shape[0]//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                cv2.imshow('Hand Gesture Mouse Control', flash_frame)
                cv2.waitKey(300)  # Flash for 300ms

                # Visual feedback
                cv2.putText(frame, f"Screenshot Saved: {filename}", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                last_gesture = "screenshot"
                last_gesture_time = current_time

                # Print confirmation to console
                print(f"Screenshot saved: {filename}")
            else:
                # Show cooldown message
                cv2.putText(frame, "Screenshot (Cooldown)", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)


def draw_help_text(frame):
    """Draw help text on the frame to show available gestures"""
    _, w = frame.shape[:2]  # Only need width for positioning

    help_text = [
        "Gestures:",
        "- Move: Index finger straight",
        "- Left Click: Bend index, keep middle straight",
        "- Right Click: Bend middle, keep index straight",
        "- Double Click: Bend index and middle fingers",
        "- Screenshot: Bend index, middle, ring + extend pinky",
        "Press 'q' to quit"
    ]

    # Draw semi-transparent background for text
    overlay = frame.copy()
    cv2.rectangle(overlay, (w-300, 10), (w-10, 160), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Draw text
    for i, text in enumerate(help_text):
        cv2.putText(frame, text, (w-290, 35 + i*20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def main():
    draw = mp.solutions.drawing_utils
    cap = cv2.VideoCapture(0)

    # Display startup message
    print("\n=== Hand Gesture Mouse Control ===")
    print("\nAvailable gestures:")
    print("- Move: Index finger straight")
    print("- Left Click: Bend index finger, keep middle finger straight")
    print("- Right Click: Bend middle finger, keep index finger straight")
    print("- Double Click: Bend both index and middle fingers, keep ring finger straight")
    print("- Screenshot: Bend index, middle, and ring fingers, extend pinky finger")
    print("\nPress 'q' to quit")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            processed = hands.process(frameRGB)

            landmark_list = []
            if processed.multi_hand_landmarks:
                hand_landmarks = processed.multi_hand_landmarks[0]  # Assuming only one hand is detected

                # Draw hand landmarks with improved visibility
                draw_options = mp.solutions.drawing_utils.DrawingSpec(
                    color=(0, 255, 0), thickness=2, circle_radius=4)
                connection_options = mp.solutions.drawing_utils.DrawingSpec(
                    color=(255, 0, 0), thickness=2, circle_radius=2)
                draw.draw_landmarks(frame, hand_landmarks, mpHands.HAND_CONNECTIONS,
                                   draw_options, connection_options)

                for lm in hand_landmarks.landmark:
                    landmark_list.append((lm.x, lm.y))

            detect_gesture(frame, landmark_list, processed)

            # Draw help text
            draw_help_text(frame)

            cv2.imshow('Hand Gesture Mouse Control', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Hand Gesture Mouse Control terminated.")


if __name__ == '__main__':
    main()





