"""
Resets each node, for sync.py
"""
import requests
import json
from config import nodes, make_url

def reset():
  results = []
  for i, node in enumerate(nodes):
    r = requests.get('/'.join([make_url(node), '_replicator', '_all_docs']))
    rows = [row for row in r.json()['rows'] if '_design' not in row['id']]
    for row in rows:
      doc = {
        'id': row['key'],
        'rev': row['value']['rev']
      }
      r = requests.delete('/'.join([make_url(node), '_replicator', doc['id']]),
                          params={'rev': doc['rev']})
      results.append(r)
    r = requests.delete('/'.join([make_url(node), 'test']))
    results.append(r)
  errors = [result for result in results if 'error' in result.json()]
  if not len(errors) == len(results):
    reset()
  else:
    print "Reset."

if __name__ == '__main__':
  reset()