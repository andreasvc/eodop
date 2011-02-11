#!/usr/bin/python
from nltk import Tree
from random import sample
from morph import forcepos, stripfunc

print "splitting original corpus . . .",

n = 100		# at most n words
s = 0.2		# take 20% for test corpus

# read data
corpus = open("../arbobanko1.sexp").readlines()
corpus = map(Tree, corpus)

# select sents with at most n words, add POS tags when necessary, 
# strip function annotations (SUBJ:np => np)
corpus = [stripfunc(forcepos(a)) for a in corpus if len(a.leaves()) <= n]

# split (tenfold?)
indices = range(len(corpus))
test = sample(indices, int(s * len(corpus)))
train = set(indices) - set(test)
test = [corpus[a] for a  in test]
train = [corpus[a] for a  in train]

#CNF
for a in train:
	a.chomsky_normal_form() #todo: sibling annotation necessary?

# write out
open("../arbobanko.train", "w").write("\n".join(a._pprint_flat('', "()", "") for a in train).replace("( :)", "(: :)"))
open("../arbobanko.gold", "w").write("\n".join(a._pprint_flat('', "()", "") for a in test).replace("( :)", "(: :)").lower())
# bitpar wants one word per line, sents separated by two newlines
open("../arbobanko.test", "w").write("\n\n".join("\n".join(a.leaves()) for a in test))

# finis
print "done"
