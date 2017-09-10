#!/bin/bash
QRCODETEXT="__SCANNER_DOCUMENT_SEPARATOR__"
QRENCODE=qrencode
CONVERT=convert

TMPFILE=/tmp/qrcode.png

# Generate a QR code
${QRENCODE} -o ${TMPFILE} "${QRCODETEXT}"

# Composite a PDF
${CONVERT} -size 1237x1762 xc:white \
        ${TMPFILE} -gravity NorthWest -composite \
        ${TMPFILE} -gravity North -composite \
        ${TMPFILE} -gravity NorthEast -composite \
        ${TMPFILE} -gravity West -composite \
        ${TMPFILE} -gravity Center -composite \
        ${TMPFILE} -gravity East -composite \
        ${TMPFILE} -gravity SouthWest -composite \
        ${TMPFILE} -gravity South -composite \
        ${TMPFILE} -gravity SouthEast -composite \
        -pointsize 25 \
        -gravity Center -draw "text 0,-275 'lagerDOX'" \
        -gravity Center -draw "text 0,-235 'http://mrworf.github.com/lagerdox'" \
        -gravity Center -draw "text 0,-75 'Scan Once'" \
        -gravity Center -draw "text 0,75 'Split Many'" \
        -gravity Center -draw "text 0,275 'Place a copy of this sheet between documents to'" \
        -gravity Center -draw "text 0,315 'split scanned items into multiple PDFs'" \
        -gravity Center -draw "text 0,415 'Tip!'" \
        -gravity Center -draw "text 0,455 'Print this double-sided'" \
        -compress ZIP \
        pdf:single.pdf

# Generate double sided version
${CONVERT} single.pdf single.pdf -compress ZIP splitter-page.pdf && rm single.pdf
