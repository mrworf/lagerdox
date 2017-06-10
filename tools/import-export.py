#!/usr/bin/env python
#
# Import/Export tool
#
# Will export data from lagerDOX 1.0
# Will import data to LagerDOX 2.0
#

"""
MariaDB [deleteme]> describe documents;
+-----------+--------------+------+-----+---------------------+----------------+
| Field     | Type         | Null | Key | Default             | Extra          |
+-----------+--------------+------+-----+---------------------+----------------+
| id        | int(11)      | NO   | PRI | NULL                | auto_increment |
| filename  | varchar(200) | NO   |     | NULL                |                |
| category  | int(11)      | NO   |     | 0                   |                |
| added     | timestamp    | NO   |     | CURRENT_TIMESTAMP   |                |
| dated     | timestamp    | NO   |     | 0000-00-00 00:00:00 |                |
| pagecount | int(11)      | NO   |     | 1                   |                |
+-----------+--------------+------+-----+---------------------+----------------+
6 rows in set (0.00 sec)

MariaDB [deleteme]> describe categories;
+----------+--------------+------+-----+---------+----------------+
| Field    | Type         | Null | Key | Default | Extra          |
+----------+--------------+------+-----+---------+----------------+
| id       | int(11)      | NO   | PRI | NULL    | auto_increment |
| name     | varchar(200) | NO   |     | NULL    |                |
| keywords | varchar(255) | NO   |     |         |                |
+----------+--------------+------+-----+---------+----------------+
3 rows in set (0.00 sec)

"""

import logging
import argparse
import uuid
import os
import sys
import shlex
import mysql.connector
from mysql.connector import errorcode
import json
import requests

""" Parse command line """
parser = argparse.ArgumentParser(description="Import/Export - LagerDOX tool", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
subp = parser.add_subparsers(help='Mode of operation', dest='mode')
e1 = subp.add_parser('exportv1', help='Exports the metadata of a LagerDOX v1.0 server')
e1.add_argument('--database', metavar='DATABASE', help='Which database to use')
e1.add_argument('--dbserver', metavar="SERVER", help='Server running mySQL or MariaDB')
e1.add_argument('--dbuser', metavar='USER', help='Username for server access')
e1.add_argument('--dbpassword', metavar='PASSWORD', help='Password for server access')
e1.add_argument('json', help="File to create with backup metadata")

i1 = subp.add_parser('importv1', help='Import the metadata and documents of a LagerDOX v1.0 server into v2.0 server')
i1.add_argument('server', metavar='SERVER', help='LagerDOX v2 server URL')
i1.add_argument('json', help="File with backed up metadata")
i1.add_argument('basedir', help='Base directory where to find documents referred to in backup')
i1.add_argument('--resume', help='Continues the import at document specified, useful if you get an error')
i1.add_argument('--max', help='Sets a limit on how many to import')

parser.add_argument('--logfile', metavar="FILE", help="Log to file instead of stdout")
cmdline = parser.parse_args()

""" Setup logging first """
logging.getLogger('').handlers = []
logging.basicConfig(filename=cmdline.logfile, level=logging.DEBUG, format='%(asctime)s - %(filename)s@%(lineno)d - %(levelname)s - %(message)s')
logging.getLogger("connectionpool").setLevel(logging.ERROR)

class ImportV1:
  def __init__(self):
    pass

  def init(self, server, basedir):
    self.server = server
    self.basedir = basedir
    # Make a testcall so we know we can talk to it
    r = requests.get(server + "/categories")
    if r.status_code == 200:
      self.categories = r.json()['result']
      for k in self.categories:
        k['filter'] = json.loads(k['filter'])
      return True
    return False

  def findCategory(self, name, keywords):
    for k in self.categories:
      if k['name'] == name and 'keywords' in k['filter'] and k['filter']['keywords'] == keywords:
        return k
    return None

  def createCategory(self, name, filter):
    filter = json.dumps({'keywords':filter})
    r = requests.put(
      self.server + '/category',
      headers={'Content-Type' : 'application/json'},
      data=json.dumps({'name':name,'filter':filter}))
    if r.status_code == 200:
      j = r.json();
      if 'result' in j:
        return int(j['result'])
      logging.error('Failed to add category: ' + j['error'])
    return None

  def resolveCategory(self, id):
    # No category
    if id == 0:
      return 0
    # Resolve mapping
    for m in self.mapping:
      if m['backup'] == id:
        return m['live']
    logging.warn('Unable to resolve category %d' % id)
    sys.exit(255)
    return 0

  def process(self, filename):
    j = None
    with open(filename, 'r') as f:
      j = json.load(f)

    logging.info('Generating category mapping')
    mapCat = []
    createCat = []
    # First, generate a list of categories we need
    for item in j['categories']:
      if item['id'] == 0:
        continue

      item['name'] = item['name'].strip().lower()
      item['keywords'] = item['keywords'].strip().lower()

      has = self.findCategory(item['name'], item['keywords'])
      if has:
        # We have it, so just map it
        mapCat.append({'backup' : item['id'], 'live' : has['id']})
      else:
        # We need to create this category
        createCat.append({'id' : item['id'], 'name':item['name'], 'filter':item['keywords']})
    if len(createCat) > 0:
      for n in createCat:
        id = self.createCategory(n['name'], n['filter'])
        mapCat.append({'backup' : n['id'], 'live' : id})
    self.mapping = mapCat

    logging.info('Processing documents and adding to server (via HTTP upload)')

    count = 0
    if cmdline.resume:
      resumeat = int(cmdline.resume)
    else:
      resumeat = 0

    if cmdline.max:
      maximport = int(cmdline.max) + resumeat
    else:
      maximport = -1

    for doc in j['documents']:
      count += 1
      logging.debug('Processing %d of %d' % (count, len(j['documents'])))

      if count < resumeat:
        continue
      if maximport != -1 and count == maximport:
        logging.error('Maximum number of documents imported (last imported was %d)' % (count-1))
        sys.exit(255)

      parts = doc['filename'].split('/')

      logging.info('Importing "%s/%s"' % (parts[-2], parts[-1]))

      filename = self.basedir + '/' + parts[-2] + '/' + parts[-1]
      files = {'file' : open(filename, 'rb')}
      values = {'scanned':doc['added'], 'received':doc['dated'], 'category' : self.resolveCategory(doc['category'])}
      try:
        r = requests.post(self.server + '/upload/manual', files=files, data=values)
        if r.status_code != 200:
          raise Exception('Server responded with error ' + r.status_code)
      except:
        logging.exception('Failed upload document #%d' % count)
        logging.error('Request details: ' + repr(values))
        logging.error('Result (RAW): ' + repr(r.content))
        sys.exit(255)


class ExportV1:
  def __init__(self):
    self.cnx = None

  def init(self, username, password, host, database):
    try:
      self.cnx = mysql.connector.connect(user=username,
                                         password=password,
                                         host=host,
                                         database=database)
      return True
    except mysql.connector.Error as err:
      if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        logging.error("Something is wrong with your user name or password")
      elif err.errno == errorcode.ER_BAD_DB_ERROR:
        logging.error("Database does not exist")
      else:
        logging.exception('Failed to connect')
    return False

  def getCategories(self):
    query = 'SELECT * FROM categories'
    cursor = self.cnx.cursor(dictionary=True, buffered=True)
    try:
      cursor.execute(query)
      return Iterator(cursor)
    except mysql.connector.Error as err:
      logging.exception('Query failed: ' + query)
      cursor.close()
    return Iterator(None, error='Error performing query')

  def getDocuments(self):
    query = 'SELECT UNIX_TIMESTAMP(added) AS added, UNIX_TIMESTAMP(dated) AS dated, pagecount, filename, category, id FROM documents'
    cursor = self.cnx.cursor(dictionary=True, buffered=True)
    try:
      cursor.execute(query)
      return Iterator(cursor)
    except mysql.connector.Error as err:
      logging.exception('Query failed: ' + query)
      cursor.close()
    return Iterator(None, error='Error performing query')

  def process(self, filename):
    logging.info('Beginning export of database to "%s"' % filename)
    logging.warn('NOTE! Actual OCR content is not exported nor are any files copied')
    with open(filename, 'w') as f:
      f.write('{"version":"1.0","categories":[')
      first = True
      for category in self.getCategories():
        if not first:
          f.write(',')
        else:
          first = False
        f.write(json.dumps(category))
      f.write('],"documents":[')
      first = True
      for document in self.getDocuments():
        if not first:
          f.write(',')
        else:
          first = False
        f.write(json.dumps(document))
      f.write(']}')
    logging.info('Export finished!')

class Iterator:
  def __init__(self, resultset, process=None, error=None):
    self.cursor = resultset
    self.error = error
    self.process = process

  def getError(self):
    """
    Returns any potential error, if no error condition exist,
    it will return None
    """
    return self.error

  def __iter__(self):
    return self

  def __next__(self):
    return self.next()

  def next(self):
    """
    Advances to the next record, returning current
    Record is a dict

    If no more record exists, the function returns None
    """
    if self.error is not None:
      raise StopIteration
    rec = self.cursor.fetchone()
    if rec is None:
      raise StopIteration
    elif self.process is not None:
      self.process(rec)
    return rec

  def release(self):
    """
    Early bailout, after calling this function, the iterator
    resources are freed and you should not use it anymore.
    """
    if self.error is not None:
      return
    self.error = 'Iterator is released'
    self.cursor.close()
    self.cursor = None
    return

if cmdline.mode == 'exportv1':
  mode = ExportV1()
  if mode.init(cmdline.dbuser, cmdline.dbpassword, cmdline.dbserver, cmdline.database):
    mode.process(cmdline.json)
  else:
    logging.error('Failed to initialize database access')
    sys.exit(1)
elif cmdline.mode == 'importv1':
  mode = ImportV1()
  if mode.init(cmdline.server, cmdline.basedir):
    mode.process(cmdline.json)
  else:
    logging.error('Unable to communicate with server or access basedir')
    sys.exit(1)
sys.exit(0)

