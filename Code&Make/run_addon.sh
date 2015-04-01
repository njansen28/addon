#! /bin/sh
# /etc/init.d/run_addon.sh
#

### BEGIN INIT INFO
# Provides: /root/scripts/addon_scan.py
# Required-Start: /root/scripts/addon_scan.py
# Required-Stop:  
# Should-Start: 
# Should-Stop: 
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Start and stop directadmin
# Description: run addon
### END INIT INFO

case "$1" in
    start)
      python /root/scripts/addon_scan.py
      echo "Starting add on"
      ;;
    stop)
      echo "Naaaaaaaaawwwwwww. not starting addon"
      ;;
    *)
      echo "Usage: /etc/init.d/foobar {start|stop}"
      exit 1
      ;;
esac

exit 0
