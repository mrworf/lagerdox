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
    try:
      self.cnx = mysql.connector.connect(user=user,
                                         password=pw,
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

  def validate(self):
    """
    Tests if the database is setup properly or if it needs to be installed
    or upgraded.

        0 = All is OK
        1 = Missing table(s)
        2 = Needs to upgrade
      255 = Things went terribly wrong
    """
    cursor = self.cnx.cursor(buffered=True)
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
      cursor = self.cnx.cursor(buffered=True)
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
      'CREATE TABLE documents (id INT PRIMARY KEY AUTO_INCREMENT, category INT, scanned INT NOT NULL, received INT, pages INT NOT NULL)',
      'CREATE TABLE pages (id INT NOT NULL, page INT NOT NULL, ocr BOOLEAN NOT NULL, blankness INT NOT NULL, degrees INT NOT NULL, confidence REAL NOT NULL, content TEXT NOT NULL, FULLTEXT INDEX (content), UNIQUE KEY page (page, id))',
      'CREATE TABLE categories (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(128) NOT NULL, keywords VARCHAR(256) NOT NULL)',
      'CREATE TABLE tags (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(128) NOT NULL)',
      'CREATE TABLE tagmap (tag INT NOT NULL, document INT NOT NULL, UNIQUE KEY tag (tag, document))'
    ]

    cursor = self.cnx.cursor(buffered=True)
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
    """
    Loads up the cache and is now ready to be used (yes, this could be done by a join)
    """
    return True

  def add_document(self, category, scanned, received, pages):
    query = 'INSERT INTO documents (category, scanned, received, pages) VALUES (%s, %s, %s, %s)'
    cursor = self.cnx.cursor(buffered=True)
    try:
      cursor.execute(query, (category, scanned, received, pages))
      self.cnx.commit()
      return cursor.lastrowid
    except mysql.connector.Error as err:
      logging.exception('Failed to add document: ' + repr(err));
    finally:
      cursor.close()
    return None

  def add_page(self, document, page, ocr, blankness, degrees, confidence, blob):
    query = 'INSERT INTO pages (id, page, ocr, blankness, degrees, confidence, content) VALUES (%s, %s, %s, %s, %s, %s, %s)'
    cursor = self.cnx.cursor(buffered=True)
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
    cursor = self.cnx.cursor(buffered=True)
    try:
      cursor.execute(query)
      self.cnx.commit()
      cursor.close()
      query = 'DELETE FROM pages WHERE id = %s' % document
      cursor = self.cnx.cursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      cursor.close()
      query = 'DELETE FROM tagmap WHERE document = %s' % document
      cursor = self.cnx.cursor(buffered=True)
      cursor.execute(query)
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to delete document: ' + repr(err));
    finally:
      cursor.close()
    return False

  def add_category(self, name, keywords):
    query = 'INSERT INTO category (name, keywords) VALUES (%s, %s)'
    cursor = self.cnx.cursor(buffered=True)
    try:
      cursor.execute(query, (name, keywords))
      self.cnx.commit()
      return cursor.lastrowid
    except mysql.connector.Error as err:
      logging.exception('Failed to add category: ' + repr(err));
    finally:
      cursor.close()
    return None

  def delete_category(self, id):
    query = 'DELETE FROM category WHERE id = %d' % id
    cursor = self.cnx.cursor(buffered=True)
    try:
      cursor.execute(query, (name, keywords))
      self.cnx.commit()
      cursor.close()
      query = 'UPDATE documents SET category = NULL WHERE id = %d' % id
      cursor = self.cnx.cursor(buffered=True)
      cursor.execute(query, (name, keywords))
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to delete category: ' + repr(err));
    finally:
      cursor.close()
    return False

  def add_tag(self, name):
    query = 'INSERT INTO tags (name) VALUES (%s)'
    cursor = self.cnx.cursor(buffered=True)
    try:
      cursor.execute(query, (name))
      self.cnx.commit()
      return cursor.lastrowid
    except mysql.connector.Error as err:
      logging.exception('Failed to add tag: ' + repr(err));
    finally:
      cursor.close()
    return None

  def delete_tag(self, id):
    query = 'DELETE FROM tags WHERE id = %d' % id
    cursor = self.cnx.cursor(buffered=True)
    try:
      cursor.execute(query, (name, keywords))
      self.cnx.commit()
      cursor.close()
      query = 'DELETE FROM tagmap WHERE id = %d' % id
      cursor = self.cnx.cursor(buffered=True)
      cursor.execute(query, (name, keywords))
      self.cnx.commit()
      return True
    except mysql.connector.Error as err:
      logging.exception('Failed to delete tag: ' + repr(err));
    finally:
      cursor.close()
    return False

  def _query_with_iterator(self, query):
    cursor = self.cnx.cursor(dictionary=True, buffered=True)
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
    result = self._query_with_iterator('SELECT * FROM documents WHERE id = %d' % id)
    if result:
      data = result.next()
      result.release()
    return data

  def query_pages(self, id):
    data = None
    result = self._query_with_iterator('SELECT * FROM pages WHERE id = %d ORDER BY page' % id)
    return result

  def query_documents(self, tags=None, categories=None, sortby=None):
    # Build the query
    query = 'SELECT * FROM documents'
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

    cursor = self.cnx.cursor(dictionary=True, buffered=True)
    try:
      cursor.execute(query)
      return Iterator(cursor, None)
    except mysql.connector.Error as err:
      logging.exception('Failed to query data: ' + repr(err));
    cursor.close()
    return Iterator(None, 'Error performing query')

class Iterator:
  def __init__(self, resultset, error=None):
    self.cursor = resultset
    self.error = error
    pass

  def getError(self):
    """
    Returns any potential error, if no error condition exist,
    it will return None
    """
    return self.error

  def next(self):
    """
    Advances to the next record, returning current
    Record is a dict

    If no more record exists, the function returns None
    """
    if self.error is not None:
      return None
    rec = self.cursor.fetchone()
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
