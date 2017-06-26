#
# Regular cron jobs for the lagerdox package
#
0 4	* * *	root	[ -x /usr/bin/lagerdox_maintenance ] && /usr/bin/lagerdox_maintenance
