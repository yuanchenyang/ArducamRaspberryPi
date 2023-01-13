from ast import Try
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QApplication, QWidget
from picamera2 import Picamera2
from PyQt5.QtGui import QImage,QPixmap
from PyQt5.QtCore import QThread
import RPi.GPIO as gp
import time
import os
import argparse
from datetime import datetime

SCALE = 60
WIDTH = 4*SCALE
HEIGHT = 3*SCALE

cameras = "ABCD"
adapter_info = {
    "A" : {
        "i2c_cmd":"i2cset -y 10 0x70 0x00 0x04",
        "gpio_sta":[0,0,1],
    }, "B" : {
        "i2c_cmd":"i2cset -y 10 0x70 0x00 0x05",
        "gpio_sta":[1,0,1],
    }, "C" : {
        "i2c_cmd":"i2cset -y 10 0x70 0x00 0x06",
        "gpio_sta":[0,1,0],
    },"D" : {
        "i2c_cmd":"i2cset -y 10 0x70 0x00 0x07",
        "gpio_sta":[1,1,0],
    }
}

class WorkThread(QThread):

    def __init__(self, capture_time=float('inf')):
        super(WorkThread,self).__init__()
        self.capture_time = capture_time # in seconds
        gp.setwarnings(False)
        gp.setmode(gp.BOARD)
        gp.setup(7, gp.OUT)
        gp.setup(11, gp.OUT)
        gp.setup(12, gp.OUT)

    def select_channel(self, index):
        channel_info = adapter_info.get(index)
        if channel_info == None:
            print("Can't get this info")
        gpio_sta = channel_info["gpio_sta"] # gpio write
        gp.output(7, gpio_sta[0])
        gp.output(11, gpio_sta[1])
        gp.output(12, gpio_sta[2])

    def init_i2c(self, index):
        channel_info = adapter_info.get(index)
        os.system(channel_info["i2c_cmd"]) # i2c write

    def run(self):
        global picam2
        # picam2 = Picamera2()
        # picam2.configure( picam2.still_configuration(main={"size": (320, 240),"format": "BGR888"},buffer_count=1))
        flag = False

        item = 'A'
        self.select_channel(item)
        self.init_i2c(item)
        time.sleep(0.5)
        picam2 = Picamera2()
        capture_config = picam2.create_still_configuration()
        preview_config = picam2.create_preview_configuration(
            main={"size": (WIDTH, HEIGHT),"format": "BGR888"}, buffer_count=2
        )
        picam2.configure(preview_config)
        picam2.start(show_preview=True)
        time.sleep(1)

        prev_time, cur_time = time.time(), time.time()
        while True:
            cur_time = time.time()
            if cur_time - prev_time > self.capture_time:
                for item in cameras:
                    self.select_channel(item)
                    time.sleep(0.1)
                    #picam2.configure(capture_config)
                    filename = f"capture_{item}_{datetime.now().isoformat()}.jpg"
                    picam2.switch_mode_and_capture_file(capture_config, filename)
                    #picam2.configure(preview_config)
                    time.sleep(0.5)
                prev_time = cur_time
            for item in cameras:
                self.select_channel(item)
                time.sleep(0.02)
                try:
                    buf = picam2.capture_array()
                    buf = picam2.capture_array()
                    cvimg = QImage(buf, WIDTH, HEIGHT, QImage.Format_RGB888)
                    pixmap = QPixmap(cvimg)
                    image_label[item].setPixmap(pixmap)
                except Exception as e:
                    print("capture_buffer: "+ str(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture_time', type=float, default=float('inf'))
    args = parser.parse_args()

    app = QApplication([])
    window = QWidget()
    layout_h = QHBoxLayout()
    layout_h2 = QHBoxLayout()
    layout_v = QVBoxLayout()

    image_label = dict(A=QLabel(),
                       B=QLabel(),
                       C=QLabel(),
                       D=QLabel())
    # picam2 = Picamera2()

    work = WorkThread(args.capture_time)

    for label in image_label.values():
        label.setFixedSize(WIDTH, HEIGHT)
    window.setWindowTitle("Qt Picamera2 Arducam Multi Camera Demo")
    layout_h.addWidget(image_label['A'])
    layout_h.addWidget(image_label['B'])
    layout_h2.addWidget(image_label['C'])
    layout_h2.addWidget(image_label['D'])
    layout_v.addLayout(layout_h, 20)
    layout_v.addLayout(layout_h2, 20)
    window.setLayout(layout_v)
    window.resize(WIDTH*2+20, HEIGHT*2+20)
    work.start()

    window.show()
    app.exec()
    work.quit()
    picam2.close()
