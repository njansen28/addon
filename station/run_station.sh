#! /bin/sh
# /etc/init.d/run_station.sh
#

### BEGIN INIT INFO
# Provides: /root/station/addon_scan.py /root/station/server.py
# Required-Start: 
# Required-Stop:  
# Should-Start: 
# Should-Stop: 
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Start and stop directadmin
# Description: run station
### END INIT INFO

case "$1" in
    start)
      hciconfig hci0 up
      ifconfig wlan0 up
      python /root/station/beacon_scanner.py
      python /root/station/server.py
      echo "Starting add on"
      ;;
    stop)
      echo "Naaaaaaaaawwwwwww. not starting server/scanner"
      ;;
    *)
      echo "Usage: /etc/init.d/foobar {start|stop}"
      exit 1
      ;;
esac

exit 0

