# Data
At this point data is staged in files, before loading into the database.

- Book data is stored in `booklist.csv`
- Library data is in `libraries.csv`

# Sources

Email and history are sources that create intermediate files, that are enhanced to include cover image file names, and in the case of email, isbns and call numbers.

## Email

`via/data/parse_email_checkouts` The mail notices include data for date,author,title,subtitle.  These are parsed by `parse_email_checkouts` stored as `email_data.csv`.

# My reading history

The my reading history function on LCI encore has an export. In order to get the check out date, the export needs to be enhanced with data from the my history home page (which is paginated in a frame).  So far working just with a saved copy of the 1st page. 

1. Get reading history: right click on the frame and open as a new page/tab.  Then save that as `data/readinghistory.html`.

1. Download full display to local disk. This creates a file `~/Downloads/export.txt`.  Move that to the `data/` folder. 

1. Run program `via/data/parse_export.py` which creates intermediate file `my_history.csv`.

# Enhance data

## email data

The data email data is enhanced by `covers.py` to include the isbn,call_no,cover fields.

Titles and check-out dates are assumed correct and are used to determine whether to add new records (together they are unique).
Other fields may be amended in booklist.csv and they will be carried forward upon update.

Email based Work flow is 

1. put latest updated booklist in data/ (or just the headings if doing a full reset)
1. bring emails into /data/maildrop
1. run `via/data/parse_email_checkouts.py`
1. run `via/data/covers.py -f data/email_data.csv`

At that point the email_data.csv and data/covers/ have been updated

## my history

All the fields are populated directly with `via/data/parse_export.py`.  This has to prompt in some cases.  

For library it uses the home library unless there it is not on list. If there is only one, use that.  Otherwise ask.
For standard book numbers it prefers hardback 13 digit, if thats not available it will ask. (this may not be ideal)

This is also taking fields not currently used, such as publication info and format.

# Merge
`via/data/merge.py` takes the intermediate files and appends new records to  `booklist.csv`.

It uses the date and the title as they common key for this.

# to do

1. For export we capture the library to go with the call number, is there a way to do this with email?  Currently just defaulting.
2. In `covers` there are places (or maybe just one) where we take the first of a list (should it prompt?)

## Data sources

## items from checkout emails

Some authors truncated.
Several have co-authors or 'written and illustrated by' or just 'by'

## LCI

https://lci-mt.iii.com/iii/encore/search/C__St%3A%28Where%20water%20meets%20land%29%20c%3A29__Lf%3Afacetcollections%3A29%3A29%3ASouthWindsor%3A%3A__Orightresult__U?lang=eng&suite=cobalt

That's encoded version of

https://lci-mt.iii.com/iii/encore/search/C__St:(Where water meets land) c:29__Lf:facetcollections:29:29:SouthWindsor::__Orightresult__U?lang=eng&suite=cobalt

Some records don't have isbns (too old) or even though they may exist.

## ISBN

International Standard Book Number - only used since about 1970.

This site seems to be open and provides covers

https://isbnsearch.org/isbn/9781616958893

Direct get gets a recapchta

This site seems easier

https://www.biblio.com

## Search

Working ok with both author and title. 

& has to be escaped in shell as \&

### Unicode
le carré works the same as le carre on the LCI search


### Without author
Nobel got 21 hits then fails on unbound isbns. LCI does not list and isbn of first book (which is the right one)
Fixed by detecting an exiting.

But 'the last theorem' worked fine with no author

### Biblio alt page

'silverview' got 4 hits then fails on NoneType when biblio returns different page format

### 429

Had to implement retry to support 429 at biblio.

# Output

Had to store ibsns in output as '="<ibsn>"' to stop excel from converting to numbers

