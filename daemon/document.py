"""
Thoughts for improvement:
- Extract the meta analytics to separate classes
- Use NLTK (see http://www.nltk.org/book/ch06.html) to classify both categories and tags
- Use threading to kick-off all meta & ocr logic at once (or at least X of them at a time) to leverage multiple CPU
- Use threading for extracting PNGs (again, at least X threads)
- The threading will work since it uses Popen
"""
import re
import logging
import threading
from subprocess import Popen, PIPE, STDOUT
import os
import time
from Queue import Queue
import shutil

class Processor (threading.Thread):
  CMD_EXTRACT = 'convert -density 300 -depth 8 %(filename)s[%(page)d] %(workpath)s/page%(page)03d.png'
  CMD_MULTIPLE = 'zbarimg %(workpath)s/page%(page)03d.png'
  CMD_SPLITTER = 'pdftk %(filename)s cat <pages> output %(dest)s'
  CMD_OCR_PAGE = 'tesseract %(workpath)s/page%(page)03d.png %(workpath)s/page%(page)03d -psm 1'

  CMD_THUMB_SMALL = 'convert %(workpath)s/page%(page)03d.png -resize 155x200 -quality 85 %(workpath)s/small%(page)03d.jpg'
  CMD_THUMB_LARGE = 'convert %(workpath)s/page%(page)03d.png -resize 620x800 -quality 85 %(workpath)s/large%(page)03d.jpg'

  CMD_META_DEGREE = 'tesseract %(workpath)s/page%(page)03d.png - -psm 0'
  CMD_META_BLANK1 = 'convert %(workpath)s/page%(page)03d.png -colorspace Gray -'
  CMD_META_BLANK2 = 'identify -format %%[standard-deviation]\\n%%[max]\\n%%[min]\\n -'

  BLANK_INDICATOR = 100
  MULTIPLE_INDICATOR = 'QR-Code:__SCANNER_DOCUMENT_SEPARATOR__'

  def __init__(self, uid, filename, callback):
    threading.Thread.__init__(self)
    self.daemon = True

    self.callback = callback
    self.filename = filename
    self.workpath = os.path.dirname(filename)
    self.filepart = os.path.basename(filename)
    self.state = {
      'overall' : 'INIT',
      'files' : 0,
      'pages' : 0,
      'file' : 0,
      'page' : 0,
      'sub' : ''
    }
    self.uid = uid
    self.start()

  def getState(self):
    return self.state


  def _execute(self, cmdline, extras=None, manual=False):
    params = {
      'filename' : self.filename,
      'workpath' : self.workpath,
      'filepart' : self.filepart,
      'uid' : self.uid
    }
    if extras is not None:
      params.update(extras)

    # Split into parts
    cmds = cmdline.split()
    # Make sure all parts are translated properly
    new = []
    for i in range(0, len(cmds)):
      if cmds[i][0] == '<' and cmds[i][-1] == '>':
        new.extend(extras[cmds[i][1,-1]])
      else:
        new.append(cmds[i] % params)
    cmds = new

    # Allows caller to just get the processing
    if manual:
      return cmds

    # initiate the call and return to caller
    try:
      p = Popen(cmds, stdout=PIPE, stderr=STDOUT)
      out, ignore = p.communicate()
      return out, p.returncode
    except:
      logging.exception('Failed to execute (%s)' % repr(cmds))
      return None, -1

  def run(self):
    result = self.process()
    self.state['overall'] = 'FINISHED'
    self.callback(self.uid, result)

  def process(self):
    self.state['overall'] = 'EXTRACT'
    success, pages = self.extract()
    if not success:
      return
    self.state['pages'] = pages

    self.state['overall'] = 'MULTIPLE'
    files = self.multiple(pages)
    if files is None:
      return
    self.state['files'] = len(files)

    # Produce metadata
    result = []
    self.state['overall'] = 'PROCESS'
    for f in files:
      data = {'file' : f['file'], 'pagelen' : len(f['pages']), 'metadata' : []}
      for p in f['pages']:
        self.state['page'] = p
        metadata = {'page' : p}
        self.state['sub'] = 'DEGREE'
        self.meta_degree(p, metadata)
        self.state['sub'] = 'BLANK'
        self.meta_blank(p, metadata)
        self.state['sub'] = 'OCR'
        self.ocrpage(p, metadata)
        self.state['sub'] = 'THUMB'
        self.thumb(p)

        data['metadata'].append(metadata)
      result.append(data)
      self.state['file'] += 1

    self.state['overall'] = 'COMPLETE'
    return result

  def thumb(self, page):
    # Reuse pageXXX.png to produce viable thumbnails and avoid render PDF again
    lines, result = self._execute(Processor.CMD_THUMB_SMALL, {'page' : page})
    if result != 0:
      logging.error('Failed to generate small thumb of page %d in "%s"' % (page, self.filepart))
      lines = lines.split('\n')
      for line in lines:
        logging.error('>>> ' + line.strip())
      return False

    lines, result = self._execute(Processor.CMD_THUMB_LARGE, {'page' : page})
    if result != 0:
      logging.error('Failed to generate large thumb of page %d in "%s"' % (page, self.filepart))
      lines = lines.split('\n')
      for line in lines:
        logging.error('>>> ' + line.strip())
      return False

  def ocrpage(self, page, meta):
    meta['ocr'] = False
    lines, result = self._execute(Processor.CMD_OCR_PAGE, {'page' : page})
    if result != 0:
      logging.error('Failed to OCR page %d in "%s"' % (page, self.filepart))
      lines = lines.split('\n')
      for line in lines:
        logging.error('>>> ' + line.strip())
      return False
    meta['ocr'] = os.path.exists(os.path.join(self.workpath, 'page%03d.txt' % page))
    return True

  def meta_blank(self, page, meta):
    '''Detects if a page is blank'''
    meta['blank'] = False
    meta['blank-confidence'] = -1

    graycmd = self._execute(Processor.CMD_META_BLANK1, {'page':page}, True)
    identcmd = self._execute(Processor.CMD_META_BLANK2, {'page':page}, True)

    try:
      ident = Popen(identcmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
      gray = Popen(graycmd, stdout=ident.stdin)
      gray.wait()
      lines, result = ident.communicate()
      lines = lines.split('\n')
      stddev = float(lines[0])
      imgmin = float(lines[2])
      imgmax = float(lines[1])
      meta['blank-confidence'] = int(stddev / (imgmax - imgmin) * 10000)
      meta['blank'] = meta['blank-confidence'] < Processor.BLANK_INDICATOR
      return True
    except:
      logging.exception('Failed to detect blank page')
    return False

  def meta_degree(self, page, meta):
    '''Detects orientation of page'''
    meta['degree'] = None
    meta['degree-confidence'] = None
    lines, result = self._execute(Processor.CMD_META_DEGREE, {'page' : page})
    if lines:
      for line in lines.split('\n'):
        parts = line.strip().split(':')
        if 'Orientation in degrees' in parts[0]:
          meta['degree'] = int(parts[1])
        elif 'Orientation confidence' in parts[0]:
          meta['degree-confidence'] = float(parts[1])
      return True
    return False

  def multiple(self, pagelen):
    logging.info('Searching "%s" for splitter pages' % self.filepart)
    documents = []
    pages = []
    for page in range(0, pagelen):
      found = 0
      total = 0
      lines, result = self._execute(Processor.CMD_MULTIPLE, {'page' : page})

      if lines:
        for line in lines.split('\n'):
          line = line.strip()
          if line == Processor.MULTIPLE_INDICATOR:
            found += 1
          else:
            r = re.search('scanned ([0-9]+) barcode', line)
            if r:
              total = int(r.group(1))
        if found == total and found > 0:
          logging.debug('Found splitter page at page %d' % (page+1))
          if len(pages):
            documents.append(pages)
          pages = []
        else:
          pages.append(page)

    if len(pages) > 0:
      documents.append(pages)
    if len(documents) == 0:
      logging.info('File "%s" just contain splitter pages' % self.filepart)
      return None

    if len(documents) == 1 and len(documents[0]) == pagelen:
      logging.info('File "%s" contains a single document' % self.filepart)
      # No need to split, this is just a single document
      return [{'file': self.filepart, 'pages' : documents[0]}]

    # Multiple, so split it accordingly
    logging.info('File "%s" contains %d documents' % (self.filepart, len(documents)))

    success = True
    doc = 0
    result = []
    for pages in documents:
      name = 'subdoc%03d.pdf' % doc
      if not self.split(pages, name):
        success = False
        break
      doc += 1
      result.append({'file' : name, 'pages' : pages})

    # If we fail, use the original doc so data isn't lost!
    if not success:
      logging.error('Unable to split "%s" into multiple documents, saving as ONE document' % self.filepart)
      result = [{'file': self.filepart, 'pages' : range(0, pagelen)}]
    else:
      logging.info('Split "%s" into %s' % (self.filepart, repr(result)))
    return result

  def split(self, pages, dest):
    adjusted = []
    for p in pages:
      adjusted.append(p+1)

    output, result = self._execute(Processor.CMD_SPLITTER, {'dest' : dest, 'pages' : adjusted})
    if result != 0 or not os.path.exists(dest):
      logging.error('Unable to split "%s" into "%s" (pages %s)' % (self.filepart, dest, repr(pages)))
      lines = output.split('\n')
      for line in lines:
        logging.error('>>> ' + line.strip())
      return False
    return True

  def extract(self):
    # Splits the PDF into individual pieces so we can process
    page = 0
    result = 0
    while result == 0:
      output, result = self._execute(Processor.CMD_EXTRACT, {'page' : page})
      if result > 0:
        if "Requested FirstPage is greater than the number of pages in the file" not in output:
          lines = output.split('\n')
          logging.error('File "%s" is corrupt:' % self.filepart)
          for line in lines:
            logging.error('>>> ' + line.strip())
          return False, 0
      else:
        page += 1

    if page == 0:
      logging.warn('No pages found in "%s"' % self.filepart)
      return False, 0
    logging.info('Found %d page(s) in "%s"' % (page, self.filepart))
    return True, page

class Feeder (threading.Thread):
  def __init__(self, dbconn, basedir, destdir):
    threading.Thread.__init__(self)
    self.daemon = True
    self.stop = False
    self.queue = Queue()
    self.dbconn = dbconn
    self.basedir = basedir
    self.destdir = destdir
    self.analzer = Analyzer()
    self.start()

  def add(self, uid, content):
    self.queue.put({'uid' : uid, 'content' : content})

  def run(self):
    while not self.stop:
      item = self.queue.get()
      logging.info('Processing from queue')
      self.process(item['uid'], item['content'])
      self.queue.task_done()

  def process(self, uid, content):
    # Create a document first so we can feed it the pages
    now = int(time.time())
    fileandpath = self.copyfile(os.path.join(self.basedir, uid, content['file']), content['pagelen'])
    id = self.dbconn.add_document(0, now, 0, content['pagelen'], fileandpath)
    if id is None:
      logging.error('Unable to add document')
      return
    else:
      self.analzer.beginDate(now)
      for meta in content['metadata']:
        # Load the contents into memory
        data = self.loaddata(os.path.join(self.basedir, uid, 'page%03d.txt' % meta['page']))
        if not data:
          logging.error('No data found for page %d' % meta['page'])
        else:
          logging.debug('Adding page %d to document' % (meta['page']+1))
          self.dbconn.add_page(id, meta['page'], meta['ocr'], meta['blank-confidence'], meta['degree'], meta['degree-confidence'], data)
          self.analzer.updateDate(data)
      date = self.analzer.finishDate()
      if date is not None:
        if not self.dbconn.update_document(id, 'received', str(date)):
          logging.error('Unable to update received date on document')
      self.cleanup(os.path.join(self.basedir, uid))

  def cleanup(self, path):
    shutil.rmtree(path)

  def copyfile(self, filename, pages):
    # First, the document itself
    folder = time.strftime('%Y-%m-%d')
    path = os.path.join(self.destdir, folder)
    if not os.path.exists(path):
      os.makedirs(path)
    t = time.strftime('%H.%M.%S')
    c = 1
    f = ''
    while True:
      f = os.path.join(path, '%s_document%d.pdf' % (t, c))
      if not os.path.exists(f):
        break
      else:
        c += 1
    shutil.copy(filename, f)

    # Next, copy all thumbnails
    dstpath = os.path.join(self.destdir, folder, '%s_document%d' % (t, c))
    srcpath = os.path.dirname(filename)
    if not os.path.exists(dstpath):
      os.makedirs(dstpath)
    for p in range(0, pages):
      src = os.path.join(srcpath, 'small%03d.jpg' % p)
      dst = os.path.join(dstpath, 'small%03d.jpg' % p)
      shutil.copy(src, dst)
      src = os.path.join(srcpath, 'large%03d.jpg' % p)
      dst = os.path.join(dstpath, 'large%03d.jpg' % p)
      shutil.copy(src, dst)

    return os.path.join(folder, '%s_document%d.pdf' % (t, c))

  def loaddata(self, filename):
    try:
      with open(filename, 'rb') as f:
        return f.read()
    except:
      logging.exception('Failed to open "%s"' % filename)
    return None

  def finish(self):
    self.stop = True

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
        dates.append(m.group(1))
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
        bits[1] += bits[2]
        bitsclean[1] += bitsclean[2]
        bits[2] = bits[3]
        bitsclean[2] = bitsclean[3]
        del bits[3]
        del bitsclean[3]
      elif len(bits) == 4 and (len(bits[2]) > 4 or len(bits[2]) == 4):
        # Looks like a MM DD HH:MM:SS YY(YY) version
        pass
      elif len(bits) != 3: # If the bits aren't three, then it's not a date!
        #if ($bDebug) print("skipping since it's not a date\n");
        continue

      calctime = 0
      if bits[0].isdigit() and bits[1].isdigit() and bits[2].isdigit():
        # It's a completely numeric date. We're assuming it's a US date (MM DD YYYY)
        calctime = time.mktime((int(bits[2]), int(bits[0]), int(bits[1]), 0, 0, 0, 0, 0, -1))
      elif bitsclean[0].isdigit() and bitsclean[1].isdigit() and bitsclean[2].isdigit():
        calctime = time.mktime((int(bitsclean[2]), int(bitsclean[0]), int(bitsclean[1]), 0, 0, 0, 0, 0, -1))
      elif bitsclean[0].isdigit() and not bitsclean[1].isdigit() and bitsclean[2].isdigit():
        # Uses text, assuming DD MMM(MMM) YYYY
        month = -1
        for i in range(0, len(self.MONTHS)):
          if bits[0][:3] == self.MONTHS[i] or bits[0][1:] == self.MONTHLAST[i]:
            month = i

        if month == -1:
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
          calctime = time.mktime((int(bitsclean[3]), month+1, int(bitsclean[1]), 0, 0, 0, 0, 0, -1))
        else:
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




