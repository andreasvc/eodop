#!/usr/bin/python
from nltk import Tree
from random import sample

n = 15		# at most 15 words
s = 0.2		# take 20% for test corpus

# read data
corpus = open("../arbobanko.sexp").readlines()
corpus = map(Tree, corpus)

# select sents with at most n words
corpus = [a for a in corpus if len(a.leaves() <= n)]

#CNF
for a in corpus:
	a.chomsky_normal_form() #todo: sibling annotation necessary?

# split (tenfold?)
indices = range(len(corpus))
test = sample(indices, int(s * len(corpus)))
train = set(indices) - set(test)
test = [corpus[a] for a  in test]
train = [corpus[a] for a  in train]

# write out
open("../arbobanko.train", "w").writelines(train)
open("../arbobanko.test", "w").writelines(test)

# finis
