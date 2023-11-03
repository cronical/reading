#!/usr/bin/env python3
'''Parse the files downloaded from email
'''
import datetime
import os
import pandas as pd

data=[]
base='data'
for item in os.listdir(base):
  folder=os.path.join(base,item)
  if os.path.isdir(folder):
    file=os.path.join(folder,"text.txt")
    if os.path.exists(file):
      with open(file) as f:
        date=None
        flag=False
        for line in f:
          if line.startswith('Title:'):
            line=line[6:].strip()
            ta=line.split(' / ')
            author=None
            if len(ta)==2:
              author=ta[1]
              if author[-1]=='.':
                author=author[:-1]
            title=ta[0].split(' : ')
            subtitle=None
            if len(title)==2:
              subtitle=title[1]
            title=title[0].strip()
          if line.startswith('Total items'):
            flag=True
            continue
          if flag:
            date=line.split(' ')[0]
            date=datetime.datetime.strptime(date,"%m/%d/%Y")
            flag=False
        data+=[[date,author,title,subtitle]]
df=pd.DataFrame(data=data,columns=['date','author','title','subtitle'])
pd.set_option('display.max_colwidth',40)
print(df)
