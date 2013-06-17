import sys
import check
import work

if __name__ == '__main__':
  check_func = sys.argv[1]
  work_func = getattr(work, sys.argv[2])
  getattr(check, check_func)(work_func)