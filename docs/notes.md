# Data sources

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

