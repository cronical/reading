"""common parsing help
"""
import re
from pandas import isna

def title_subitle(val):
  """Covert line that has title [: subtitle] / author to
  [title,subtitle]"""
  val=val.split('/')[0].strip()+':' # extra : in case there is no subtitle
  val=[a.strip() for a in val.split(':')]
  return val[0:2]

def author_clean(val):
  """drop 2nd comma and trailing stuff
  """
  val=','.join(val.split(',')[0:2])
  return val

def drop_trailing_point(val: str)->str:
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