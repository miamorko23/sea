import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QCursor, QPixmap, QIcon
from PyQt5.QtCore import Qt
import psycopg2
import subprocess
import csv
import time
from datetime import datetime
import cv2
import dlib
import imutils
import requests
from scipy.spatial import distance
from imutils import face_utils
from pygame import mixer
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


def disconnect_wifi():
    subprocess.call('netsh wlan disconnect', shell=True)


def connect_wifi(network):
    # Attempt to connect to the Wi-Fi network
    result = subprocess.call(f'netsh wlan connect name="{network}"', shell=True)
    # Return False if the command was successful (exit status 0), True otherwise
    return result != 0


def refresh_and_connect_wifi(network):
    # Disconnect from the current Wi-Fi network
    subprocess.call('netsh wlan disconnect', shell=True)
    # Scan for new Wi-Fi networks
    subprocess.call('netsh wlan show networks', shell=True)
    # Attempt to connect to the specified Wi-Fi network
    result = subprocess.call(f'netsh wlan connect name="{network}"', shell=True)
    # Return False if the command was successful (exit status 0), True otherwise
    return result != 0


def check_wifi_connection(ssid):
    try:
        output = subprocess.check_output(["netsh", "wlan", "show", "interface"])
        output = output.decode("utf-8")
        return ssid in output
    except subprocess.CalledProcessError:
        return False


secret_key = ''
brake_activator = 'SeaMern'

# Connect to the Brake Activator
connection_result = refresh_and_connect_wifi(brake_activator)  # True if not connected
while connection_result:
    connection_result = refresh_and_connect_wifi(brake_activator)
    print(f'Connecting to {brake_activator}...')
    time.sleep(5)


disconnect_wifi()  # Disconnect from the current Wi-Fi, in this case the SeaMern

# Transitioning to the INTERNET ACCESS
internet_wifi = '********'
# Connect to the internet_wifi
connection_result = refresh_and_connect_wifi(internet_wifi)  # True if not connected
while connection_result:
    connection_result = refresh_and_connect_wifi(internet_wifi)
    print(f'Connecting to {internet_wifi}...')
    time.sleep(5)

# Second layer in making sure the machine is connected to the Wi-Fi providing an internet connection
cloud = check_wifi_connection(internet_wifi)
while cloud:
    cloud = connect_wifi(internet_wifi)
    time.sleep(3)


# Record a drowsiness event locally
def record_drowsiness_event_local(status):
    with open('local_drowsiness_events.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().isoformat(), status])


# Upload local drowsiness events to the database
def upload_drowsiness_events_to_db(user_id):
    import psycopg2
    try:
        conn = psycopg2.connect(
            dbname="miamorko23",
            user="miamorko23_user",
            password="jsUL6Rbb6Ce1ZTopxZUtHO2hylVQIFA5",
            host="dpg-ckn0mf91rp3c73epu630-a.singapore-postgres.render.com",
            port="5432"
        )
        cur = conn.cursor()
        # Read the local drowsiness events
        with open('local_drowsiness_events.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                event_time, status = row
                cur.execute("""
                            INSERT INTO main_drowsinessevent (user_id, time, status)
                            SELECT user_ptr_id, %s, %s FROM main_userwithkey WHERE secret_key = %s
                            """, (event_time, status, secret_key))
        conn.commit()
        cur.close()
        conn.close()
        return 'ok kayo'
    except Exception as e:
        print("Failed to Upload Drowsiness Events:", e)


# Function to calculate the Eye Aspect Ratio (EAR)
def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear


# Main function for the drowsiness detection system
def sea():
    try:
        # Set the ESP8266 IP address
        esp8266_ip = "192.168.4.1"

        # Initialize the mixer and load the initial sound
        mixer.init()
        mixer.music.load("partial.mp3")

        # Get the current volume and set it to a predefined level
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current_volume_db = volume.GetMasterVolumeLevel()
        volume.SetMasterVolumeLevel(-20.461252212524414, None)

        # Initialize dlib's face detector and facial landmark predictor
        detect = dlib.get_frontal_face_detector()
        predict = dlib.shape_predictor("68FaceLandmarks.dat")

        # Grab the indexes of the facial landmarks for the left and right eye
        (lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
        (rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

        # Start the video stream
        cap = cv2.VideoCapture(0)
        flag = 0
        cnt = 0
        status = ''
        hp = 0

        # Define the EAR threshold and the number of consecutive frames for checking
        thresh = 0.25
        frame_check = 10

        while True:
            ret, frame = cap.read()
            frame = imutils.resize(frame, width=523, height=323)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            subjects = detect(gray, 0)

            for subject in subjects:
                shape = predict(gray, subject)
                shape = face_utils.shape_to_np(shape)
                leftEye = shape[lStart:lEnd]
                rightEye = shape[rStart:rEnd]
                leftEAR = eye_aspect_ratio(leftEye)
                rightEAR = eye_aspect_ratio(rightEye)
                ear = (leftEAR + rightEAR) / 2.0

                # Draw eye contours with a semi-transparent overlay
                leftEyeHull = cv2.convexHull(leftEye)
                rightEyeHull = cv2.convexHull(rightEye)
                cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
                cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)
                overlay = frame.copy()
                cv2.fillPoly(overlay, [leftEyeHull], (0, 255, 0, 70))
                cv2.fillPoly(overlay, [rightEyeHull], (0, 255, 0, 70))
                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

                # Connect the outer points of the eye contours to create sunglasses effect
                leftmost_point = tuple(leftEye[leftEye[:, 0].argmin()])
                rightmost_point = tuple(rightEye[rightEye[:, 0].argmax()])
                cv2.line(frame, leftmost_point, rightmost_point, (0, 255, 0), 2)

                if ear < thresh:
                    flag += 1
                    if flag >= frame_check:
                        cv2.rectangle(frame, (10, 20), (250, 60), (0, 0, 255), -1)
                        cv2.putText(frame, "EYE CLOSED", (10, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        if cnt >= 2 and not mixer.music.get_busy():
                            mixer.music.load("final.mp3")
                            mixer.music.play()
                            status = 'Hercules'
                            requests.get(f"http://{esp8266_ip}/ledon")
                            record_drowsiness_event_local('B')
                        if not mixer.music.get_busy():
                            mixer.music.play()
                            cnt += 1
                            if cnt == 1:
                                record_drowsiness_event_local('W')
                            if cnt == 2:
                                record_drowsiness_event_local('C')
                            if status == 'Hercules':
                                hp = 0

                else:
                    hi = 'hi'
                    sky = 'sky'
                    if cnt >= 1 and status != 'Hercules':
                        sky = 'blue'
                        if not mixer.music.get_busy():
                            volume.SetMasterVolumeLevel(current_volume_db, None)
                            hi = 'hello'
                    if status == 'Hercules':
                        if not mixer.music.get_busy():
                            mixer.music.play()
                            hp += 1
                        elif hp == 1:
                            volume.SetMasterVolumeLevel(current_volume_db, None)
                            mixer.music.load("partial.mp3")
                            hp = 0
                            status = ''
                            requests.get(f"http://{esp8266_ip}/ledoff")
                            record_drowsiness_event_local('BD')

                    flag = 0
                    if sky == 'sky' or hi == 'hello':
                        cnt = 0
                    cv2.rectangle(frame, (10, 20), (200, 60), (0, 255, 0), -1)
                    cv2.putText(frame, "AWAKE", (10, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                if cnt >= 2:
                    volume.SetMasterVolumeLevel(current_volume_db + 20.4, None)

            cv2.imshow("Frame", frame)

            # key = cv2.waitKey(1) & 0xFF
            # if key == ord('z'):
            #     # Disconnect from the current Wi-Fi
            #     disconnect_wifi()
            #     # Connect to a previously connected Wi-Fi
            #     connect_wifi('*******P')
            #
            #     # After DRIVING:
            #     while upload_drowsiness_events_to_db(secret_key) == 'ok kayo':
            #         # PRINT
            #         with open('local_drowsiness_events.csv', 'r') as file:
            #             for line in file:
            #                 print(line, end='')
            #         print("First_Print^________________________________")
            #         # ERASE
            #         with open('local_drowsiness_events.csv', 'w') as file:
            #             file.truncate()
            #         print("Erase^______________________________________")
            #         # PRINT
            #         with open('local_drowsiness_events.csv', 'r') as file:
            #             for line in file:
            #                 print(line, end='')
            #         print("Second_Print^_______________________________")
            #     else:
            #         print('NOT ok kayo')
            #     break

            key = cv2.waitKey(1) & 0xFF
            if key == ord('z'):

                # Transitioning to the INTERNET ACCESS
                disconnect_wifi()  # Disconnect from the current Wi-Fi, in this case the SeaMern
                # Connect to the internet_wifi
                connection_result_2 = refresh_and_connect_wifi(internet_wifi)  # True if not connected
                while connection_result_2:
                    connection_result_2 = refresh_and_connect_wifi(internet_wifi)
                    print(f'Connecting to {internet_wifi}...')
                    time.sleep(5)

                # Second layer in making sure the machine is connected to the Wi-Fi providing an internet connection
                cloud_2 = check_wifi_connection(internet_wifi)
                while cloud_2:
                    cloud_2 = connect_wifi(internet_wifi)
                    time.sleep(3)

                else:
                    # After DRIVING:
                    max_retries = 5
                    attempts = 0
                    while attempts < max_retries:
                        upload_response = upload_drowsiness_events_to_db(secret_key)
                        if upload_response == 'ok kayo':
                            # PRINT
                            with open('local_drowsiness_events.csv', 'r') as file:
                                for line in file:
                                    print(line, end='')
                            print("First_Print^________________________________")
                            # ERASE
                            with open('local_drowsiness_events.csv', 'w') as file:
                                file.truncate()
                            print("Erase^______________________________________")
                            # PRINT
                            with open('local_drowsiness_events.csv', 'r') as file:
                                for line in file:
                                    print(line, end='')
                            print("Second_Print^_______________________________")
                            break  # Exit the loop if upload is successful
                        else:
                            attempts += 1
                            print(f'Upload failed. Attempt {attempts} of {max_retries}. Retrying...')
                            time.sleep(3)  # Wait for 3 seconds before trying again
                    if attempts == max_retries:
                        print('Maximum upload attempts reached. Please try again later.')
                break

        cap.release()
        cv2.destroyAllWindows()
    except Exception as e:
        print(e)


class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        # Set window icon
        self.setWindowIcon(QIcon('hat.ico'))
        self.setWindowTitle("Sign In")
        self.setFixedWidth(400)
        self.setFixedHeight(600)
        self.setStyleSheet(
            "background-color: #1c1c1c; color: #fff;"
            "font-family: 'Segoe UI', sans-serif;"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        # Logo
        logo_label = QtWidgets.QLabel(self)
        logo_pixmap = QPixmap("rudder.png")
        logo_label.setPixmap(logo_pixmap.scaledToWidth(200))
        layout.addWidget(logo_label, alignment=Qt.AlignCenter)

        # Secret Key Field
        self.key_field = QtWidgets.QLineEdit()
        self.key_field.setPlaceholderText("Secret Key")
        self.key_field.setStyleSheet(
            "border: 2px solid #888; padding: 10px;"
            "background-color: #fff; color: #333; font-size: 16px;"
            "border-radius: 5px;"
        )
        layout.addWidget(self.key_field)

        # Login Button
        self.login_btn = QtWidgets.QPushButton("Sign In")
        self.login_btn.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        self.login_btn.setStyleSheet(
            "background-color: #1c1c1c; color: #fff; font-size: 16px;"
            "padding: 10px 30px; border: 2px solid #fff; border-radius: 5px; margin-top: 20px;"
        )
        self.login_btn.clicked.connect(self.login)
        layout.addWidget(self.login_btn, alignment=Qt.AlignCenter)

        # Message Area
        self.message_label = QtWidgets.QLabel("")
        self.message_label.setStyleSheet(
            "color: red; font-size: 16px; margin-top: 20px;"
        )
        layout.addWidget(self.message_label, alignment=Qt.AlignCenter)
        layout.addStretch()  # Add flexible space at the bottom

    def login(self):
        try:

            # Fetch the secret key from the user input
            global secret_key
            secret_key = 'secret'
            secret_key = self.key_field.text()

            # Connect to your Post_SQL database
            conn = psycopg2.connect(
                dbname="miamorko23",
                user="miamorko23_user",
                password="jsUL6Rbb6Ce1ZTopxZUtHO2hylVQIFA5",
                host="dpg-ckn0mf91rp3c73epu630-a.singapore-postgres.render.com",
                port="5432"
            )

            # Create a cursor object
            cur = conn.cursor()
            # Execute a query to fetch the user
            cur.execute("SELECT secret_key FROM main_userwithkey WHERE secret_key = %s", (secret_key,))
            # Fetch the result
            user = cur.fetchone()

            # If a match is found in the database
            if user is not None:
                self.login_btn.setStyleSheet(
                    "background-color: green; color: #fff; font-size: 16px;"
                    "padding: 10px 30px; border-radius: 5px; margin-top: 20px;"
                )
                self.clear_fields()
                self.close()
                cur.close()
                conn.close()
                sea()
            else:
                self.login_btn.setStyleSheet(
                    "background-color: red; color: #fff; font-size: 16px;"
                    "padding: 10px 30px; border-radius: 5px; margin-top: 20px;"
                )
                self.clear_fields()

            # Close the cursor and connection
            cur.close()
            conn.close()

        except Exception as r:
            print(r)

    def clear_fields(self):
        self.key_field.clear()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")  # Apply Fusion style
    app_icon = QIcon("skull.png")
    app.setWindowIcon(app_icon)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())

# c52b429a83a2ae595c0ae492eb88f001
