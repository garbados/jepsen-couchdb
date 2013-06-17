import requests
import time
from config import nodes, make_url
from work import work

if __name__ == '__main__':
  n = 100
  final_sum = sum(range(n))
  results = work(n)
  print "%d writes total." % n
  print "%d writes acknowledged." % len([result for result in results if result == 201])
  time.sleep(5)
  for node in nodes:
    r = requests.get('/'.join([make_url(node), 'test', '_all_docs']),
                     params={
                      'include_docs': True
                     })
    print "%d writes written to node %d" % (r.json()['total_rows'], node)
    if r.json()['total_rows'] == n:
      values = [row['doc']['value'] for row in r.json()['rows']]
      if sum(values) == final_sum:
        print "...and checksum passes!"