# sea imports
import psycopg2
from scipy.spatial import distance
from imutils import face_utils
from pygame import mixer
import imutils
import dlib
import cv2
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import requests
import subprocess

import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QCursor, QPixmap, QIcon
from PyQt5.QtCore import Qt


def check_wifi_connection(ssid):
    try:
        output = subprocess.check_output(["netsh", "wlan", "show", "interface"])
        output = output.decode("utf-8")
        return ssid in output
    except subprocess.CalledProcessError:
        return False


wifi_name = 'SeaMern'
is_connected = check_wifi_connection(wifi_name)
if is_connected:
    pass
else:
    print('~N~')
    # sys.exit(0)


def sea():
    try:
        # Set the ESP8266 IP address
        esp8266_ip = "192.168.4.1"

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current_volume_db = volume.GetMasterVolumeLevel()
        if current_volume_db != -20.461252212524414:
            volume.SetMasterVolumeLevel(-20.461252212524414, None)

        # Define the coordinates for displaying the text on the screen
        text_coordinates = (23, 300)
        text_font = cv2.FONT_HERSHEY_SIMPLEX
        text_scale = 0.7
        text_color = (0, 255, 0)
        text_thickness = 2

        mixer.init()
        mixer.music.load("partial.mp3")

        def eye_aspect_ratio(eye):
            a = distance.euclidean(eye[1], eye[5])
            b = distance.euclidean(eye[2], eye[4])
            c = distance.euclidean(eye[0], eye[3])
            the_long_gun = (a + b) / (2.0 * c)
            return the_long_gun

        thresh = 0.25
        frame_check = 10
        detect = dlib.get_frontal_face_detector()
        predict = dlib.shape_predictor("68FaceLandmarks.dat")

        (lStart, lEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
        (rStart, rEnd) = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]

        cap = cv2.VideoCapture(0)
        flag = 0

        leftEye = ""
        rightEye = ""

        cnt = 0
        status = ''
        hp = 0
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

                if ear < thresh:
                    flag += 1
                    if flag >= frame_check:
                        text_color = (0, 0, 255)
                        cv2.putText(frame, "EYE CLOSED", text_coordinates, text_font, text_scale, text_color,
                                    text_thickness)

                        if cnt >= 3 and not mixer.music.get_busy():
                            mixer.music.load("final.mp3")
                            mixer.music.play()
                            status = 'Hercules'
                            # This is where the Arduino Uno comes in
                            requests.get(f"http://{esp8266_ip}/ledon")
                        if not mixer.music.get_busy():
                            mixer.music.play()
                            cnt += 1
                            if status == 'Hercules':
                                hp = 0

                else:
                    hi = 'hi'
                    sky = 'sky'
                    if cnt >= 2 and status != 'Hercules':
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

                    flag = 0
                    if sky == 'sky' or hi == 'hello':
                        cnt = 0
                    cv2.putText(frame, "AWAKE", text_coordinates, text_font, text_scale, text_color, text_thickness)

            if cnt >= 3:
                volume.SetMasterVolumeLevel(current_volume_db + 20.4, None)

            # Draw squares around the eyes
            left_eye_rect = cv2.boundingRect(leftEye)
            right_eye_rect = cv2.boundingRect(rightEye)
            cv2.rectangle(frame, left_eye_rect, text_color, text_thickness)
            cv2.rectangle(frame, right_eye_rect, text_color, text_thickness)
            text_color = (0, 255, 0)
            cv2.imshow("DROWSINESS DETECTOR", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("z"):
                break

        cv2.destroyAllWindows()
        cap.release()

    except Exeption as pt:
        print(pt)
        sys.exit(0)


class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Realm")
        self.setFixedWidth(400)
        self.setFixedHeight(600)
        self.setStyleSheet(
            "background-color: #222; color: #fff;"
            "font-family: 'Segoe UI', sans-serif;"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        # Heading
        heading_label = QtWidgets.QLabel("Sign In")
        heading_label.setStyleSheet(
            "font-size: 30px; font-weight: bold; margin: 20px 0;"
        )
        layout.addWidget(heading_label, alignment=Qt.AlignCenter)

        # Username Field
        self.user_field = QtWidgets.QLineEdit()
        self.user_field.setPlaceholderText("Username")
        self.user_field.setStyleSheet(
            "border: none; border-bottom: 2px solid #888; padding: 10px;"
            "background-color: transparent; color: #fff; font-size: 16px;"
        )
        layout.addWidget(self.user_field)

        # Password Field
        self.pass_field = QtWidgets.QLineEdit()
        self.pass_field.setPlaceholderText("Password")
        self.pass_field.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pass_field.setStyleSheet(
            "border: none; border-bottom: 2px solid #888; padding: 10px;"
            "background-color: transparent; color: #fff; font-size: 16px;"
        )
        layout.addWidget(self.pass_field)

        # Login Button
        self.login_btn = QtWidgets.QPushButton("Log In")
        self.login_btn.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        self.login_btn.setStyleSheet(
            "background-color: #00a8ff; color: #fff; font-size: 16px;"
            "padding: 10px 30px; border-radius: 5px; margin-top: 20px;"
        )
        self.login_btn.clicked.connect(self.login)
        layout.addWidget(self.login_btn, alignment=Qt.AlignCenter)

        # Image
        image_label = QtWidgets.QLabel(self)
        image_pixmap = QPixmap("chest.png")
        image_label.setPixmap(image_pixmap.scaledToWidth(200))
        layout.addWidget(image_label, alignment=Qt.AlignCenter)

        layout.addStretch()  # Add flexible space at the bottom

    def login(self):
        username = self.user_field.text()
        password = self.pass_field.text()

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

        # Execute a query to check the username and password
        cur.execute("SELECT * FROM auth_user WHERE username = %s OR password = %s", (username, password))

        # If a match is found in the database
        if cur.fetchone() is not None:
            self.login_btn.setStyleSheet(
                "background-color: green; color: #fff; font-size: 16px;"
                "padding: 10px 30px; border-radius: 5px; margin-top: 20px;"
            )
            self.clear_fields()
            self.close()
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

    def clear_fields(self):
        self.user_field.clear()
        self.pass_field.clear()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")  # Apply Fusion style
    app_icon = QIcon("skull.png")
    app.setWindowIcon(app_icon)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
