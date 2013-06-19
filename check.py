import requests
import sync
import time
import sys
from collections import Counter
from config import nodes, make_url

def format_acks(results, n):
  print "%d writes total." % n
  print "%d writes acknowledged." % len([result for result in results if 'ok' in result])

def format_remote(port, r, n):
    total = r.json()['total_rows']
    values = [row['doc']['value'] for row in r.json()['rows']]
    print "%d writes written to node %d" % (total, port)
    if total == n:
      if sum(values) == sum(range(n)):
        print "...and checksum passes!"

def get_all(nodes):
  results = {}
  for node in nodes:
    try:
      r = requests.get('/'.join([make_url(node), 'test', '_all_docs']),
                       params={
                        'include_docs': True
                       })
    except requests.exceptions.ConnectionError:
      print "%s down :(" % node
    else:
      results[node] = r
  return results

def get_by_quorum(nodes):
  results = []
  for node in nodes:
    try:
      r = requests.get('/'.join([make_url(node), 'test', '_all_docs']),
                       params={
                        'include_docs': True
                       })
    except requests.exceptions.ConnectionError:
      pass
    else:
      results.extend(r.json()['rows'])
  ids = {}
  for row in results:
    ids[row['id']] = row['doc']['value']
  for id in ids.keys()[:1]:
    doc = get_one_by_quorum(nodes, id)
    if doc:
      print "Got %s by quorum!" % id
    else:
      print "Failed to get %s by quorum" % id
  return ids

def get_one_by_quorum(nodes, id):
  n = 3
  docs = {}
  votes = Counter()
  for node in nodes:
    try:
      r = requests.get('/'.join([make_url(node), 'test', id]))
    except requests.exceptions.ConnectionError:
      pass
    else:
      doc = r.json()
      if '_rev' in doc:
        docs[doc['_rev']] = doc
        votes[doc['_rev']] += 1
        if votes.most_common(1)[0][1] >= n:
          break
  else:
    print votes
    return None
  return docs[votes.most_common(1)[0][0]]

def trainwreck_get(nodes):
  results = []
  for node in nodes:
    try:
      r = requests.get('/'.join([make_url(node), 'test', '_all_docs']),
                       params={
                        'include_docs': True
                       })
    except requests.exceptions.ConnectionError:
      pass
    else:
      results.extend(r.json()['rows'])
  ids = {}
  for row in [row['doc'] for row in results]:
    if row['_id'] in ids and row['_rev'] != ids[row['_id']]['rev']:
      print "Document conflict with %s" % row['_id']
    ids[row['_id']] = {
      'rev': row['_rev'],
      'value': row['value']
    }
  for id in ids.keys()[:1]:
    doc = get_one_by_quorum(nodes, id)
    if doc:
      print "Got %s by quorum!" % id
    else:
      print "Failed to get %s by quorum" % id
  return ids

### CHECKS ###

def simple(work, n=100):
  results = work(n)
  format_acks(results, n)
  results = get_all(nodes)
  for node, r in results.items():
    format_remote(node, r, n)

def sleep(work, n=100):
  results = work(n)
  format_acks(results, n)
  time.sleep(5)
  results = get_all(nodes)
  for node, r in results.items():
    format_remote(node, r, n)

def quorum(work, n=100):
  results = work(n)
  format_acks(results, n)
  results = get_by_quorum(nodes)
  print len(results.keys()), "docs in result set."
  if sum(results.values()) == sum(range(n)):
    print "...and checksum passed!"

def trainwreck(work, n=100):
  results = work(n)
  format_acks(results, n)
  results = trainwreck_get(nodes)
  print len(results.keys()), "docs in result set."
  values = [row['value'] for row in results.values()]
  # print values
  if sum(values) == sum(range(n)):
    print "...and checksum passed!"
  return results

def heal(work, n=100):
  trainwreck(work, n)
  sync.sync()
  time.sleep(5)
  results = get_all(nodes)
  for node, r in results.items():
    format_remote(node, r, n)
  else:
    id = r.json()['rows'][0]['id']
    doc = get_one_by_quorum(nodes, id)
    if doc:
      print "Got %s by quorum!" % id
    else:
      print "Failed to get %s by quorum" % id
    
