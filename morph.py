#!/usr/bin/python
# -*- coding: UTF-8 -*-
""" An application of Data-Oriented Parsing to Esperanto.
	Combines a syntax and a morphology corpus. """

from dopg import *
from evalb import evalb
from nltk import UnsortedChartParser, InsideChartParser, NgramModel, Nonterminal, induce_pcfg, ProbabilisticTree
from nltk.metrics.scores import precision, recall, f_measure
from bitpar import BitParChartParser
from random import sample,seed
seed()

def chapelitoj(word): #todo: replace capitals as well Ĉ Ĝ Ĥ Ĵ Ŝ Ŭ
	return unicode(word).replace(u'cx',u'ĉ').replace(u'gx',u'ĝ').replace(u'hx',
		u'ĥ').replace(u'jx',u'ĵ').replace(u'sx',u'ŝ').replace(u'ux',u'ŭ')

def malchapelitoj(word): #todo: replace capitals as well Ĉ Ĝ Ĥ Ĵ Ŝ Ŭ
	return word.replace('ĉ', 'cx').replace('ĝ', 'gx').replace('ĥ', 
		'hx').replace('ĵ', 'jx').replace('ŝ', 'sx').replace('ŭ', 'ux')

def forcepos(tree):
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
		if isinstance(tree[a], Tree) and ':' in tree[a].node and len(tree[a].node.split(':')[1]) > 0:
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
	#bigram model. there must be a way to avoid precomputing this?
	#this is not working yet has I haven't succeeded in getting nltk's
	#smoothing implemantion's to work.
	#also, a better way would be to systematically try all possibilities
	#and store the ones with a probability above a threshold
	#(there must be an algorithm for doing this efficiently)
	model = NgramModel(2, words)
	lengths = map(len, words)
	# iterate over possible number of morphemes
	for n in range(2, max(lengths)+1):
		# sample as many words as there are words with this number of morphemes
		for m in lengths.count(n):
			yield model.generate(n)

def dos3(words):
	# regex tokenizer. TBD
	pass

def segmentor(segmentd):
	""" wrap a segmentation dictionary in a naive unknown word 
	segmentation function with some heuristics 
	(phonological rules could probably improve this further) """

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

def morphology(train, top='S'):
	""" generates three DOP models for a given list of phrase structure trees:
	a syntax model, a morphology model, and a combined syntax and morphology
	model """ 
	from cPickle import dump, load
	d = GoodmanDOP((Tree(malchapelitoj(a)) for a in train), rootsymbol=top,
		parser=BitParChartParser, n=100, unknownwords='unknownwordsm',
		openclassdfsa='pos.dfsa', name='syntax', cleanup=False)
	print "built syntax model"

	mcorpus = map(malchapelitoj, open("morph.corp.txt").readlines())
	md = GoodmanDOP((forcepos(Tree(a)) for a in mcorpus), rootsymbol='W',
		wrap=True, parser=BitParChartParser, n=100, 
		unknownwords='unknownmorph', name='morphology')
	print "built morphology model"

	try:
		segmentd = load(open("segmentd.pickle", "rb"), protocol=-1)
	except:
		segmentd = dict(("".join(a), tuple(a)) for a in (Tree(a).leaves() 
			for a in mcorpus))
		print "morphology exemplars: ", " ".join(segmentd.keys())
		print "segmentation dictionary size:", len(segmentd),

		mlexicon = set(reduce(chain, segmentd.values()))
		segmentd = dos1(set(segmentd.values()))
		#restore original original words in case they were overwritten
		for a in (Tree(a).leaves() for a in mcorpus):
			segmentd["".join(a)] = tuple(a)
		print "extrapolated:", len(segmentd) #, " ".join(segmentd.keys())
		dump(segmentd, open('segmentd.pickle', 'wb'), protocol=-1)
	segment = segmentor(segmentd)
	
	try:
		mtreebank = map(Tree, open("arbobanko.train.morph").readlines())
	except:
		print "analyzing morphology of treebank"
		mtreebank = []
		for n, a in enumerate(Tree(a) for a in train):
			print '%d / %d:' % (n, len(train)-1),
			mtreebank.append(forcepos(morphmerge(a, md, map(segment, a.leaves()))))
			print
		open("arbobanko.train.morph", "w").writelines(a._pprint_flat("", "()", 
			"") + "\n" for a in mtreebank)
	#mtreebank = [m(Tree(a)) for a in train]
	#for a in mtreebank: print a
	msd = GoodmanDOP(mtreebank, rootsymbol=top, parser=BitParChartParser, 
		n=100, unknownwords='unknownmorph', name='morphsyntax', cleanup=False)
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
		""" heuristics for a plausible morphological structure """
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
		#try:
		if 1:
			#TODO?: d.parse(w) should backoff to POS supplied by morphology for
			#unknown words; but bitpar already does this with its word class
			#automata support
			print morphmerge(d.removeids(d.parse(w)), md, map(segment, w))
			#sent = ["".join(a.split('|')) for a in w]
			#for tree in d.parser.nbest_parse(w):
			#	print tree
		#except Exception as e:
		#	print "error:", e

def monato():
	""" produce the goodman reduction of the monato corpus """
	#splitting has already been done. TODO: split here.
	train = [forcepos(stripfunc(Tree(a.lower()))) for a in open("arbobanko.train")]

	# surface forms:
	test = ["%s\n\n" % "\n".join(Tree(a.lower()).leaves()) for a in open("arbobanko.gold")]
	open("arbobanko.test", "w").writelines(test)
	test = [Tree(a.lower()).leaves() for a in open("arbobanko.gold")]

	gold = [stripfunc(forcepos(Tree(a.lower()))) for a in open("arbobanko.gold")]
	# PCFG baseline
	print "inducing PCFG . . .",
	pcfg = induce_pcfg(Nonterminal("top"), reduce(chain, (a.productions() for a in train)))
	p = InsideChartParser(pcfg)
	def rule2str(a):
		if isinstance(a.rhs(), tuple):
			return "%s\t%s" % (str(a.lhs()), "\t".join(map(str, a.rhs())))
		return "%s\t%s" % (str(a.lhs()), str(a.rhs()))
	weightedrules = FreqDist(reduce(chain, (map(rule2str, a.productions()) for a in train))).items()
	p = BitParChartParser(weightedrules, set(reduce(chain, (a.leaves() for a in train))), "top", name='pcfgsyntax', cleanup=False, n=100, unknownwords='unknownwordsm', openclassdfsa='pos.dfsa')

	"""
	results, eval = [], []
	for n, (a,b) in enumerate(zip(test, gold)):
		try:
			results.append(p.parse(a))
		except ValueError as e:
			results.append(Tree("top", [Tree("nnp", [c]) for c in a]))
			print e
		try:
			eval.append(evalb(b, results[-1], parameters="COLLINS.prm") + "\n")
		except:
			eval.append("\n")
		print n, "=", results[-1]
		print eval[-1]
		if str(results[-1]) == str(b): print "match!"
	open("arbobanko.results.pcfg", "w").writelines(a._pprint_flat('', "()", "") + "\n" for a in results)
	open("arbobanko.eval.pcfg", "w").writelines(eval)
	print "done"
	"""

	print "inducing DOP reduction . . .",
	# turn cleanup off so that the grammar will not be removed
	#d = GoodmanDOP(train, rootsymbol='top', parser=BitParChartParser, name='syntax', cleanup=False, n=100, unknownwords='unknownwordsm', openclassdfsa='pos.dfsa')
	train = [str(a._pprint_flat('', '()', '')) for a in train]
	d, md, msd, segment, lexicon = morphology(train, "top")
	try:
		goldm = map(Tree, open("arbobanko.gold.morph").readlines())
	except:
		goldm = [morphmerge(a, md, map(segment, a.leaves())) for a in gold]
		open("arbobanko.gold.morph", "w").writelines(a._pprint_flat("","()",
			"") + "\n" for a in goldm)

	testm = ["%s\n\n" % "\n".join(reduce(chain, map(segment, Tree(a.lower()).leaves()))) for a in open("arbobanko.gold")]
	open("arbobanko.test.morph", "w").writelines(testm)

	
	"""
	print "parsing DOP"
	results, eval = [], []
	for n, (a,b) in enumerate(zip(test, gold)):
		try:
			results.append(d.removeids(d.mostprobableparse(a)))
		except ValueError as e:
			results.append(Tree("top", [Tree("nnp", [c]) for c in a]))
			print e
		try:
			eval.append(evalb(b, results[-1], parameters="COLLINS.prm") + "\n")
		except:
			eval.append("\n")
		print n, "=", results[-1]
		print eval[-1]
		if str(results[-1]) == str(b): print "match!"
	open("arbobanko.results", "w").writelines(a._pprint_flat('', "()", "") + "\n" for a in results)
	open("arbobanko.eval", "w").writelines(eval)
	
	print "parsing DOP w/morphology combined"
	results, eval = [], []
	for n, (a,b) in enumerate(zip(test, goldm)):
		sent = list(reduce(chain, map(segment, a)))
		try:
			results.append(msd.removeids(msd.mostprobableparse(sent)))
		except ValueError as e:
			results.append(Tree("top", [Tree("nnp", [c]) for c in sent]))
			print e
		try:
			eval.append(evalb(b, results[-1], parameters="COLLINS.prm") + "\n")
		except:
			eval.append("\n")
		print n, "=", results[-1]
		print eval[-1]
		if str(results[-1]) == str(b): print "match!"
	open("arbobanko.results.msd", "w").writelines(a._pprint_flat('', "()", "") + "\n" for a in results)
	open("arbobanko.eval.msd", "w").writelines(eval)
	"""

	import subprocess	
	print "parsing pcfg baseline"
	p1 = subprocess.Popen("bitpar -q -p -vp -b 100 -s top -u unknownwordsm -w pos.dfsa /tmp/gpcfgsyntax.pcfg /tmp/gpcfgsyntax.lex arbobanko.test arbobanko.results.pcfg".split())
	print "parsing syntax"
	p2 = subprocess.Popen("bitpar -q -p -vp -b 100 -s top -u unknownwordsm -w pos.dfsa /tmp/gsyntax.pcfg /tmp/gsyntax.lex arbobanko.test arbobanko.results".split())
	print "parsing morphosyntax"
	p3 = subprocess.Popen("bitpar -q -p -vp -b 100 -s top -u unknownmorph /tmp/gmorphsyntax.pcfg /tmp/gmorphsyntax.lex arbobanko.test.morph arbobanko.results.morph".split())

	p1.wait()
	print "processing results"
	getbest("arbobanko.results.pcfg", "arbobanko.resproc.pcfg")
	p2.wait()
	getbest("arbobanko.results", "arbobanko.resproc")
	p3.wait()
	getbest("arbobanko.results.morph", "arbobanko.resproc.morph")
	out = open("arbobanko.resproc.sepmorph", "w")
	for a in open("arbobanko.resproc").readlines():
		try:
			t = Tree(a)
		except:
			t = None
		if t:
			out.write(forcepos(morphmerge(t, md, map(segment, t.leaves())))._pprint_flat("", "()", "") + "\n")
		else:
			out.write(a)
	out.close()
	
	# add morphology to arbobanko.resproc

	#gold = map(Tree, open("arbobanko.gold").readlines())
	#goldm = map(Tree, open("arbobanko.gold.morph").readlines())
	#geteval("arbobanko.resproc", "arbobanko.resselect", "arbobanko.eval", gold)
	#geteval("arbobanko.resproc.morph", "arbobanko.resselect.morph", "arbobanko.eval.morph", goldm)

def removeids(tree):
	""" remove unique IDs introduced by the Goodman reduction """
	result = Tree.convert(tree)
	for a in tree.treepositions():
		if '@' in str(tree[a]):
			result[a].node = tree[a].node.split('@')[0]
	return result

def geteval(infile, outfile, evalfile, gold):
	eval = []
	ok = []
	for a,b in zip(gold, map(Tree, open(infile).readlines())):
		try:
			#eval.append(evalb(a, b, parameters="COLLINS.prm") + "\n")
			eval.append(evalb(a, b) + "\n")
			ok.append(b)
		except:
			eval.append("\n")
	open(outfile, "w").writelines(a._pprint_flat("","()","") + "\n" for a in ok)
	open(evalfile, "w").writelines(eval)
	
def trymap(f, list):
	for a in list:
		try: yield f(a)
		except: pass

def getbest(infile, outfile):
	""" process output of bitpar, remove ids from parse trees and choose
	the ones with highest probability. """
	import re
	results = []
	for result in open(infile).read().split("\n\n"):
		result = result.splitlines()
		probs = (float(a.split("=")[1]) for a in result[::2] if "=" in a)
		trees = trymap(Tree, result[1::2])
		p = FreqDist()
		for a in (ProbabilisticTree(b.node, b, prob=a) for a,b in zip(probs, trees)):
			p.inc(ImmutableTree.convert(removeids(a)), a.prob())
		if p.max():
	                results.append(p.max())
		else:
			results.append(None)
	def rep(a):
		if a: 
			foo = a._pprint_flat("","()","") + "\n"
			# remove CNF-conversion information
			foo = re.sub(r"\|\\<.*?\\>","", foo)
			# remove bitpar's escaping of certain chars
			return re.sub(r"\\([{}\[\]<>])",r"\1", foo)
		return "\n"
	open(outfile, "w").writelines(map(rep, results))


if __name__ == '__main__':
	import doctest
	# do doctests, but don't be pedantic about whitespace (I suspect it is the
	# militant anti-tab faction who are behind this obnoxious default)
	fail, attempted = doctest.testmod(verbose=False,
	optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
	if attempted and not fail:
		print "%d doctests succeeded!" % attempted
	#interface()	#interactive demo with toy corpus
	#toy()		#get toy corpus DOP reduction
	monato()	#get monato DOP reduction
