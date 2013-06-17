"""
Puts the cluster through its paces, randomly
"""
import requests
import random as rand
import json
from config import nodes, make_url

def random(n=100):
  """
  Assigns work amongst the nodes randomly
  """
  def get_node():
    """
    Returns a random node; pretends to be a Heroku router. (zing!)
    """
    return rand.choice(nodes)
  results = []
  for i in range(n):
    url = '/'.join([make_url(get_node()), 'test'])
    doc = {
      'value': i
    }
    r = requests.post(url,
                      data=json.dumps(doc),
                      headers={
                        'content-type': 'application/json'
                      })
    results.append(r.json())
  return results

def direct(n=100):
  """
  Writes to a single master. Picks the next node on failure.
  """
  node_index = 0
  def get_node():
    """
    Returns the node corresponding to `node_index`. 
    Wraps around if `node_index` > `len(nodes)`.
    """
    return nodes[node_index % len(nodes)]
  results = []
  for i in range(n):
    while True:
      url = '/'.join([make_url(get_node()), 'test'])
      doc = {
        'value': i
      }
      r = requests.post(url,
                        data=json.dumps(doc),
                        headers={
                          'content-type': 'application/json'
                        })
      if r.status_code == 201:
        break
      else:
        node_index += 1
    results.append(r.json())
  return results