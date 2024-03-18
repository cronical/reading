"""common parsing help. Hosted in the 'post' project
(symbolic used in the 'reading' project).
Intended as a step in the eventual merger or the projects.
"""
import re
from pandas import isna

def extract_isbn(text: str)->str:
  """given a snippit of text grab the unformatted isbn contain it it (either 10 or 13)
  """
  pat='.*?(\d{13}|\d{9}[X0-9]{1}).*'
  mtch=re.match(pat,text)
  if not mtch: return None
  isbn=mtch.group(1)
  return isbn

def title_subitle_author(val):
  """Covert line that has title [: subtitle] / author to
  [title,subtitle,author]
  """
	
  s=val.split('/')
  if len(s)==1:
    s+=[''] # no author provided
    s[0]=drop_trailing_point(s[0]) # in that case the point is attached to the title
  ts,a=s
  val=ts.strip()+':' # extra : in case there is no subtitle
  val=val.replace(';',':') # sometimes a semi is used
  val=[a.strip() for a in val.split(':')]
  return val[0:2]+[a.strip()]

def author_clean(val):
  """drop 2nd comma and trailing stuff
  """
  val=','.join(val.split(',')[0:2])
  return val

def drop_trailing_point(val: str)->str:
  """Remove the trailing period if there is one."""
  if val.endswith('.'):
    val=val[:-1]
  return val

def xl_friendly_isbn(isbn):
  '''force excel to show isbn as a string'''
  if isna(isbn): return isbn
  return '="%s"'% isbn

def strip_xl_friendly(isbn):
  """remove the xl wrapper
  """
  if isna(isbn): return isbn
  pat='="([X\d]{10,10}|[\d]{13,13})"' 
  mtch=re.match(pat,isbn)
  if mtch:
    return mtch.group(1)
  else:
    return isbn
  
if __name__=="__main__":
  """testing
  """
  tests=[
    ("isbn 037542136X junk","037542136X"),
    ("037542136X","037542136X"),
    ("9780198842323 ","9780198842323"),
    ("junk", None)
    ]
  for test in tests:
    res=extract_isbn(test[0])
    if res is None:
      ok=test[1] is None
    else:
      ok=test[1] == res
    print(test[0], ":", ok)
