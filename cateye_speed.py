from bluepy.btle import UUID, Scanner, DefaultDelegate, Peripheral
from bluepy import btle
import struct
import time
import os
import re
import subprocess
import RPi.GPIO as GPIO
import nmap
import cateye_speed_settings as settings


class YoutubePlayStop:
    def __init__(self):
        self.isPause = True
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(2, GPIO.OUT)

    def play(self):
        if self.isPause:
            os.system("adb shell input keyevent 126")
        self.isPause = False
        GPIO.output(2, GPIO.HIGH)

    def pause(self):
        if not self.isPause:
            os.system("adb shell input keyevent 127")
        self.isPause = True
        GPIO.output(2, GPIO.LOW)


youtube = YoutubePlayStop()


class ScanDelegate(DefaultDelegate):
    def __init__(self, speed_char_handle):
        DefaultDelegate.__init__(self)
        self.speed_char_handle = speed_char_handle
        self.wheel_events = []

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device:", dev.addr)

    def handleNotification(self, cHandle, data):
        if cHandle == self.speed_char_handle:
            # 速度計算
            wheel_data = (data[2] << 8) + data[1]
            if len(self.wheel_events) > 10:  # リストの長さが100を超えた場合は、最も古いデータを削除
                self.wheel_events.pop(0)
            if len(self.wheel_events) > 1:  # リストに2つ以上のデータがある場合は、速度を計算
                if wheel_data == self.wheel_events[-1]['wheel_data']:
                    self.wheel_events.pop(0)
                    youtube.pause()
                    return
                wheel_diff = self.wheel_events[-1]['wheel_data'] - self.wheel_events[0]['wheel_data']  # ホイール回転数の差分
                time_diff = self.wheel_events[-1]['event_time'] - self.wheel_events[0]['event_time']  # 時間の差分
                speed = settings.WHEEL_CIRCUMFERENCE * (wheel_diff / time_diff) * 3.6 / 1000
                if speed >= settings.SPEED_THRESHOLD:
                    youtube.play()
                else:
                    youtube.pause()
                print("Speedaa: {:.1f} km/h".format(speed))

            self.wheel_events.append({"wheel_data": wheel_data, "event_time": time.monotonic()})


def scan_for_cateye_device():
    scanner = btle.Scanner()
    devices = scanner.scan(5)
    for dev in devices:
        if dev.getValueText(9) is not None and "CATEYE" in dev.getValueText(9):
            return dev

    return None


def enable_notifications(peripheral, char_handle):
    cccd_handle = char_handle + 1
    peripheral.writeCharacteristic(cccd_handle, b"\x01\x00")


def get_ip_address_from_mac_address(target_mac):
    nm = nmap.PortScanner()
    nm.scan(hosts='192.168.0.0/24', arguments='-sP')

    for host in nm.all_hosts():
        if 'mac' in nm[host]['addresses']:
            if nm[host]['addresses']['mac'] == target_mac:
                return host

    return None


def adb_connect(ip_address):
    try:
        cmd = ["adb", "connect", "{}:5555".format(ip_address)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        return False


def is_adb_connect_device():
    try:
        cmd = "adb devices | grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}'"
        output = subprocess.check_output(cmd, shell=True)
        return bool(output)
    except:
        return False


def main():
    # ADB接続済みでなければ接続する
    if not is_adb_connect_device():
        # Fire Stick TV とADP接続する
        while True:
            # IPアドレスを探す
            print("find fire stick tv")
            fire_stick_ip_addr = get_ip_address_from_mac_address(settings.FIRE_STICK_TV_MAC_ADDRESS)
            print("fire stick tv found ip:", fire_stick_ip_addr)
            if fire_stick_ip_addr:
                break
        while True:
            # 見つけたIPアドレスでadb接続する
            if adb_connect(fire_stick_ip_addr):
                print("adb connect success ", fire_stick_ip_addr)
                break

    # CATEYEデバイスを探す
    cateye_device = None
    while cateye_device is None:
        print("Scanning for CATEYE device...")
        cateye_device = scan_for_cateye_device()
        if cateye_device is None:
            print("CATEYE device not found, waiting before trying again...")
            time.sleep(5)
    print("Cateye Strada Smart found:", cateye_device.addr)

    # CATEYEデバイスに接続
    while True:
        try:
            cateye_peripheral = Peripheral(cateye_device)
            break
        except:
            print("Device Connect error retry")

    # 速度デバイスのキャラクタリスティックハンドルを取得
    speed_char_handle = None
    services = cateye_peripheral.getServices()
    while speed_char_handle is None:
        for service in services:
            if service.uuid == settings.CSC_SERVICE_UUID:  # Cycling Speed and Cadence Service
                characteristics = service.getCharacteristics()
                for characteristic in characteristics:
                    if characteristic.uuid == settings.WHEEL_CHAR_UUID:  # CSC Measurement Characteristic
                        speed_char_handle = characteristic.getHandle()
                        break

    # 速度監視
    # 速度はScanDelegateへ通知される
    cateye_peripheral.setDelegate(ScanDelegate(speed_char_handle))
    enable_notifications(cateye_peripheral, speed_char_handle)
    while True:
        if cateye_peripheral.waitForNotifications(1.0):
            # 通知が処理されます
            continue
        print("Waiting for notifications...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        for i in range(3):
            GPIO.output(2, GPIO.HIGH)
            time.sleep(0.3)
            GPIO.output(2, GPIO.LOW)
            time.sleep(0.3)
        GPIO.cleanup()
