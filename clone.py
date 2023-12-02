import subprocess


def disconnect_wifi():
    subprocess.call('netsh wlan disconnect', shell=True)


def connect_wifi(network):
    subprocess.call(f'netsh wlan connect name="{network}"', shell=True)


# Disconnect from the current Wi-Fi
disconnect_wifi()
# Connect to a previously connected Wi-Fi
connect_wifi('*******P')
