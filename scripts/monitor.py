#!/usr/bin/env python

import sys
import os
import time

class FileMonitor:
  def __init__(self):
    self.keepgoing = False

  def stop(self):
    self.keepgoing = False

  def monitor(self, folder, delay=5):
    if self.keepgoing:
      return

    self.keepgoing = True

    lstFiles = {}
    lstProcessed = []

    while self.keepgoing:
      time.sleep(delay)
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
          sys.stdout.write(folder + '/' + f + "\n")
          sys.stdout.flush()
          lstProcessed.append(f)
          break
        else:
          # Just track the change
          lstFiles[f] = size


if len(sys.argv) != 2:
  sys.stdout.write("monitor.py <folder>\n")
  sys.exit(255)


mon = FileMonitor()
mon.monitor(sys.argv[1])
