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
import argparse
import hashlib
from ConfigParser import ConfigParser

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
          # Send this file to the callback
          if callback(folder + '/' + f, f):
            lstProcessed.append(f)
        else:
          # Just track the change
          lstFiles[f] = size

cmdline = None

def generateHash(filename):
  sha = hashlib.new('sha256')
  with open(filename, 'rb') as fp:
    for chunk in iter(lambda: fp.read(32768), b''):
      sha.update(chunk)
  return sha.hexdigest() + "%3A" + "sha256"

def onFile(filename, name):
  # First, make sure file isn't already on server
  hashstr = generateHash(filename)
  url = cmdline.server + "/document/hash/" + hashstr
  try:
    r = requests.get(url)
  except:
    logging.exception('Failed to communicate with server "%s"', cmdline.server)
    return False
  if r.status_code == 200:
    logging.debug('"%s" already on server' % name)
    if not cmdline.upload_existing:
      return True

  url = cmdline.server + "/upload"
  files = {'file' : open(filename, 'rb')}
  try:
    r = requests.post(url, files=files)
  except:
    logging.exception('Failed to communicate with server "%s"', cmdline.server)
    return False

  ret = False
  j = None
  try:
    j = r.json()
  except:
    logging.exception('"%s" failed: Corrupt server response', name)
  if j is not None:
    if 'result' in j and j['result'] == 'OK':
      ret = True # Success
      logging.info('"%s" uploaded, uid = %s', name, j['uid'])
      if cmdline.keep:
        logging.debug('Keeping "%s" in folder', filename)
      else:
        try:
          os.unlink(filename)
        except:
          logging.exception('Failed to delete "%s"', filename)
    elif 'error' in j:
      logging.error('"%s" failed: %s', name, j['error'])
      if j['error'] == 'File not allowed' and cmdline.delete_invalid:
        ret = True # Considered success
        logging.debug('Deleting invalid file "%s"', filename)
        try:
          os.unlink(filename)
        except:
          logging.exception('Failed to delete "%s"', filename)
    else:
      logging.error('"%s" failed', name)
  else:
    logging.error('"%s" failed', name)
  return ret

parser = argparse.ArgumentParser(description="Monitor - Looks for files to push into lagerDOX", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--logfile', help="Log to file instead of stdout")
parser.add_argument('--server', default="http://localhost:7000", help="Which server to send documents to")
parser.add_argument('--folder', help="Which folder to monitor for files")
parser.add_argument('--keep', action='store_true', default=False, help="Don't delete the uploaded file from folder")
parser.add_argument('--upload-existing', action='store_true', default=False, help="Upload existing documents (causes duplicates)")
parser.add_argument('--delete-invalid', action='store_true', default=False, help="Delete files which the server says it doesn't support")
parser.add_argument('--debug', action='store_true', default=False, help="Enable additional log messages")
parser.add_argument('config', help='Configuration file')
cmdline = parser.parse_args()

loglevel = logging.INFO
if cmdline.debug:
  loglevel = logging.DEBUG

logging.getLogger('').handlers = []
logging.basicConfig(filename=cmdline.logfile, level=loglevel, format='%(asctime)s - %(filename)s@%(lineno)d - %(levelname)s - %(message)s')
logging.getLogger("requests").setLevel(logging.ERROR)

config = ConfigParser()
config.add_section("general")
config.set("general", "folder", '')
config.set("general", "server", "http://localhost:7000")
config.set("general", "keep", 'False')
config.set("general", "upload-existing", 'False')
config.set("general", "delete-invalid", 'False')

if not cmdline.keep:
	cmdline.keep = config.getboolean("general", "keep")
if not cmdline.upload_existing:
	cmdline.upload_existing = config.getboolean("general", "upload-existing")
if not cmdline.delete_invalid:
	cmdline.delete_invalid = config.getboolean("general", "delete-invalid")
if not cmdline.folder:
	cmdline.folder = config.get("general", "folder")
if not cmdline.server:
	cmdline.server = config.get("general", "server")

if cmdline.folder is None or cmdline.folder == '':
	logging.error('You must specify a folder to monitor (cannot be blank or left out)')
	sys.exit(1)

mon = FileMonitor()
mon.monitor(cmdline.folder, onFile)
