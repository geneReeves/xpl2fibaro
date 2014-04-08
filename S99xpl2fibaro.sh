#!/bin/sh

DAEMON=/volume1/web/python/xpl2fibaro.py

case "$1" in
    start)
	$DAEMON start > /dev/null 2>&1
	;;

    stop)
	$DAEMON stop > /dev/null 2>&1
	;;

    restart)
	$DAEMON restart > /dev/null 2>&1
	;;

    *)
	echo "Usage: S99xpl2fibaro.sh start|stop|restart"
	;;
esac
