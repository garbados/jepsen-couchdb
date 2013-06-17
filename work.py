"""
Puts the cluster through its paces
"""
import requests
import random
import json
from config import nodes, make_url

def get_node():
  """
  Returns a random node; pretends to be a Heroku router. (zing!)
  """
  return random.choice(nodes)

def work(n=100):
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
    results.append(r.status_code)
  return results

if __name__ == '__main__':
  work()