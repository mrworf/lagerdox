#!/usr/bin/env python
#
# Since many times users will be using a network folder for monitoring
# we cannot rely on inotify messages because they only work IF we're
# running on the machine which hosts the files. The moment we're monitoring
# files residing on a network share, this breaks.
#
# So instead we monitor files and sizes over time, and if they're no longer
# changing, we assume they're done and process them.
#

import sys
import os
import time

import logging
import requests

class FileMonitor:
  def __init__(self):
    self.keepgoing = False

  def stop(self):
    self.keepgoing = False

  def monitor(self, folder, callback, delay=5):
    if self.keepgoing:
      return

    self.keepgoing = True

    lstFiles = {}
    lstProcessed = []

    logging.info('Monitoring of "%s" started', folder)

    while self.keepgoing:
      time.sleep(float(delay))
      files = os.listdir(folder)
      d = []
      # Figure out which files have disappeared so we don't track them
      for f in lstFiles:
        if f not in files:
          d.append(f)

      # Remove them from tracking
      for f in d:
        if f in lstProcessed:
          lstProcessed.remove(f)
        del lstFiles[f]

      # Process newcomers and old favorites
      for f in files:
        if not os.path.isfile(folder + '/' + f):
          continue
        size = os.path.getsize(folder + '/' + f)

        if f in lstFiles and lstFiles[f] == size and f not in lstProcessed:
          # File has not changed since last, emit it
          callback(folder + '/' + f, f)
          lstProcessed.append(f)
        else:
          # Just track the change
          lstFiles[f] = size

logging.getLogger('').handlers = []
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(filename)s@%(lineno)d - %(levelname)s - %(message)s')
logging.getLogger("requests").setLevel(logging.ERROR)

def onFile(filename, name):
  url = sys.argv[2] + "/upload"
  files = {'file' : open(filename, 'rb')}
  r = requests.post(url, files=files)
  j = None
  try:
    j = r.json()
  except:
    logging.exception('"%s" failed: Corrupt server response', name)
  if j is not None:
    if 'result' in j and j['result'] == 'OK':
      logging.info('"%s" uploaded, uid = %s', name, j['uid'])
    elif 'error' in j:
      logging.error('"%s" failed: %s', name, j['error'])
    else:
      logging.error('"%s" failed', name)
  else:
    logging.error('"%s" failed', name)

if len(sys.argv) != 3:
  sys.stdout.write("monitor.py <folder> <server url>\n")
  sys.exit(255)

mon = FileMonitor()
mon.monitor(sys.argv[1], onFile)
