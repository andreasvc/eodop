# remove blank lines (bitpar outputs an empty line between each sentence)
# then remove errors (but keep an empty line to keep the results aligned with the gold corpus!)
# remove IDs introduced by the goodman reduction
egrep -v '^$' $1 \
| sed -s 's/^No parse.*$//' \
| sed -s 's/@[0-9]\+//'

