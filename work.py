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
    doc = {
      'value': i
    }
    while True:
      url = '/'.join([make_url(get_node()), 'test'])
      try:
        r = requests.post(url,
                          data=json.dumps(doc),
                          headers={
                            'content-type': 'application/json'
                          })
      except requests.exceptions.ConnectionError:
        pass
      else:
        results.append(r.json())
        break
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
      try:
        r = requests.post(url,
                          data=json.dumps(doc),
                          headers={
                            'content-type': 'application/json'
                          })
      except requests.exceptions.ConnectionError:
        node_index += 1
      else:
        results.append(r.json())
        break
  return results

def sequential(n=100):
  """
  Each write goes to a different node, in sequence
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
      node_index += 1
      url = '/'.join([make_url(get_node()), 'test'])
      doc = {
        'value': i
      }
      try:
        r = requests.post(url,
                          data=json.dumps(doc),
                          headers={
                            'content-type': 'application/json'
                          })
      except requests.exceptions.ConnectionError:
        pass
      else:
        results.append(r.json())
        break
  return results

def shitshow(n=100):
  """
  Like sequential, but with updates, because you're a glutton for pain.
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
      node_index += 1
      url = '/'.join([make_url(get_node()), 'test'])
      doc = {
        'value': i
      }
      try:
        r = requests.post(url,
                          data=json.dumps(doc),
                          headers={
                            'content-type': 'application/json'
                          })
      except requests.exceptions.ConnectionError:
        pass
      else:
        results.append(r.json())
        break
  # now for the updates
  results2 = []
  for i, result in enumerate(results):
    if 'ok' in result:
      while True:
        node_index += 1
        url = '/'.join([make_url(get_node()), 'test', result['id']])
        doc = {
          'value': i,
          'changed': True,
          '_id': result['id'],
          '_rev': result['rev']
        }
        try:
          r = requests.put(url,
                            data=json.dumps(doc),
                            headers={
                              'content-type': 'application/json'
                            })
        except requests.exceptions.ConnectionError:
          pass
        else:
          results2.append(r.json())
          break
    else:
      results2.append(result)
  return results2