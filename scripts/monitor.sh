#!/bin/bash
#
# Simple script which monitors a folder and automatically
# imports the PDFs found there-in. This means that once the PDF has been
# analyzed, it will be moved from this directory into the destination folder
# as specified by config.php
#
# Makes use of inotify to improve performance.
#
####### SETTINGS ##############################################################
#
# Directory to monitor for incoming PDFs (this needs to change from example)
#
INPUTDIR=$(dirname "$0")/../example-pdf/
#
# Command to call to import the document. This is normally found in the same
# folder as this script.
#
PROCESSCMD=$(dirname "$0")/add_database.php
#
####### DO NOT EDIT BELOW #####################################################
#
# Before we start, process any pending documents if user
# had already placed them here before starting us.
#
echo "Processing pending documents..."
for FILE in $( find ${INPUTDIR}/ -iname '*.pdf' ); do
	EXT=${FILE##*.}
	EXT=${EXT,,}

	if [ "${EXT}" == "pdf" ]; then
		${PROCESSCMD} "${FILE}"
	fi
done

# Begin monitoring the folder for changes
#
echo "Starting scanner monitor"
inotifywait -q --format %w%f -me close_write -r ${INPUTDIR} | while read LINE
do
	FILE=${LINE}
	EXT=${FILE##*.}
	EXT=${EXT,,}

	if [ "${EXT}" == "pdf" ]; then
		${PROCESSCMD} "${FILE}"
	fi
done
