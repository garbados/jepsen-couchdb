"""
Sets up syncing between each node.
"""
import requests
import json
from config import nodes, make_url

sync_doc = """{
   "source": "%s/test",
   "target": "test",
   "continuous": true
}"""

def sync():
  for i, node in enumerate(nodes):
    # create test db in source
    r = requests.put('/'.join([make_url(node), 'test']))
    if r.status_code not in [201, 412]:
      print r.status_code
      raise Exception(r.json())
    # get list of nodes to create replications with
    other_nodes = nodes[::]
    other_nodes.pop(i)
    # push replication docs
    for other_node in other_nodes:
      doc = sync_doc % make_url(other_node)
      # print doc
      headers = {
        'Content-Type': 'application/json'
      }
      r = requests.post('/'.join([make_url(node), '_replicator']),
                        data=doc,
                        headers=headers)
      if 'error' in r.json():
        raise Exception(r.json())
  print "Synced." 

if __name__ == '__main__':
  sync()