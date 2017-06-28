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

class Processor:
  def __init__(self, threads):
    self.exit = False
    self.queue = Queue()
    for w in range(threads):
      t = threading.Thread(target=self.worker)
      t.daemon = True
      t.start()

  def worker(self):
    while True:
      work = self.queue.get()
      work()
      self.queue.task_done()

  def add(self, process):
    if self.exit:
      return
    self.queue.put(process)

  def stop(self):
    self.queue.join()
