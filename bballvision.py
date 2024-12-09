from ultralytics import YOLO
import cv2
import math
import numpy as np
from collections import deque
from helper import is_increasing_distances, is_ball_below_rim, is_ball_above_rim, is_made_shot, write_text_with_background, get_available_filename

# Load Video
video_path = 'input_vids/IMG_6448.mov'
cap = cv2.VideoCapture(video_path)

# Stuff for output video
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS))

output_path = get_available_filename('output_vids', 'output', 'mp4')
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

model = YOLO("bballvision.pt")

# "made" class doesn't work very well
classnames = ["ball", "made", "person", "rim", "shoot"]

total_attempts = 0
total_made = 0

frame = 0

# In the format [x_center, y_center, frame]
ball_position = deque(maxlen=30)
shoot_position = deque(maxlen=30)
# In the format [x1, y1, x2, y2, frame]
rim_position = deque(maxlen=30)

ball_above_rim = None

overlay = None

while True:
    success, img = cap.read()
    if not success:
        break

    results = model(img, stream=True)
    detections = np.empty((0,5))

    for r in results:
        boxes = r.boxes
        for box in boxes:
            
            # Bounding Box and confidence
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            w, h = x2-x1, y2-y1
            conf = math.ceil(box.conf[0] * 100) / 100

            # Class name
            cls = int(box.cls[0])
            current_class = classnames[cls]

            cx, cy = x1+w // 2, y1+h // 2

            # Detecting the "shoot" action
            if current_class == "shoot" and conf>0.4:
                shoot_position.append([cx, cy, frame])
            
            # Check if ball is detected
            if current_class == "ball" and conf>0.4:
                ball_position.append([cx, cy, frame])

                # Draw the center point
                cv2.circle(img, (cx, cy), 5, (0, 0, 200), cv2.FILLED)

            # Check if rim is detected
            if current_class == "rim" and conf>0.4:
                rim_position.append([x1, y1, x2, y2, frame])
            
            # Draw bounding boxes and classnames
            cv2.rectangle(img, (x1, y1), (x2, y2), (200, 0, 0), 2)
            write_text_with_background(img, f'{current_class} {conf}', (x1, y1 - 10), cv2.FONT_HERSHEY_PLAIN, 1, (200, 200, 200), (100, 0, 0), 1)


    # Checks if distance from shoot position and ball keeps increasing after shot attempt
    # Checks if last time "shoot" was detected was five frames ago
    print(shoot_position)
    if shoot_position and shoot_position[-1][2] == frame - 3:
        last_ball_pos = [(cx, cy) for cx, cy, frame in list(ball_position)[-3:]]
        print("HHIIIIIIJIHIHIHIHIHI")
        if is_increasing_distances((shoot_position[-1][0], shoot_position[-1][1]), last_ball_pos):
            total_attempts += 1

    # This means that ball was above rim (or between lower and higher rim bound) in last frame and is now below rim
    if ball_above_rim and is_ball_below_rim(ball_position[-1], rim_position[-1]):
        if is_made_shot(ball_above_rim, ball_position[-1], rim_position[-1]):
            total_made += 1
        ball_above_rim = None

    # By doing it through an if statement instead of just assignment, the variable ball_above_rim remains true when
    # lower_rim_bound < ball < higher_rim_bound
    if is_ball_above_rim(ball_position[-1], rim_position[-1]):
        ball_above_rim = ball_position[-1]
    
    write_text_with_background(img, f'Attempts: {str(total_attempts)}', (50, 150), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), (0, 50, 0), 2)
    write_text_with_background(img, f'Made Shots: {total_made}', (50, 200), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), (0, 50, 0), 2)

    # Adds circles on ball position every 5 frames
    if overlay is None:
        overlay = np.zeros_like(img, dtype=np.uint8)

    # Draws a path for the balls
    if frame % 3 == 0:
        # Clear the overlay (reset to transparent)
        overlay = np.zeros_like(img, dtype=np.uint8)
        
        for pos in ball_position:
            cx, cy, pos_frame = pos
            if pos_frame % 5 == 0:
                cv2.circle(overlay, (cx, cy), 5, (0, 0, 255), cv2.FILLED)
    
    frame += 1

    # Blend the overlay onto the main frame
    blended_img = cv2.addWeighted(img, 1.0, overlay, 1, 0)

    cv2.imshow("Image", blended_img)

    # Write the frame to the video file
    out.write(blended_img)

    # To watch video frame by frame
    # cv2.waitKey(0)

    # To watch video continuosly
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()
