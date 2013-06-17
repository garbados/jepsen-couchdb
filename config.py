nodes = [5984+i for i in range(1,6)]

def make_url(port):
  return "http://localhost:%s" % port