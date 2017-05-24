# Need to add string escape code
#
import sys
import time
import threading
import logging
import datetime
import traceback
import random
import Storage

import mysql.connector
from mysql.connector import errorcode

class MariaDB:

  def __init__(self):
    pass

  def connect(self, user, pw, host, database):
    self.user = user
    self.password = pw
    self.host = host
    self.database = database
    return self.reconnect()

  def reconnect(self):
    try:
      self.cnx = mysql.connector.connect(user=self.user,
                                         password=self.password,
                                         host=self.host,
                                         database=self.database)
      return True
    except mysql.connector.Error as err:
      if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        logging.error("Something is wrong with your user name or password")
      elif err.errno == errorcode.ER_BAD_DB_ERROR:
        logging.error("Database does not exist")
      else:
        logging.exception('Failed to connect')
    return False

  def getCursor(self, dictionary=False, buffered=False):
    cursor = None
    try:
      cursor = self.cnx.cursor(buffered=buffered, dictionary=dictionary)
    except:
      if self.reconnect():
        cursor = self.cnx.cursor(buffered=buffered, dictionary=dictionary)
      else:
        logging.exception('Unable to reestablish connection with database')
    return cursor

  def validate(self):
    """
    Tests if the database is setup properly or if it needs to be installed
    or upgraded.

        0 = All is OK
        1 = Missing table(s)
        2 = Needs to upgrade
      255 = Things went terribly wrong
    """
    cursor = self.getCursor(buffered=True)
    for table in [ 'documents', 'pages', 'categories', 'tags', 'tagmap' ]:
      query = ("DESCRIBE " + table)
      try:
        cursor.execute(query)
      except mysql.connector.Error as err:
        cursor.close()
        if err.errno == errorcode.ER_NO_SUCH_TABLE:
          return Storage.VALIDATION_NOT_SETUP
        else:
          logging.exception('Failed to validate')
          return Storage.VALIDATION_ERROR
    cursor.close()
    return Storage.VALIDATION_OK

  def setup(self, force):
    if force:
      cursor = self.getCursor(buffered=True)
      for table in [ 'documents', 'pages', 'categories', 'tags', 'tagmap' ]:
        query = ("DROP TABLE " + table)
        try:
          logging.info(query)
          cursor.execute(query)
        except mysql.connector.Error as err:
          pass
      cursor.close()

    if self.validate() != Storage.VALIDATION_NOT_SETUP:
      logging.error('Database is not in a state where it can be setup')
      return False

    sql = [
      'CREATE TABLE documents (id INT PRIMARY KEY AUTO_INCREMENT, category INT, scanned INT NOT NULL, received INT, pages INT NOT NULL, filename TEXT NOT NULL)',
      'CREATE TABLE pages (id INT NOT NULL, page INT NOT NULL, ocr BOOLEAN NOT NULL, blankness INT NOT NULL, degrees INT NOT NULL, confidence REAL NOT NULL, content LONGTEXT NOT NULL, FULLTEXT INDEX (content), UNIQUE KEY page (page, id))',
      'CREATE TABLE categories (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(128) NOT NULL, filter TEXT NOT NULL DEFAULT "")',
      'CREATE TABLE tags (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(128) NOT NULL, UNIQUE KEY name (name))',
      'CREATE TABLE tagmap (tag INT NOT NULL, document INT NOT NULL, UNIQUE KEY tag (tag, document))'
    ]

    cursor = self.getCursor(buffered=True)
    for s in sql:
      try:
        cursor.execute(s)
      except mysql.connector.Error as err:
        logging.exception('Failed to execute: ' + s)
        cursor.close()
        return False
    cursor.close()
    return True

  def disconnect(self):
    self.cnx.close()

  def prepare(self):
    return True

  def add_document(self, category, scanned, received, pages, filename):
    query = 'INSERT INTO documents (category, scanned, received, pages, filename) VALUES (%s, %s, %s, %s, %s)'
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query, (category, scanned, received, pages, filename))
      self.cnx.commit()
      return cursor.lastrowid
    except mysql.connector.Error as err:
      logging.exception('Failed to add document: ' + repr(err));
    finally:
      cursor.close()
    return None

  def add_page(self, document, page, ocr, blankness, degrees, confidence, blob):
    query = 'INSERT INTO pages (id, page, ocr, blankness, degrees, confidence, content) VALUES (%s, %s, %s, %s, %s, %s, %s)'
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query, (document, page, ocr, blankness, degrees, confidence, blob))
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to add page: ' + repr(err));
    finally:
      cursor.close()
    return False

  def delete_document(self, document):
    query = 'DELETE FROM documents WHERE id = %s' % document
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      if cursor.rowcount != 1:
        return False
      cursor.close()
      query = 'DELETE FROM pages WHERE id = %s' % document
      cursor = self.getCursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      cursor.close()
      query = 'DELETE FROM tagmap WHERE document = %s' % document
      cursor = self.getCursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to delete document: ' + repr(err));
    finally:
      cursor.close()
    return False

  def add_category(self, name, filter):
    name = name.lower().strip()
    if len(name) == 0:
      return False
    query = 'INSERT INTO categories (name, filter) VALUES (%s, %s)'
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query, (name.lower(), filter))
      self.cnx.commit()
      return cursor.lastrowid
    except mysql.connector.Error as err:
      logging.exception('Failed to add category: ' + repr(err));
    finally:
      cursor.close()
    return None

  def set_category(self, id, name, filter):
    if name is None and filter is None:
      return True
    if name is not None:
      name = name.lower().strip()
      if len(name) == 0:
        return False

    query = 'UPDATE categories SET'
    if name is not None:
      query += ' name="%s"' % name
    if filter is not None:
      query += ' filter="%s"' % filter
    query += ' WHERE id=%d' % id
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      return cursor.rowcount == 1
    except mysql.connector.Error as err:
      logging.exception('Failed to edit category: ' + repr(err));
    finally:
      cursor.close()
    return False

  def delete_category(self, id):
    query = 'DELETE FROM categories WHERE id = %d' % id
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      if cursor.rowcount != 1:
        return False
      cursor.close()
      query = 'UPDATE documents SET category = NULL WHERE id = %d' % id
      cursor = self.getCursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to delete category: ' + repr(err));
    finally:
      cursor.close()
    return False

  def assign_category(self, document, category):
    # Check that there is such a category!
    cursor = self.getCursor(buffered=True)
    try:
      # Zero is allowed since it's no category
      if category > 0:
        query = 'SELECT id FROM categories WHERE id = %d' % category
        cursor.execute(query)
        self.cnx.commit()
        if cursor.rowcount != 1:
          return False
      query = 'UPDATE documents SET category = %d WHERE id = %d' % (category, document)
      cursor.execute(query)
      self.cnx.commit()
      return cursor.rowcount == 1
    except mysql.connector.Error as err:
      logging.exception('Failed to update category: ' + repr(err));
    finally:
      cursor.close()
    return False

  def assign_tag(self, document, tag):
    cursor = self.getCursor(buffered=True)
    try:
      query = 'SELECT id FROM tags WHERE id = %d' % tag
      cursor.execute(query)
      self.cnx.commit()
      if cursor.rowcount != 1:
        return False
      query = 'SELECT id FROM documents WHERE id = %d' % document
      cursor.execute(query)
      self.cnx.commit()
      if cursor.rowcount != 1:
        return False
      query = 'INSERT INTO tagmap (tag, document) VALUES (%d, %d)' % (tag, document)
      cursor.execute(query)
      self.cnx.commit()
      return cursor.rowcount == 1
    except mysql.connector.Error as err:
      logging.exception('Failed to assign tag: ' + repr(err));
    finally:
      cursor.close()
    return False

  def remove_tag(self, document, tag):
    cursor = self.getCursor(buffered=True)
    try:
      # Zero is allowed since it's no category
      query = 'DELETE FROM tagmap WHERE tag=%d and document=%d' % (tag, document)
      cursor.execute(query)
      self.cnx.commit()
      return cursor.rowcount == 1
    except mysql.connector.Error as err:
      logging.exception('Failed to remove tag: ' + repr(err));
    finally:
      cursor.close()
    return False

  def clear_tag(self, document):
    cursor = self.getCursor(buffered=True)
    try:
      # Zero is allowed since it's no category
      query = 'DELETE FROM tagmap WHERE document=%d' % (document)
      cursor.execute(query)
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to remove tag: ' + repr(err));
    finally:
      cursor.close()
    return False

  def add_tag(self, name):
    name = name.lower().strip()
    if len(name) == 0:
      return False
    query = 'INSERT INTO tags (name) VALUES ( "%s" )' % name
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      return cursor.lastrowid
    except mysql.connector.Error as err:
      logging.exception('Failed to add tag, sql: "%s" name="%s"' % (query, name));
    finally:
      cursor.close()
    return None

  def set_tag(self, id, name):
    name = name.lower().strip()
    if len(name) == 0:
      logging.error('Empty name was provided')
      return False
    query = 'UPDATE tags SET name="%s" WHERE id=%d' % (name, int(id))
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      return cursor.rowcount == 1
    except mysql.connector.Error as err:
      logging.exception('Failed to edit tag, sql: "%s" name="%s"' % (query, name));
    finally:
      cursor.close()
    return False

  def delete_tag(self, id):
    query = 'DELETE FROM tags WHERE id = %d' % id
    cursor = self.getCursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      if cursor.rowcount != 1:
        return False
      cursor.close()
      query = 'DELETE FROM tagmap WHERE tag = %d' % id
      cursor = self.getCursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to delete tag: ' + repr(err));
    finally:
      cursor.close()
    return False

  def _query_with_iterator(self, query):
    cursor = self.getCursor(dictionary=True, buffered=True)
    try:
      cursor.execute(query)
      return Iterator(cursor, None)
    except mysql.connector.Error as err:
      logging.exception('Query failed');
    cursor.close()
    return None

  def query_tags(self):
    return self._query_with_iterator('SELECT * FROM tags ORDER BY name')

  def query_categories(self):
    return self._query_with_iterator('SELECT * FROM categories ORDER BY name')

  def query_document(self, id):
    data = None
    result = self._query_with_iterator('SELECT documents.*, categories.name AS cname FROM documents LEFT JOIN categories ON (documents.category = categories.id) WHERE documents.id = %d' % id)
    try:
      data = result.next()
      if data['cname'] is not None:
        data['category'] = {'id' : data['category'], 'name' : data['cname']}
      else:
        del data['category'];
      del data['cname']
      # Also load the tags related to this and replace the tag field
      result = self._query_with_iterator('SELECT tags.id, tags.name FROM tagmap LEFT JOIN tags ON (tags.id = tagmap.tag) WHERE document = %d' % id)
      data['tags'] = []
      for t in result:
        data['tags'].append(t)
      if len(data['tags']) == 0:
        del data['tags']
    except:
      logging.exception('Error getting document')
    return data

  def update_document(self, id, field, value):
    cursor = self.getCursor(dictionary=True, buffered=True)
    query = 'UPDATE documents SET %s = %s WHERE id = %d' % (field, value, id)
    try:
      cursor.execute(query)
      self.cnx.commit()
    except mysql.connector.Error as err:
      logging.exception('Query failed');
      return False
    finally:
      cursor.close()
    return True

  def query_pages(self, id):
    data = None
    result = self._query_with_iterator('SELECT * FROM pages WHERE id = %d ORDER BY page' % id)
    return result

  def cleanDocumentInfo(self, record):
    if 'category' in record and record['category'] == 0:
      del record['category']
    else:
      record['category'] = {'id' : record['category'], 'name' : record['cname']}
    del record['cname']
    if 'scanned' in record and record['scanned'] == 0:
      del record['scanned']
    if 'received' in record and record['received'] == 0:
      del record['received']

  def query_documents(self, tags=None, categories=None, sortby=None):
    # Build the query
    query = 'SELECT documents.*,categories.name AS cname FROM documents LEFT JOIN categories ON (documents.category = categories.id)'
    if tags:
      query += ' LEFT JOIN tagmap ON tagmap.document = documents.id WHERE tagmap.id IN ('
      for tag in tags:
        query += '%d' % tag
        if tag != tags[len(tags)-1]:
          query += ', '
      query += ')'

    if not tags and categories:
      query += ' WHERE'

    if categories:
      query += ' category IN ('
      for category in categories:
        query += '%d' % category
        if category != categories[len(categories)-1]:
          query += ', '
      query += ')'

    if sortby:
      query += ' ORDER BY %s' % sortby

    logging.debug('Query statement: ' + query)

    cursor = self.getCursor(dictionary=True, buffered=True)
    try:
      cursor.execute(query)
      return Iterator(cursor, self.cleanDocumentInfo, None)
    except mysql.connector.Error as err:
      logging.exception('Failed to query data: ' + repr(err));
    cursor.close()
    return Iterator(None, 'Error performing query')

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
