#!/bin/bash
# Copyright (c) 2018 Felix Almeida (white-glider)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

umask 077
RSLT=/tmp/$$_clamav.tmp
MSG=/tmp/$$_email.tmp

function awk_file {
	AWK_FILE=$(echo $1 | sed 's/\(.*\)\.\([^\.]*\)/\1\.awk/')
        if [ "$1" == "$AWK_FILE" ]; then
		AWK_FILE=$1.awk
	fi
}

cat > $MSG
awk_file $(readlink -f "$0")
if [ ! -r "$AWK_FILE" ]; then
	echo "$(basename $0): Missing AWK counterpart ($AWK_FILE)" >&2
	rm $MSG
	exit 2
fi

#clamdscan --no-summary $MSG > $RSLT
clamscan --no-summary --detect-pua=yes --official-db-only=yes $MSG > $RSLT
if [ $? -eq 1 ]; then
	THREAT=$(awk '$NF ~ /FOUND/ {print $2}' $RSLT)
	STRING=$(awk -f $AWK_FILE $MSG)
	notify-send --urgency=critical --category=email --icon=/usr/share/icons/Adwaita/scalable/status/dialog-warning-symbolic.svg "ClamAV: e-mail threat detected!" "$THREAT\n$STRING"
	rm $MSG $RSLT
	exit 1
fi
rm $MSG $RSLT
exit 0
