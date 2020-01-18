boot_py = r'''
#! Write PASS
from machine import Timer
from machine import I2C
import touchscreen as ts
from Maix import I2S, GPIO
from machine import UART
import sensor
import image
import time
import lcd
import utime
from fpioa_manager import *
import audio

BACKLIGHT_PIN_NUM = 17
BACKLIGHT_FPIOA = fm.fpioa.GPIO0
BACKLIGHT_GPIO = GPIO.GPIO0

LED_PIN_NUM = 22
LED_FPIOA = fm.fpioa.GPIO1
LED_GPIO = GPIO.GPIO1

BOOT_PIN_NUM = 16
BOOT_FPIOA = fm.fpioa.GPIO2
BOOT_GPIO = GPIO.GPIO2

PIR_PIN_NUM = 23
PIR_FPIOA = fm.fpioa.GPIOHS0
PIR_GPIO = GPIO.GPIOHS0

class LilyGO():
    def __init__(self):
        fm.register(BACKLIGHT_PIN_NUM, BACKLIGHT_FPIOA)
        self.bl = GPIO(BACKLIGHT_GPIO, GPIO.OUT)
        self.bl.value(1)

        fm.register(LED_PIN_NUM, LED_FPIOA)
        self.led = GPIO(LED_GPIO, GPIO.OUT)

        self.led.value(0)
        time.sleep(0.5)
        self.led.value(1)
        time.sleep(0.5)
        self.led.value(0)
        time.sleep(0.5)
        self.led.value(1)
        # time.sleep(0.5)
        # self.led.value(0)

        fm.register(PIR_PIN_NUM, PIR_FPIOA)
        self.pir = GPIO(PIR_GPIO, GPIO.IN)
        self.pir.irq(self.pirIRQ, GPIO.IRQ_RISING, GPIO.WAKEUP_NOT_SUPPORT, 7)

        fm.register(BOOT_PIN_NUM, BOOT_FPIOA)
        self.button = GPIO(BOOT_GPIO, GPIO.IN)

        #! Uart
        fm.register(6, fm.fpioa.UART1_TX)
        fm.register(7, fm.fpioa.UART1_RX)
        self.serial = UART(UART.UART1, 115200, 8, None, 1,
                           timeout=1000, read_buf_len=4096)

        #! Audio
        fm.register(34, fm.fpioa.I2S2_OUT_D1)
        fm.register(35, fm.fpioa.I2S2_SCLK)
        fm.register(33, fm.fpioa.I2S2_WS)
        self.audioDev = I2S(I2S.DEVICE_2)
        self.audioDev.channel_config(self.audioDev.CHANNEL_1, I2S.TRANSMITTER, resolution=I2S.RESOLUTION_16_BIT,
                                     cycles=I2S.SCLK_CYCLES_32, align_mode=I2S.LEFT_JUSTIFYING_MODE)
        self.audioDev.set_sample_rate(44*1000)
        self.player = None

        #! Mic
        fm.register(20, fm.fpioa.I2S0_IN_D0)
        fm.register(19, fm.fpioa.I2S0_WS)
        fm.register(18, fm.fpioa.I2S0_SCLK)
        self.mic = I2S(I2S.DEVICE_0)

        self.mic.channel_config(self.mic.CHANNEL_0, self.mic.RECEIVER,
                                align_mode=I2S.LEFT_JUSTIFYING_MODE)
        self.mic.set_sample_rate(44*1000)

        #! LCD
        lcd.init(freq=15000000)
        lcd.rotation(1)
        lcd.clear(lcd.BLACK)

        self.x = 0
        self.y = 0

        dev = os.listdir('/')
        if 'sd' in dev:
            self.showInfo("find the sdcard", True)
            print('find the sdcard')
        else:
            self.showInfo("sdcard not the found", False)
            print('sdcard not the found')

        # self.startAudio()
        self.startNewwork()
        self.startTouchpad()
        self.startCamera()

    def pirIRQ(self, GPIO):
        val = not self.led.value()
        self.led.value(val)

    def startNewwork(self):
        start = utime.ticks_ms()
        self.serial.write('at\r\n')
        while True:
            data = self.serial.read()
            if data is not None:
                print(data)
                self.showInfo("esp32 respone is OK", True)
                return
            if utime.ticks_ms() > 3000:
                self.showInfo("esp32 no respone", False)
                return

    def showInfo(self, string, done):
        if done:
            lcd.draw_string(self.x, self.y, string,
                            lcd.GREEN, lcd.BLACK)
        else:
            lcd.draw_string(
                self.x, self.y, string, lcd.RED, lcd.BLACK)
        self.y = self.y + 16
        if self.y > 240:
            self.y = 0
            lcd.clear(lcd.BLACK)

    def buttonIsPressed(self):
        return self.button.value() == 0

    def startTouchpad(self):
        i2c = I2C(I2C.I2C0, freq=400000, scl=30, sda=31)
        i2cdev = i2c.scan()
        print(i2cdev)
        if 53 in i2cdev:
            print('find axp202')
            self.showInfo("find axp202", True)
        else:
            self.showInfo("axp202  not the found", False)

        if 56 in i2cdev:
            print('find ft6236')
            self.showInfo("find ft6236", True)
        else:
            self.showInfo("ft6236 not the found", False)

        if 81 in i2cdev:
            self.showInfo("find mpu6050", True)
            print('find pcf8563')
        else:
            self.showInfo("mpu6050 not the found", False)

        if 104 in i2cdev:
            print('find mpu6050')
            self.showInfo("find mpu6050", True)
        else:
            self.showInfo("mpu6050 init failed", False)

        try:
            ts.init(i2c, ts.FT62XX)
        except:
            print('faile to init touchpad')
            self.showInfo("touchpad init failed", False)
        else:
            self.showInfo("touchpad init done", True)
            print('pass to init touchpad')

    def startCamera(self):
        try:
            sensor.reset()
            sensor.set_pixformat(sensor.RGB565)
            sensor.set_framesize(sensor.QVGA)
            sensor.skip_frames(time=2000)
        except:
            print('faile to init camera')
            self.showInfo("camera init failed", False)
        else:
            print('pass to init camera')
            self.showInfo("camera init done", True)

    def cameraRun(self):
        img = sensor.snapshot()
        lcd.display(img)

    def startMic(self):
        # sampling points number must be smaller than 256
        audio = self.mic.record(256)
        self.audioDev.play(audio)

    def startAudio(self):
        try:
            self.player = audio.Audio(path="/sd/play.wav")
        except:
            print('faile to init audio')
        else:
            print('pass to init audio')
            self.player.volume(20)
            wav_info = self.player.play_process(self.audioDev)
            self.audioDev.set_sample_rate(wav_info[1])
            while True:
                ret = self.player.play()
                if ret == None:
                    print("format error")
                    break
                elif ret == 0:
                    print("end")
                    break
            player.finish()
            pass

    def enableLED(self, en):
        self.led.value(en)

    def enableBackLight(self, en):
        self.bl.value(en)


m = LilyGO()
time.sleep(5)

lcd.clear(lcd.BLACK)
lcd.draw_string(0, 0, "Press button keep test ", lcd.GREEN, lcd.BLACK)
lcd.draw_string(0, 16, "camera", lcd.GREEN, lcd.BLACK)
while not m.buttonIsPressed():
    time.sleep_ms(100)


lcd.clear(lcd.BLACK)
time.sleep(1)
while not m.buttonIsPressed():
    img = sensor.snapshot()
    img.draw_string(0, 0, "Test Done", lcd.GREEN, scale=2)
    new = img.copy(roi=(0, 0, 239, 239))
    lcd.display(new)

lcd.clear(lcd.BLACK)
time.sleep(1)
lcd.draw_string(0, 0, "Press button keep test camera", lcd.GREEN, lcd.BLACK)
print('run mic audio')
while not m.buttonIsPressed():
    # m.startMic()
     m.startAudio()

while True:
    img = sensor.snapshot()
    img.draw_string(0, 0, "Test Done", lcd.GREEN, scale=2)
    new = img.copy(roi=(0, 0, 239, 239))
    lcd.display(new)
'''
import sys
# try:
#     f = open("/flash/boot.py", "r")
#     f.readline()
#     s = f.readline()
#     f.close()
#     if '#! Write PASS' in s:
#         with open("/flash/boot.py") as f:
#             exec(f.read())
# except:
#     print('failed open boot')



from fpioa_manager import *
import os, Maix, lcd, image
from Maix import FPIOA, GPIO

lcd.init(freq=15000000,color=(255,0,0))
fm.register(board_info.PIN17,fm.fpioa.GPIO0)
led=GPIO(GPIO.GPIO0,GPIO.OUT)
led.value(1)
lcd.rotation(1)
lcd.clear((255,0,0))


try:
    os.remove('/flash/boot.py')
except:
    pass
try:
    f = open("/flash/boot.py", "wb")
    f.write(boot_py)
    f.close()
except:
    lcd.draw_string(lcd.width()//2-68,lcd.height()//2-4, "Write boot.py failed", lcd.WHITE, lcd.BLACK)
else:
    lcd.draw_string(lcd.width()//2-68,lcd.height()//2-4, "Write boot.py pass", lcd.GREEN, lcd.BLACK)

with open("/flash/boot.py") as f:
    exec(f.read())
