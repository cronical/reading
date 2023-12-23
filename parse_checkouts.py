#!/usr/bin/env python3
'''Parse the files downloaded from email
'''
import datetime
import os
import pandas as pd

base='data'
outfile='booklist.csv'

csv_file=os.path.join(base,outfile)
merge=os.path.exists(csv_file)
if merge:
  # merge existing
  old=pd.read_csv(csv_file,parse_dates=['date'])

data=[]
mail_path=base+'/maildrop'

for item in os.listdir(mail_path):
  folder=os.path.join(mail_path,item)
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
            ta[0]=ta[0].replace(';',' :')# subtitle delimiter is wrong (at least once)
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
pd.set_option('display.max_colwidth',35)
pd.set_option('display.max_columns',10)
pd.set_option('display.width',0)
if merge:
  oix=pd.MultiIndex.from_frame(old[['date','title']])
  nix=pd.MultiIndex.from_frame(df[['date','title']])
  assert all([x in nix for x in oix]),'Based on date and title, not all old records are in new set. Inspect to see why'
  print(f"Merging with {old.shape[0]} old records")
  merged=pd.merge(df,old,how="left",on=["date","title"]) # assume date and title are clean, 
  #authors and subtitles will need to come from the old
  sel=merged.author_y.notna()
  merged.loc[sel,'author_x']=merged.loc[sel,'author_y']
  sel=merged.subtitle_y.notna()
  merged.loc[sel,'subtitle_x']=merged.loc[sel,'subtitle_y']
  merged.drop(['author_y','subtitle_y'],axis=1,inplace=True)
  df=merged.rename({'author_x':'author','subtitle_x':'subtitle'},axis=1)
  pass
df.to_csv(csv_file,index=False)
print('%d records written to %s'%(df.shape[0],csv_file))
