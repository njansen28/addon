import subprocess
import threading
import requests
# import getpass
import signal
import json
import sys
import os

from constants import *


class BeaconScanner:
    def __init__(self):
        # start scan and dump processes, don't show scan output
        # TODO: catch errors of hcitool
        # password = getpass.getpass()
        scanargs = "sudo hcitool lescan --duplicates".split(" ")
        dumpargs = "sudo hcidump -x -R -i hci1".split(" ")
        devnull = open(os.devnull, 'wb')
        self.scan = subprocess.Popen(scanargs, stdin=subprocess.PIPE, stdout=devnull)
        # self.scan.stdin.write(password + '\n')
        # self.scan.stdin.close()
        self.dump = subprocess.Popen(dumpargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.search_uuid = "11111111111111111111111111111111"
        self.settings_dict = {}
        self.uuid_lock = threading.Lock()
        self.settings_lock = threading.Lock()
        self.settings_last_updated = None
        self.id = None

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
        sp_thread = threading.Thread(target=self.send_packets, args=())
        us_thread = threading.Thread(target=self.update_settings, args=())
        ui_thread = threading.Thread(target=self.update_id, args=())
        rp_thread.start()
        sp_thread.start()
        us_thread.start()
        ui_thread.start()

	def set_search_uuid(self, uuid)
		self.search_uuid = uuid
		
    def get_search_uuid(self):
        return self.search_uuid

    def receive_packets(self):
        cur_packet = ""
        try:
            for line in iter(self.dump.stdout.readline, b''):
                # check if new packet as packet is split into multiple lines
                if line[0] is ">":
                    # print(">>> " + cur_packet)
                    # check for ibeacon advertisement
                    # http://www.warski.org/blog/2014/01/how-ibeacons-work/
                    index = cur_packet.find(IBEACON_ID)
                    if index != -1:
                        uuid_start = index + len(IBEACON_ID) + 1
                        # 47 is the length of the UUID
                        uuid_end = uuid_start + 47
                        # check if complete uuid is received
                        if uuid_end < len(cur_packet):
                            uuid = cur_packet[uuid_start:uuid_end].replace(" ", "")
                            # last byte of packet contains RSSI information
                            rssi = int(cur_packet[-2:], 16) - 256
                            # lock for thread safety
                            self.uuid_lock.acquire()
                            self.uuid_dict[uuid] = rssi
                            self.uuid_lock.release()
							if uuid == get_search_uuid(self) :
								print("UUID: {}, RSSI: {}".format(uuid, rssi))
								if int(rssi) < -90:
									print("No LEDs are on right now")
								elif int(rssi) < -80:
									print("First LED is on")
								elif int(rssi) < -70:
									print("Two are on")
								elif int(rssi) < -60:
									print("Three are on")	
								elif int(rssi) < -50:
									print("Four are on")
								elif int(rssi) < -40:
									print("Five are on")
								else
									print("BUZZZZZZZZ")
                    # start tracking of new packet
                    cur_packet = line.strip()
                    continue
                else:
                    cur_packet += " " + line.strip()
        finally:
            os.killpg(self.scan.pid, signal.SIGTERM)
            os.killpg(self.dump.pid, signal.SIGTERM)
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

    def update_settings(self):
        threading.Timer(UPDATE_SETTINGS_PERIOD, self.update_settings).start()
        try:
            # no need to update settings if the file has not changed
            statbuf = os.stat(SETTINGS_FILENAME)
            if statbuf.st_mtime == self.settings_last_updated:
                return

            # read settings from file and update the dict
            f = open(SETTINGS_FILENAME, 'r', os.O_NONBLOCK)
            settings = json.loads(f.read())
            self.settings_lock.acquire()
            self.settings_dict = settings
            self.settings_lock.release()
            print "New settings: " + str(self.settings_dict)
            self.settings_last_updated = statbuf.st_mtime
        except Exception as e:
            print "Unable to load settings: " + str(e)

    def update_id(self):
        # no need to update settings if there is an ID
        if self.id is not None:
            return

        threading.Timer(UPDATE_SETTINGS_PERIOD, self.update_id).start()
        try:
            # read ID from file and update the ID variable
            f = open(ID_FILENAME, 'r', os.O_NONBLOCK)
            id_object = json.loads(f.read())
            self.id = id_object['id']
            print "New ID: " + str(self.id)
        except Exception as e:
            print "Unable to load ID: " + str(e)

    def get_setting(self, key):
        # safely get setting with locking
        self.settings_lock.acquire()
        setting = self.settings_dict.get(key)
        self.settings_lock.release()
        if setting is None:
            print "Setting {} does not exist!".format(key)
            return None
        else:
            return setting


BeaconScanner()