import sys
import check
import work
from reset import reset
import sync

if __name__ == '__main__':
  # get appropriate functions
  check_func = sys.argv[1]
  work_func = getattr(work, sys.argv[2])
  if len(sys.argv) > 3:
    sync_func = getattr(sync, sys.argv[3])
  else:
    sync_func = sync.sync
  # execute!
  reset()
  sync_func()
  getattr(check, check_func)(work_func)
  reset()