import re
import logging
import threading
from subprocess import Popen, PIPE, STDOUT
import os
import time
from Queue import Queue
import shutil
import json
import Analyzer
import hashlib

class Feeder (threading.Thread):
  def __init__(self, dbconn, basedir, destdir, thumbdir):
    threading.Thread.__init__(self)
    self.daemon = True
    self.stop = False
    self.queue = Queue()
    self.dbconn = dbconn
    self.basedir = basedir
    self.destdir = destdir
    self.thumbdir = thumbdir
    self.analyzer = Analyzer.Analyzer()
    self.start()

  def add(self, uid, content, mode, extras=None):
    self.queue.put({'uid' : uid, 'content' : content, 'mode' : mode, 'extras' : extras})

  def run(self):
    while not self.stop:
      item = self.queue.get()
      logging.info('Processing from queue');
      if item['content']['type'] == 'import':
        self.process(item['uid'], item['content'], item['mode'], item['extras'])
      elif item['content']['type'] == 'thumbnail':
        self.addthumb(item['uid'], item['content'], item['mode'], item['extras'])
      self.queue.task_done()

  def addthumb(self, uid, content, mode, extras):
    # Just copy the thumbnails
    folder = os.path.dirname(content['filename'])
    subfolder = os.path.basename(content['filename'])[:-4]
    dstpath = os.path.join(self.thumbdir, folder, subfolder)
    srcpath = os.path.join(self.basedir, uid)
    if not os.path.exists(dstpath):
      os.makedirs(dstpath)
    for p in content['pages']:
      src = os.path.join(srcpath, 'small%03d.jpg' % p['page'])
      dst = os.path.join(dstpath, 'small%03d.jpg' % p['page'])
      shutil.copy(src, dst)
      src = os.path.join(srcpath, 'large%03d.jpg' % p['page'])
      dst = os.path.join(dstpath, 'large%03d.jpg' % p['page'])
      logging.debug('Copying "%s" => "%s"' % (src, dst))
      shutil.copy(src, dst)
    self.cleanup(os.path.join(self.basedir, uid))

  def generateHash(self, filename):
    sha = hashlib.new('sha256')
    with open(filename, 'rb') as fp:
      for chunk in iter(lambda: fp.read(32768), b''):
        sha.update(chunk)
    return sha.hexdigest() + ":sha256"

  def process(self, uid, content, mode, extras):
    # Create a document first so we can feed it the pages
    now = int(time.time())
    fileandpath = self.copyfile(os.path.join(self.basedir, uid, content['file']), content['pagelen'])
    hashstr = self.generateHash(os.path.join(self.destdir, fileandpath))
    id = self.dbconn.add_document(0, now, 0, content['pagelen'], fileandpath, hashstr)
    if id is None:
      logging.error('Unable to add document')
      return
    else:
      self.analyzer.beginDate(now)
      for meta in content['metadata']:
        # Load the contents into memory
        data = self.loaddata(os.path.join(self.basedir, uid, 'page%03d.txt' % meta['page']))
        if not data:
          logging.error('No data found for page %d' % meta['page'])
          data = ''
        logging.debug('Adding page %d to document' % (meta['page']+1))
        self.dbconn.add_page(id, meta['page'], meta['ocr'], meta['blank-confidence'], meta['degrees'], meta['confidence'], meta['colors'], data)
        try:
          self.analyzer.updateDate(data)
        except:
          logging.exception('Failed during additon of data to analyzer')

      try:
        date = self.analyzer.finishDate()
      except:
        logging.exception('Failed when trying to find origination date, skipped')
        date = None

      if date is not None:
        if not self.dbconn.update_document(id, 'received', str(date)):
          logging.error('Unable to update received date on document')
      self.cleanup(os.path.join(self.basedir, uid))

      # This is where we figure out which category to assign
      if mode == 'manual':
        logging.info('Skipping categorization due to manual flag')
        logging.debug('Extras: ' + repr(extras))
        # Check if we're provided additional information
        changes = {}
        if 'scanned' in extras:
          # Change time of received
          changes['scanned'] = extras['scanned']
        if 'received' in extras:
          # What date to put on it
          changes['received'] = extras['received']
        if 'category' in extras:
          # What category to assign
          changes['category'] = extras['category']
        logging.debug('Pending changes: ' + repr(changes))
        if len(changes):
          self.dbconn.update_document(id, changes)
      elif mode is None:
        categories = self.dbconn.query_categories()
        candidates = []
        top = {'score':0}
        for cat in categories:
          logging.debug(repr(cat))
          score = 0
          filter = json.loads(cat['filter'])
          if 'keywords' in filter and filter['keywords'] != '':
            for res in self.dbconn.test_filter(filter['keywords'], id):
              score += res['score']
          if score > 0:
            candidates.append({'id' : cat['id'], 'score' : score})
            if score > top['score']:
              top['score'] = score
              top['id'] = cat['id']
        logging.debug('Category scores: ' + repr(candidates))
        logging.debug('Category top: ' + repr(top))
        if 'id' in top:
          logging.info('Assigning category %d to document' % top['id'])
          self.dbconn.assign_category(id, top['id'])
        else:
          logging.info('No matching category for this document')

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
    dstpath = os.path.join(self.thumbdir, folder, '%s_document%d' % (t, c))
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
