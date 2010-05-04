#!/bin/sh
from dopg import *
from bitpar import BitParChartParser

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
	""" `Data-Oriented Segmentation:' given a sequence of segmented words
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
	""" `Data-Oriented Segmentation:' given a sequence of segmented words
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

def segment(w):
	""" consult segmentation dictionary with fallback to rule-based heuristics. """
	try: return segmentd[w]
	#naive esperanto segmentation (assume root of the appropriate type)
	except KeyError:
		if w[-1] in 'jn': return segment(w[:-1]) + (w[-1],)
		if w[-1] in 'oaeu': return (w[:-1], w[-1])
		if w[-1] == 's': return (w[:-2], w[-2:])
	return (w,)

def removeids(tree):
	""" remove unique IDs introduced by the Goodman reduction """
	for a in tree.treepositions():
		if '@' in str(tree[a]):
			tree[a].node = tree[a].node.split('@')[0]
	return tree

def morphmerge(tree):
	""" merge morphology into phrase structure tree """
	copy = tree.copy(True)
	for a in tree.treepositions('leaves'):
		try:
			#print tree[a[:-1]][0],
			copy[a[:-1]] = removeids(md.parse(segment(tree[a[:-1]][0]))[0])
		except Exception as e:
			print "word:", tree[a[:-1]][0],
			print "error:", e
	return copy


def monato():
	# turn cleanup off so that the grammar will not be removed
	d = GoodmanDOP((stripfunc(cnf(Tree(a))) for a in open("arbobanko1.train")), rootsymbol='fcl', parser=BitParChartParser, cleanup=False)
	#d = GoodmanDOP((Tree(a) for a in corpus), rootsymbol='S', wrap=True)

def toy():
	from corpus import corpus
	# turn cleanup off so that the grammar will not be removed
	d = GoodmanDOP((Tree(a) for a in corpus), rootsymbol='S', parser=BitParChartParser, cleanup=False, unknownwords='unknownwords', openclassdfsa='postoy.dfsa')
	print "built syntax model"
	mcorpus = open("morph.corp.txt").readlines()
	md = GoodmanDOP((cnf(Tree(a)) for a in mcorpus), rootsymbol='W', wrap=True, parser=BitParChartParser, unknownwords='unknownmorph')
	print "built morphology model"

	segmentd = dict(("".join(a), tuple(a)) for a in (Tree(a).leaves() for a in mcorpus))
	print "morphology exemplars: ", " ".join(segmentd.keys())
	print "segmentation dictionary size:", len(segmentd),

	segmentd = dos1(set(segmentd.values()))
	#restore original original words in case they were overwritten
	for a in (Tree(a).leaves() for a in mcorpus):
		segmentd["".join(a)] = tuple(a)

	print "extrapolated:", len(segmentd) #, " ".join(segmentd.keys())

	print "analyzing morphology of treebank"
	mtreebank = []
	for n, a in enumerate(corpus):
		print '%d / %d:' % (n, len(corpus)-1),
		mtreebank.append(morphmerge(Tree(a)))
		print

	#mtreebank = [m(Tree(a)) for a in corpus]
	#for a in mtreebank: print a
	msd = GoodmanDOP(mtreebank, rootsymbol='S', parser=BitParChartParser, unknownwords='unknownmorph')
	print "built combined morphology-syntax model"

def morphology():
	from corpus import corpus
	#corpus = ["(S (NP (NN amiko)) (VP (VB venis)))"]
	d = GoodmanDOP((Tree(a) for a in corpus), rootsymbol='S', parser=BitParChartParser, unknownwords='unknownwords', openclassdfsa='postoy.dfsa')
	print "built syntax model"

	mcorpus = open("morph.corp.txt").readlines()
	md = GoodmanDOP((cnf(Tree(a)) for a in mcorpus), rootsymbol='W', wrap=True, parser=BitParChartParser, unknownwords='unknownmorph')
	print "built morphology model"

	segmentd = dict(("".join(a), tuple(a)) for a in (Tree(a).leaves() for a in mcorpus))
	print "morphology exemplars: ", " ".join(segmentd.keys())
	print "segmentation dictionary size:", len(segmentd),

	segmentd = dos1(set(segmentd.values()))
	#restore original original words in case they were overwritten
	for a in (Tree(a).leaves() for a in mcorpus):
		segmentd["".join(a)] = tuple(a)

	print "extrapolated:", len(segmentd) #, " ".join(segmentd.keys())

	print "analyzing morphology of treebank"
	mtreebank = []
	for n, a in enumerate(corpus):
		print '%d / %d:' % (n, len(corpus)-1),
		mtreebank.append(morphmerge(Tree(a)))
		print

	#mtreebank = [m(Tree(a)) for a in corpus]
	#for a in mtreebank: print a
	msd = GoodmanDOP(mtreebank, rootsymbol='S', parser=BitParChartParser, unknownwords='unknownmorph')
	print "built combined morphology-syntax model"

	#d.writegrammar('/tmp/syntax.pcfg', '/tmp/syntax.lex')
	#md.writegrammar('/tmp/morph.pcfg', '/tmp/morph.lex')
	#msd.writegrammar('/tmp/morphsyntax.pcfg', '/tmp/morphsyntax.lex')

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
				print a, md.parse(segment(a))[0]
			except Exception as e:
				print "error:", e
			
		print "morphology + syntax combined:"
		try:
			sent = list(reduce(chain, (segment(a) for a in w)))
			print sent
			print removeids(msd.parse(sent))
			#for tree in d.parser.nbest_parse(w):
			#	print tree
		except Exception as e:
			print "error", e

		print "syntax & morphology separate:"
		try:
			#TODO: d.parse(w) should backoff to POS supplied by morphology for unknown words
			print morphmerge(removeids(d.parse(w)))
			#sent = ["".join(a.split('|')) for a in w]
			#for tree in d.parser.nbest_parse(w):
			#	print tree
		except Exception as e:
			print "error:", e

if __name__ == '__main__':
	import doctest
	# do doctests, but don't be pedantic about whitespace (I suspect it is the
	# militant anti-tab faction who are behind this obnoxious default)
	fail, attempted = doctest.testmod(verbose=False,
	optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
	if attempted and not fail:
		print "%d doctests succeeded!" % attempted
	#morphology()   #interactive demo with toy corpus
	monato()        #get monato DOP reduction
