#!/usr/bin/python
""" An application of Data-Oriented Parsing to Esperanto.
	Combines a syntax and a morphology corpus. """

from dopg import *
from nltk import UnsortedChartParser
from bitpar import BitParChartParser
from random import sample,seed
seed()

def cnf(tree):
	""" make sure all terminals have POS tags; 
	invent one if necessary ("parent_word") """
	result = tree.copy(True)
	for a in tree.treepositions('leaves'):
		if len(tree[a[:-1]]) != 1:
			result[a] = Tree("%s_%s" % (tree[a[:-1]].node, tree[a]), [tree[a]])
	return result

def stripfunc(tree):
	""" strip all function labels from a tree with labels of
	the form "function:form", eg. S:np for subject, np. """
	for a in tree.treepositions():
		if isinstance(tree[a], Tree) and ':' in tree[a].node:
			tree[a].node = tree[a].node.split(':')[1]
	return tree

def dos(words):
	""" `Data-Oriented Segmentation 1': given a sequence of segmented words
	(ie., a sequence of morphemes), produce a dictionary with extrapolated
	segmentations (mapping words to sequences of morphemes). 
	Assumes non-ambiguity. 
	Method: cartesian product of all possible morphemes at position 0..n, where n is maximum word length."""
	l = [len(a) for a in words]
	morph_at = dict((x, set(a[x] for a,n in zip(words, l) if n > x)) 
						for x in range(0, max(l)))
	return dict(("".join(a), a) for a in 
		reduce(chain, (cartpi([morph_at[x] for x in range(n)]) 
			for n in range(min(l), max(l)))))
def dos1(words):
	""" `Data-Oriented Segmentation 2': given a sequence of segmented words
	(ie., a sequence of morphemes), produce a dictionary with extrapolated
	segmentations (mapping words to sequences of morphemes). 
	Discards ambiguous results.
	Method: cartesian product of all words with the same number of morphemes. """
	l = [len(a) for a in words]
	return dict(("".join(a), a) for a in 
		reduce(chain, (cartpi(zip(*(w for w, m in zip(words, l) if m == n)))
			for n in range(min(l), max(l)))))
def dos2(words):
	#bigram model. TBD
	pass

def dos3(words):
	# regex tokenizer. TBD
	pass

def segmentor(segmentd):
	""" wrap a segmentation dictionary in a naive unknown word 
	segmentation function """

	# this unspeakable hack is necessary because python does not have
	# proper support for lexical closures.
	def s(segmentd):
		def f(w):
			""" consult segmentation dictionary with fallback to rule-based heuristics. """
			try: return segmentd[w]
			#naive esperanto segmentation (assume root of the appropriate type)
			except KeyError:
				if w[-1] in 'jn': return f(w[:-1]) + (w[-1],)
				if w[-1] in 'oaeu': return (w[:-1], w[-1])
				if w[-1] == 's': return (w[:-2], w[-2:])
				if w[-1] == 'i': return (w[:-1], w[-1])
			#last resort, unanalyzable word, e.g. proper noun
			return (w,)
		return f
	return s(segmentd)

def morphmerge(tree, md, segmented):
	""" merge morphology into phrase structure tree """
	copy = tree.copy(True)
	for a,w in zip(tree.treepositions('leaves'), segmented):
		try:
			# MPD: copy[a[:-1]] = md.removeids(md.parse(w))[0]
			# MPP
			copy[a[:-1]] = md.mostprobableparse(w)[0]
		except Exception as e:
			print "word:", tree[a[:-1]][0], "segmented", w
			print "error:", e
	return copy

def morphology(train):
	""" an interactive interface to the toy corpus """
	d = GoodmanDOP((Tree(a) for a in train), rootsymbol='S', parser=BitParChartParser, n=100, unknownwords='unknownwords', openclassdfsa='postoy.dfsa', name='syntax')
	print "built syntax model"

	mcorpus = open("morph.corp.txt").readlines()
	md = GoodmanDOP((cnf(Tree(a)) for a in mcorpus), rootsymbol='W', wrap=True, parser=BitParChartParser, n=100, unknownwords='unknownmorph', name='morphology')
	print "built morphology model"

	segmentd = dict(("".join(a), tuple(a)) for a in (Tree(a).leaves() for a in mcorpus))
	print "morphology exemplars: ", " ".join(segmentd.keys())
	print "segmentation dictionary size:", len(segmentd),

	mlexicon = set(reduce(chain, segmentd.values()))
	segmentd = dos1(set(segmentd.values()))
	#restore original original words in case they were overwritten
	for a in (Tree(a).leaves() for a in mcorpus):
		segmentd["".join(a)] = tuple(a)
	segment = segmentor(segmentd)
	
	print "extrapolated:", len(segmentd) #, " ".join(segmentd.keys())

	print "analyzing morphology of treebank"
	mtreebank = []
	for n, a in enumerate(Tree(a) for a in train):
		print '%d / %d:' % (n, len(train)-1),
		mtreebank.append(morphmerge(a, md, map(segment, a.leaves())))
		print

	#mtreebank = [m(Tree(a)) for a in train]
	#for a in mtreebank: print a
	msd = GoodmanDOP(mtreebank, rootsymbol='S', parser=BitParChartParser, n=100, unknownwords='unknownmorph', name='morphsyntax')
	print "built combined morphology-syntax model"

	return d, md, msd, segment, mlexicon

def toy():
	#syntax treebank
	from corpus import corpus
	test = sample(corpus, int(0.1 * len(corpus)))
	train = [a for a in corpus if a not in test]	
	d, md, msd, segment, lexicon = morphology(train)

	#evaluation
	for tree in (Tree(a) for a in []): #test
		w = tree.leaves()
		#morphology + syntax combined
		try:
			sent = list(reduce(chain, map(segment, w)))
			print sent
			print msd.removeids(msd.mostprobableparse(sent))
		except Exception as e:
			print "error", e

		#syntax & morphology separate
		try:
			print morphmerge(d.removeids(d.mostprobableparse(w)), md, map(segment, w))
		except Exception as e:
			print "error:", e

	def guess(w):
		""" guess a plausible morphological structure """
		if w[:3] == 'mal':
			a = guess(w[3:])
			return "(%s (%s (A mal) %s) %s)" % (a[1:a.index(' ')], a[a.index(' ')+1:a.index(' ', 2)], a[a.index(' '):-1], a[:-2])
		if w[-1] == 'n':
			a = guess(w[:-1])
			return "(%s %s n)" % (a[1:a.index(' ')], a)
		if w[-1] == 'j':
			a = guess(w[:-1])
			return "(%s %s j)" % (a[1:a.index(' ')], a)
		if w[-1] == 'o':
			return "(NN (N %s) o)" % w[:-1]
		if w[-1] == 'a':
			return "(JJ (J %s) a)" % w[:-1]
		if w[-1] == 'e':
			return "(RB (R %s) e)" % w[:-1]
		if w[-1] == 'i':
			return "(VB (V %s) i)" % w[:-1]
		if w[-1] == 's':
			return "(VB (V %s) %s)" % (w[:-2], w[-2:])
		return "(%s %s)" % (w, w)

	for a in open("fundamento.vocab"):
		if len(a) <= 1:	continue
		try: s = segment(a[:-1].lower())
		except:
			s = None
			print "( %s)" % a[:-1].lower()
		if s and all(a in lexicon for a in s):
			try: print md.removeids(md.mostprobableparse(s))[0]
			except:
				try: print guess(a[:-1])
				except: print "( %s)" % a[:-1].lower()
		else: 
			try: print guess(a[:-1])
			except: print "( %s)" % a[:-1].lower()

def interface():
	from corpus import corpus
	d, md, msd, segment, lexicon = morphology(corpus)

	#print d.grammar
	w = "foo!"

	# basic REPL
	while w:
		print "sentence:",
		w = raw_input().split()
		if not w: break	#quit

		print "morphology:"
		for a in w:
			try:
				print a, md.mostprobableparse(segment(a))[0]
			except Exception as e:
				print "error:", e
			
		print "morphology + syntax combined:"
		try:
			sent = list(reduce(chain, map(segment, w)))
			print sent
			print msd.removeids(msd.mostprobableparse(sent))
			#for tree in d.parser.nbest_parse(w):
			#	print tree
		except Exception as e:
			print "error", e

		print "syntax & morphology separate:"
		try:
			#TODO?: d.parse(w) should backoff to POS supplied by morphology for
			#unknown words; but bitpar already does this with its word class
			#automata support
			print morphmerge(d.removeids(d.parse(w)), md, map(segment, w))
			#sent = ["".join(a.split('|')) for a in w]
			#for tree in d.parser.nbest_parse(w):
			#	print tree
		except Exception as e:
			print "error:", e

def monato():
	""" produce the goodman reduction of the full monato corpus """
	# turn cleanup off so that the grammar will not be removed
	d = GoodmanDOP((stripfunc(cnf(Tree(a))) for a in open("arbobanko1.train")), rootsymbol='fcl', parser=BitParChartParser, name='syntax', cleanup=False)
	#d = GoodmanDOP((Tree(a) for a in corpus), rootsymbol='S', wrap=True)

if __name__ == '__main__':
	import doctest
	# do doctests, but don't be pedantic about whitespace (I suspect it is the
	# militant anti-tab faction who are behind this obnoxious default)
	fail, attempted = doctest.testmod(verbose=False,
	optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
	if attempted and not fail:
		print "%d doctests succeeded!" % attempted
	#interface()	#interactive demo with toy corpus
	toy()		#get toy corpus DOP reduction
	#monato()	#get monato DOP reduction
