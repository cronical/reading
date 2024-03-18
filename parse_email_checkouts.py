#!/usr/bin/env python3
'''Parse the files downloaded from email
This method is problematic due to truncation in the email for items with long titles.
'''
import datetime
import logging
import os
import pandas as pd


logging.basicConfig(level=logging.DEBUG)
logger=logging.getLogger(__name__)

base='data'
outfile='email_data.csv'

email_data_file=os.path.join(base,outfile)

def split_ta(line):
	# returns title, subtitle, author
	ta=line.split(' / ')
	author=None
	if len(ta)==2:
		author=ta[1]# was from_title(ta[1]).flat_authors()
	ta[0]=ta[0].replace(';',' :')# subtitle delimiter is wrong (at least once)
	title=ta[0].split(' : ')
	subtitle=None
	if len(title)==2:
		subtitle=title[1]
	return title[0].strip(),subtitle,author

data=[]
mail_path=base+'/maildrop'

for item in os.listdir(mail_path):
	folder=os.path.join(mail_path,item)
	if os.path.isdir(folder):
		file=os.path.join(folder,"text.txt")
		if os.path.exists(file):
			logger.debug(f"Processing {file}")
			with open(file) as f:
				date=None
				flag=False
				titles=[]
				for line in f:
					if line.startswith('Title:'):
						titles+=[line[6:].strip()]
					if line.startswith('Total items'):
						n=int(line.split(':')[1])
						if n!=len(titles):
							logger.error(f"Captured title count ({len(titles)}) does not match to checked out count ({n})")
						flag=True
						continue
					if flag:
						date=line.split(' ')[0]
						date=datetime.datetime.strptime(date,"%m/%d/%Y")
						flag=False
				for title in titles:
					title,subtitle,author=split_ta(title)
					data+=[[date,author,title,subtitle]]
					logger.debug(f"		{title}")

df=pd.DataFrame(data=data,columns=['date','author','title','subtitle'])
pd.set_option('display.max_colwidth',35)
pd.set_option('display.max_columns',10)
pd.set_option('display.width',0)

df.to_csv(email_data_file,index=False)
print('%d records written to %s'%(df.shape[0],email_data_file))
