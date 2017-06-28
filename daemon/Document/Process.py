"""
Thoughts for improvement:
- Extract the meta analytics to separate classes
- Use NLTK (see http://www.nltk.org/book/ch06.html) to classify both categories and tags
- Use threading to kick-off all meta & ocr logic at once (or at least X of them at a time) to leverage multiple CPU
- Use threading for extracting PNGs (again, at least X threads)
- The threading will work since it uses Popen

Add new filter to detect top colors and match them to list, see:
ha@development:~/projects/lagerdox/example-pdf$ convert rose.png -colors 32 limit.png
ha@development:~/projects/lagerdox/example-pdf$ convert limit.png -define histogram:unique-colors=true -format %c histogram:info:-
https://en.wikipedia.org/wiki/Color_difference

"""
import re
import logging
import threading
from subprocess import Popen, PIPE, STDOUT
import os
import time
from Queue import Queue
import shutil
import json

FLAG_MANUAL = 1

class Process:
  CMD_EXTRACT = 'convert -density 300 -depth 8 %(filename)s[%(page)d] -background white -flatten %(workpath)s/page%(page)03d.png'
  CMD_MULTIPLE = 'zbarimg %(workpath)s/page%(page)03d.png'
  CMD_SPLITTER = 'pdftk %(filename)s cat <pages> output %(dest)s'
  CMD_OCR_PAGE = 'tesseract %(workpath)s/page%(page)03d.png %(workpath)s/page%(page)03d -psm 1'

  CMD_THUMB_SMALL = 'convert %(workpath)s/page%(page)03d.png -resize 155x200 -rotate %(rotate)d -quality 85 %(workpath)s/small%(page)03d.jpg'
  CMD_THUMB_LARGE = 'convert %(workpath)s/page%(page)03d.png -resize 620x800 -rotate %(rotate)d -quality 85 %(workpath)s/large%(page)03d.jpg'

  CMD_META_DEGREE = 'tesseract %(workpath)s/page%(page)03d.png - -psm 0'
  CMD_META_BLANK1 = 'convert %(workpath)s/page%(page)03d.png -colorspace Gray -'
  CMD_META_BLANK2 = 'identify -format %%[standard-deviation]\\n%%[max]\\n%%[min]\\n -'
  CMD_META_COLOR  = 'convert %(workpath)s/page%(page)03d.png -colorspace HSL -channel H -separate -unique-colors -format %%w info:'

  BLANK_INDICATOR = 100
  MULTIPLE_INDICATOR = 'QR-Code:__SCANNER_DOCUMENT_SEPARATOR__'

  def __init__(self, uid, filename, workpath, callback, existing=None):
    self.callback = callback
    self.filename = filename
    self.workpath = workpath
    self.filepart = os.path.basename(filename)
    self.existing = existing
    self.state = {
      'overall' : 'PENDING',
      'filename' : self.filepart,
      'files' : 0,
      'pages' : 0,
      'file' : 0,
      'page' : 0,
      'sub' : ''
    }
    self.uid = uid

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
    if self.existing:
      print(repr(self.existing))
      result = self.processThumb()
    else:
      result = self.processFull()

    self.state['overall'] = 'FINISHED'
    self.callback(self.uid, result)

  def processThumb(self):
    self.state['overall'] = 'EXTRACT'
    success, _ = self.extract()
    if not success:
      self.state['overall'] = 'FAILED'
      return
    # Produce metadata
    result = []
    self.state['overall'] = 'PROCESS'
    for p in self.existing['pages']:
      self.state['page'] = p['page']
      self.state['sub'] = 'THUMB'
      self.thumb(p['page'], p)

    self.state['overall'] = 'COMPLETE'
    self.existing['type'] = 'thumbnail'
    return [self.existing]

  def processFull(self):
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
      data = {'type' : 'import', 'file' : f['file'], 'pagelen' : len(f['pages']), 'metadata' : []}
      for p in f['pages']:
        self.state['page'] = p
        metadata = {'page' : p}
        self.state['sub'] = 'COLORS'
        self.detectcolor(p, metadata)
        self.state['sub'] = 'DEGREE'
        self.meta_degree(p, metadata)
        self.state['sub'] = 'BLANK'
        self.meta_blank(p, metadata)
        self.state['sub'] = 'OCR'
        self.ocrpage(p, metadata)
        self.state['sub'] = 'THUMB'
        self.thumb(p, metadata)

        data['metadata'].append(metadata)
      result.append(data)
      self.state['file'] += 1

    self.state['overall'] = 'COMPLETE'
    return result

  def detectcolor(self, page, metadata):
    metadata['colors'] = 0

    lines, result = self._execute(Process.CMD_META_COLOR, {'page' : page})
    if result == 0 and lines:
      metadata['colors'] = int(lines)
    else:
      logging.error('Failed to analyze colors of page %d in "%s"' % (page, self.filepart))
      lines = lines.split('\n')
      for line in lines:
        logging.error('>>> ' + line.strip())
      return False


  def thumb(self, page, metadata):
    # Reuse pageXXX.png to produce viable thumbnails and avoid render PDF again
    lines, result = self._execute(Process.CMD_THUMB_SMALL, {'page' : page, 'rotate' : -metadata['degrees']})
    if result != 0:
      logging.error('Failed to generate small thumb of page %d in "%s"' % (page, self.filepart))
      lines = lines.split('\n')
      for line in lines:
        logging.error('>>> ' + line.strip())
      return False

    lines, result = self._execute(Process.CMD_THUMB_LARGE, {'page' : page, 'rotate' : -metadata['degrees']})
    if result != 0:
      logging.error('Failed to generate large thumb of page %d in "%s"' % (page, self.filepart))
      lines = lines.split('\n')
      for line in lines:
        logging.error('>>> ' + line.strip())
      return False

  def ocrpage(self, page, meta):
    meta['ocr'] = False
    lines, result = self._execute(Process.CMD_OCR_PAGE, {'page' : page})
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

    graycmd = self._execute(Process.CMD_META_BLANK1, {'page':page}, True)
    identcmd = self._execute(Process.CMD_META_BLANK2, {'page':page}, True)

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
      meta['blank'] = meta['blank-confidence'] < Process.BLANK_INDICATOR
      return True
    except:
      logging.exception('Failed to detect blank page')
    return False

  def meta_degree(self, page, meta):
    '''Detects orientation of page'''
    meta['degrees'] = 0
    meta['confidence'] = 0
    lines, result = self._execute(Process.CMD_META_DEGREE, {'page' : page})
    if lines:
      for line in lines.split('\n'):
        parts = line.strip().split(':')
        if 'Orientation in degrees' in parts[0]:
          meta['degrees'] = int(parts[1])
        elif 'Orientation confidence' in parts[0]:
          meta['confidence'] = float(parts[1])
      return True
    return False

  def multiple(self, pagelen):
    logging.info('Searching "%s" for splitter pages' % self.filepart)
    documents = []
    pages = []
    for page in range(0, pagelen):
      found = 0
      total = 0
      lines, result = self._execute(Process.CMD_MULTIPLE, {'page' : page})

      if lines:
        for line in lines.split('\n'):
          line = line.strip()
          if line == Process.MULTIPLE_INDICATOR:
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

    output, result = self._execute(Process.CMD_SPLITTER, {'dest' : dest, 'pages' : adjusted})
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
      output, result = self._execute(Process.CMD_EXTRACT, {'page' : page})
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
