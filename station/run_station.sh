#! /bin/sh
# /etc/init.d/run_station.sh
#

### BEGIN INIT INFO
# Provides: /root/station/beacon_scanner.py
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
      python /root/station/beacon_scanner.py&
      echo "Starting scanner"
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
