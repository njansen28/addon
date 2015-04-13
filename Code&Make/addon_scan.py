import subprocess
import threading
import requests
# import getpass
import signal
import json
import sys
import os
import time
import Adafruit_BBIO.GPIO as GPIO

from constants import *

countdown = 5


class BeaconScanner:
    def __init__(self):
        # start scan and dump processes, don't show scan output
        # TODO: catch errors of hcitool
        # password = getpass.getpass()
        # make sure hci0 is up
        #"sudo hciconfig hci0 down".split(" ")
        "sudo hciconfig hci0 up".split(" ")
        scanargs = "sudo hcitool lescan --duplicates".split(" ")
        dumpargs = "sudo hcidump -x -R -i hci0".split(" ")
        devnull = open(os.devnull, 'wb')
        self.scan = subprocess.Popen(scanargs, stdin=subprocess.PIPE, stdout=devnull)
        # self.scan.stdin.write(password + '\n')
        # self.scan.stdin.close()
        self.dump = subprocess.Popen(dumpargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.search_uuid = ""#"33333333333333333333333333333333"
        #self.settings_dict = {}
        self.uuid_lock = threading.Lock()
        #self.settings_lock = threading.Lock()
        #self.settings_last_updated = None
        #self.id = None
        # Setup pins
        GPIO.setup("P8_13", GPIO.OUT)
        GPIO.setup("P8_14", GPIO.OUT)
        GPIO.setup("P8_15", GPIO.OUT)
        GPIO.setup("P8_16", GPIO.OUT)
        GPIO.setup("P8_17", GPIO.OUT)
        GPIO.setup("P8_18", GPIO.OUT)
        GPIO.setup("P9_12", GPIO.OUT)
        GPIO.setup("P8_26", GPIO.IN)
        GPIO.setup("P9_14", GPIO.IN)
        

        # kill processes on exiting of program
        def signal_handler(signal, frame):
            print('You pressed Ctrl+C!')
            os.killpg(self.scan.pid, signal.SIGTERM)
            os.killpg(self.dump.pid, signal.SIGTERM)
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)

        # start new threads to receive packets,
        # send packets, and update settings
        rp_thread = threading.Thread(target=self.receive_packets, args=())
        wd_thread = threading.Thread(target=self.watch_dog, args=())
        #us_thread = threading.Thread(target=self.update_settings, args=())
        #ui_thread = threading.Thread(target=self.update_id, args=())
        rp_thread.start()
        wd_thread.start()
        #us_thread.start()
        #ui_thread.start()

    def watch_dog(self):
        global countdown
       # print("running watchdog")
        while(1) :
            self.uuid_lock.acquire()
            if (countdown != 0) :
                countdown = countdown - 1
            if (countdown == 0) :
                GPIO.output("P8_18", GPIO.LOW)
                GPIO.output("P8_17", GPIO.LOW)
                GPIO.output("P8_16", GPIO.LOW)
                GPIO.output("P8_15", GPIO.LOW)
                GPIO.output("P8_14", GPIO.LOW)
                GPIO.output("P9_12", GPIO.LOW)
            self.uuid_lock.release()
            print("countdown: {}".format(countdown))
            time.sleep(0.1)
        
    def set_search_uuid(self, uuid):
        self.search_uuid = uuid
		
    def get_search_uuid(self):
        return self.search_uuid

    def receive_packets(self):
        global countdown
        cur_packet = ""
        #rssi value will be average of last 3
        #init to -70
        rssi1 = -70
        rssi2 = -70
        rssi3 = -70
        rssi4 = -70
        rssi5 = -70
        try:
            for line in iter(self.dump.stdout.readline, b''):
                #Test Button
                if (GPIO.input("P9_14") == GPIO.HIGH) :
                    print("input is high")
                    GPIO.output("P8_13", GPIO.HIGH)
                    GPIO.output("P8_14", GPIO.HIGH)
                    GPIO.output("P8_15", GPIO.HIGH)
                    GPIO.output("P8_16", GPIO.HIGH)
                    GPIO.output("P8_17", GPIO.HIGH)
                    GPIO.output("P8_18", GPIO.HIGH)
                    GPIO.output("P9_12", GPIO.HIGH)
                #else :
                 #   GPIO.output("P8_13", GPIO.HIGH)
                  #  GPIO.output("P8_14", GPIO.HIGH)
                   # GPIO.output("P8_15", GPIO.HIGH)
                    #GPIO.output("P8_16", GPIO.HIGH)
                    #GPIO.output("P8_17", GPIO.HIGH)
                    #GPIO.output("P8_18", GPIO.HIGH)
                    #GPIO.output("P9_12", GPIO.HIGH)
                elif (self.get_search_uuid() == "") :
                    GPIO.output("P8_13", GPIO.LOW)
                if (GPIO.input("P8_26") == GPIO.HIGH) :
                    GPIO.output("P8_13", GPIO.LOW) # current status is not searching
                    self.set_search_uuid("")
                    GPIO.output("P8_18", GPIO.LOW)
                    GPIO.output("P8_17", GPIO.LOW)
                    GPIO.output("P8_16", GPIO.LOW)
                    GPIO.output("P8_15", GPIO.LOW)
                    GPIO.output("P8_14", GPIO.LOW)
                    GPIO.output("P9_12", GPIO.LOW)
                #    print("P8_7: {}".format(GPIO.input("P8_26"))
                #else:
                #    print("P8_7: {}".format(GPIO.input("P8_26"))
                # check if new packet as packet is split into multiple lines
                if line[0] is ">":
                    # print(">>> " + cur_packet)
                    # check for ibeacon advertisement
                    # http://www.warski.org/blog/2014/01/how-ibeacons-work/
                    send_param_header = "1E 02 01 06 1A FF 00 00 AB AB"
                    index = cur_packet.find(send_param_header)
                    if index != -1:
                        uuid_start = index + len(send_param_header) + 1
                        # 47 is the length of the UUID
                        uuid_end = uuid_start + 47
                        # check if complete uuid is received
                        if uuid_end < len(cur_packet):
                            self.set_search_uuid(cur_packet[uuid_start:uuid_end].replace(" ", ""))
                            # last byte of packet contains RSSI information
                            rssi = int(cur_packet[-2:], 16) - 256
                            GPIO.output("P8_13", GPIO.HIGH) #searching for item now
                            print("Searching for UUID: {}, RSSI: {}".format(self.get_search_uuid(), rssi))
                    index = cur_packet.find(IBEACON_ID)
                    if index != -1:
                        uuid_start = index + len(IBEACON_ID) + 1
                        # 47 is the length of the UUID
                        uuid_end = uuid_start + 47
                        # check if complete uuid is received
                        if uuid_end < len(cur_packet):
                            uuid = cur_packet[uuid_start:uuid_end].replace(" ", "")
                            if uuid == self.get_search_uuid() :
                                # last byte of packet contains RSSI information
                                rssi1 = rssi2
                                rssi2 = rssi3
                                rssi3 = rssi4
                                rssi4 = rssi5
                                rssi5 = int(cur_packet[-2:], 16) - 256
                                rssi = (rssi1 + rssi2 + rssi3 +rssi4 + rssi5) / 5
                                # lock for thread safety
                                self.uuid_lock.acquire()
                                countdown = 5
                                # self.uuid_dict[uuid] = rssi
                                self.uuid_lock.release()
                                print("UUID: {}, RSSI: {}".format(uuid, rssi))
                                GPIO.output("P8_18", GPIO.HIGH)
                               # rssi = 0
                                if int(rssi) < -83:
                                    print("No LEDs are on right now")
                                    GPIO.output("P8_18", GPIO.LOW)
                                    GPIO.output("P8_17", GPIO.LOW)
                                    GPIO.output("P8_16", GPIO.LOW)
                                    GPIO.output("P8_15", GPIO.LOW)
                                    GPIO.output("P8_14", GPIO.LOW)
                                    GPIO.output("P9_12", GPIO.LOW)
                                elif int(rssi) < -77:
                                    print("First LED is on")
                                    GPIO.output("P8_18", GPIO.HIGH)
                                    GPIO.output("P8_17", GPIO.LOW)
                                    GPIO.output("P8_16", GPIO.LOW)
                                    GPIO.output("P8_15", GPIO.LOW)
                                    GPIO.output("P8_14", GPIO.LOW)
                                    GPIO.output("P9_12", GPIO.LOW)
                                elif int(rssi) < -72:
                                    print("Two are on")
                                    GPIO.output("P8_18", GPIO.HIGH)
                                    GPIO.output("P8_17", GPIO.HIGH)
                                    GPIO.output("P8_16", GPIO.LOW)
                                    GPIO.output("P8_15", GPIO.LOW)
                                    GPIO.output("P8_14", GPIO.LOW)
                                    GPIO.output("P9_12", GPIO.LOW)
                                elif int(rssi) < -68:
                                    print("Three are on")
                                    GPIO.output("P8_18", GPIO.HIGH)
                                    GPIO.output("P8_17", GPIO.HIGH)
                                    GPIO.output("P8_16", GPIO.HIGH)
                                    GPIO.output("P8_15", GPIO.LOW)
                                    GPIO.output("P8_14", GPIO.LOW)
                                    GPIO.output("P9_12", GPIO.LOW)
                                elif int(rssi) < -65:
                                    print("Four are on")
                                    GPIO.output("P8_18", GPIO.HIGH)
                                    GPIO.output("P8_17", GPIO.HIGH)
                                    GPIO.output("P8_16", GPIO.HIGH)
                                    GPIO.output("P8_15", GPIO.HIGH)
                                    GPIO.output("P8_14", GPIO.LOW)
                                    GPIO.output("P9_12", GPIO.LOW)
                                elif int(rssi) < -63:
                                    print("Five are on")
                                    GPIO.output("P8_18", GPIO.HIGH)
                                    GPIO.output("P8_17", GPIO.HIGH)
                                    GPIO.output("P8_16", GPIO.HIGH)
                                    GPIO.output("P8_15", GPIO.HIGH)
                                    GPIO.output("P8_14", GPIO.HIGH)
                                    GPIO.output("P9_12", GPIO.LOW)
                                else:
                                    print("BUZZZZZZZZ")
                                    GPIO.output("P8_18", GPIO.HIGH)
                                    GPIO.output("P8_17", GPIO.HIGH)
                                    GPIO.output("P8_16", GPIO.HIGH)
                                    GPIO.output("P8_15", GPIO.HIGH)
                                    GPIO.output("P8_14", GPIO.HIGH)
                                    GPIO.output("P9_12", GPIO.HIGH)
                            else :
                                print("detectedUUID: {}, searchingForUUID: {}".format(uuid, self.get_search_uuid()))
                    # start tracking of new packet
                    cur_packet = line.strip()
                    continue
                else:
                    cur_packet += " " + line.strip()
        finally:
            #os.killpg(self.scan.pid, signal.SIGTERM)
            #os.killpg(self.dump.pid, signal.SIGTERM)
            print("exiting...")

    # def send_packets(self):
        # threading.Timer(SEND_PACKET_PERIOD, self.send_packets).start()
        # try:
            # dump received packets and send them to webserver
            # json_dict = json.dumps(self.uuid_dict)
            # self.uuid_lock.acquire()
            # data = {'data': json.dumps(self.uuid_dict)}
            # if self.id is None:
                # data = {'data': json_dict}
            # else:
                # data = {'id': self.id, 'data': json_dict}
            # clear dict after sending to ensure fresh values
            # self.uuid_dict.clear()
            # self.uuid_lock.release()
            # print "POST data: " + str(data)
            # requests.post(WEBSERVER_IP + '/newData', data=data)
        # except Exception as e:
            # print "Unable to post data: " + str(e)

##    def update_settings(self):
##        threading.Timer(UPDATE_SETTINGS_PERIOD, self.update_settings).start()
##        try:
##            # no need to update settings if the file has not changed
##            statbuf = os.stat(SETTINGS_FILENAME)
##            if statbuf.st_mtime == self.settings_last_updated:
##                return
##
##            # read settings from file and update the dict
##            f = open(SETTINGS_FILENAME, 'r', os.O_NONBLOCK)
##            settings = json.loads(f.read())
##            self.settings_lock.acquire()
##            self.settings_dict = settings
##            self.settings_lock.release()
##            print "New settings: " + str(self.settings_dict)
##            self.settings_last_updated = statbuf.st_mtime
##        except Exception as e:
##            print "Unable to load settings: " + str(e)
##
##    def update_id(self):
##        # no need to update settings if there is an ID
##        if self.id is not None:
##            return
##
##        threading.Timer(UPDATE_SETTINGS_PERIOD, self.update_id).start()
##        try:
##            # read ID from file and update the ID variable
##            f = open(ID_FILENAME, 'r', os.O_NONBLOCK)
##            id_object = json.loads(f.read())
##            self.id = id_object['id']
##            print "New ID: " + str(self.id)
##        except Exception as e:
##            print "Unable to load ID: " + str(e)

##    def get_setting(self, key):
##        # safely get setting with locking
##        self.settings_lock.acquire()
##        setting = self.settings_dict.get(key)
##        self.settings_lock.release()
##        if setting is None:
##            print "Setting {} does not exist!".format(key)
##            return None
##        else:
##            return setting


BeaconScanner()
