import re
import logging
import threading
from subprocess import Popen, PIPE, STDOUT
import os
import time
from Queue import Queue
import shutil
import json

class Analyzer:
  def __init__(self):
    self.MONTHS = [ "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec" ]
    # List of month, using the last unique bits to try and piece together it, incase OCR failed badly
    self.MONTHLAST = [ "nuary", "ruary", "rch", "ril", "may", "une", "uly", "ust", "tember", "ober", "vember", "cember" ]
    self.CONVERT = {"o" : "0", "z" : "2", "i" : "1"}.iteritems()

    flags = re.I|re.M|re.S
    self.patterns = [
      re.compile('([ o01]?[o0-9][/\\-\\.~][o0123]?[o0-9][/\\-\\.~][12]?[0-9]?[oiz0-9] ?[oiz0-9])', flags),
      # july 31  2012
      re.compile('((?:' + '|'.join(self.MONTHLAST) + '|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|july|August|September|october|November|December) +[0-3]?[ 0-9]{1,2}[\\., ]+[12][0-9 ]{3,4})', flags),
      # DD MMMMMMMM YYYY
      re.compile('([0-3]?[ 0-9]{1,2}[\\.\\-, ]+(?:' + '|'.join(self.MONTHLAST) + '|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|july|August|September|october|November|December)[\\.\\-, ]+[12][0-9 ]{3,4})', flags),
      # This one is weird, because it's when we have MMM DD HH:MM:SS YYYY
      re.compile('((?:' + '|'.join(self.MONTHLAST) + '|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|july|August|September|october|November|December) +[0-3]?[0-9][\\., ]+[0-9\\?:]{5,8} +[12][0-9 ]{3,4})', flags),
    ]

  def beginDate(self, scantime=None):
    self.dates = []
    self.scantime = scantime

  def updateDate(self, data):
    dates = []

    for reg in self.patterns:
      for m in reg.finditer(data):
        logging.debug('Found date candidate: "%s"' % m.group(1))
        # Remove erroneous spaces
        result = re.sub('([0-9]) ([0-9])', '\g<1>\g<2>', m.group(1))
        dates.append(result)
    self.dates.extend(dates)

  def finishDate(self):
    dates = []
    for date in self.dates:
      dateclean = date.strip().lower()
      for s,d in self.CONVERT:
        dateclean = dateclean.replace(s, d)

      bits = re.split('[\s,\\.\\-/~]+', date)
      bitsclean = re.split('[\s,\\.\\-/~]+', dateclean)

      # There is a special case, if we get 4 items and the last two are 3 and 1, then join them
      if len(bits) == 4 and len(bits[2]) == 3 and len(bits[3]) == 1:
        bits[2] += bits[3]
      elif len(bits) == 4 and (len(bits[2]) == 2 or len(bits[2]) == 4):
        # Looks like a MM DD YY(YY) version
        del bits[3]
      elif len(bits) == 4 and len(bits[1]) == 1 and len(bits[2]) == 1 and (len(bits[3]) == 2 or len(bits[3]) == 4):
        # Looks like a MM D D YY(YY) version, merge bits 2 into 1
        try:
          bits[1] += bits[2]
          bitsclean[1] += bitsclean[2]
          bits[2] = bits[3]
          bitsclean[2] = bitsclean[3]
          del bits[3]
          del bitsclean[3]
        except:
          logging.exception('Failed to remove bits')
          logging.debug('bits = ' + repr(bits))
          logging.debug('bitsclean = ' + repr(bitsclean))
          continue # Skip
      elif len(bits) == 4 and (len(bits[2]) > 4 or len(bits[2]) == 4):
        # Looks like a MM DD HH:MM:SS YY(YY) version
        pass
      elif len(bits) != 3: # If the bits aren't three, then it's not a date!
        #if ($bDebug) print("skipping since it's not a date\n");
        continue

      calctime = 0
      if bits[0].isdigit() and bits[1].isdigit() and bits[2].isdigit():
        # It's a completely numeric date. We're assuming it's a US date (MM DD YYYY)
        if int(bits[2]) < 1970 or int(bits[2]) > 2200:
          continue
        calctime = time.mktime((int(bits[2]), int(bits[0]), int(bits[1]), 0, 0, 0, 0, 0, -1))
      elif bitsclean[0].isdigit() and bitsclean[1].isdigit() and bitsclean[2].isdigit():
        if int(bitsclean[2]) < 1970 or int(bitsclean[2]) > 2200:
          continue
        calctime = time.mktime((int(bitsclean[2]), int(bitsclean[0]), int(bitsclean[1]), 0, 0, 0, 0, 0, -1))
      elif bitsclean[0].isdigit() and not bitsclean[1].isdigit() and bitsclean[2].isdigit():
        # Uses text, assuming DD MMM(MMM) YYYY
        month = -1
        for i in range(0, len(self.MONTHS)):
          if bits[0][:3] == self.MONTHS[i] or bits[0][1:] == self.MONTHLAST[i]:
            month = i

        if month == -1:
          continue

        if int(bitsclean[2]) < 1970 or int(bitsclean[2]) > 2200:
          continue
        calctime = time.mktime((int(bitsclean[2]), month+1, int(bitsclean[0]), 0, 0, 0, 0, 0, -1))
      else:
        # Uses text, assuming MMM(MMM) DD YYYY
        month = -1
        for i in range(0, len(self.MONTHS)):
          if bits[0][:3] == self.MONTHS[i] or bits[0][1:] == self.MONTHLAST[i]:
            month = i
        if month == -1:
          continue

        # One more exception here, if the last bit is 4 and the second to last is more than 4, use last for year
        if len(bitsclean[2]) > 4 and len(bitsclean[3]) == 4:
          if int(bitsclean[3]) < 1970 or int(bitsclean[3]) > 2200:
            continue
          calctime = time.mktime((int(bitsclean[3]), month+1, int(bitsclean[1]), 0, 0, 0, 0, 0, -1))
        else:
          if int(bitsclean[2]) < 1970 or int(bitsclean[2]) > 2200:
            continue
          calctime = time.mktime((int(bitsclean[2]), month+1, int(bitsclean[1]), 0, 0, 0, 0, 0, -1))

      logging.debug('Date "%s" translates to "%s"' % (dateclean, time.strftime('%c', time.localtime(calctime))))
      dates.append(calctime)

    """ For now, we calculate the distance in days and choose
        the entry which is closest to todays (or scanned) date, based on the
        fact that usually you don't get future dated stuff :)
    """
    if self.scantime:
      now = time.time()
    else:
      now = self.scantime

    # Make sure we strip off the time part to avoid issues with "rounding"
    snow = time.gmtime(now)
    now = time.mktime((snow[0], snow[1], snow[2], 0, 0, 0, snow[6], snow[7], snow[8]))
    closest = 0
    for date in dates:
      # Avoid future dating things...
      if date > now:
        continue

      if abs(now - date) < abs(now - closest):
        closest = date;
      else:
        pass

    # Check the final delta, because we are kinda picky
    sclosest = time.gmtime(closest)
    if abs(snow[0] - sclosest[0]) > 9:
      # Over 9 years delta, probably not a valid guess!
      return None

    logging.debug('Closest match is: %d (%s)' % (closest, time.strftime("%x", sclosest)))

    return closest