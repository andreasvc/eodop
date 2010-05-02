# -*- coding: utf-8 -*-
"""DOP1 implementation. Andreas van Cranenburgh <andreas@unstable.nl>
TODOs: unicode support (replace str and repr calls)"""
#import psyco
#psyco.full()

from collections import defaultdict
from itertools import chain, count
#from math import log #do something with logprobs instead?
from nltk import Production, WeightedProduction, WeightedGrammar, FreqDist
from nltk import Tree, Nonterminal, InsideChartParser, UnsortedChartParser
from bitpar import BitParChartParser

def cartprod(a, b):
	""" cartesian product of two sequences """
	for x in a:
		for y in b:
			yield x, y

def cartpi(seq):
	""" produce a flattened fold using cartesian product as operator

	>>> list(cartpi( ( (1,2), (3,4), (5,6) ) ) )
	[(1, 3, 5), (2, 3, 5), (1, 4, 5), (2, 4, 5), (1, 3, 6), (2, 3, 6), 
	(1, 4, 6), (2, 4, 6)] """
	if len(seq) == 0: return ((), )
	else: return ((a,) + b for b in cartpi(seq[1:]) for a in seq[0])

#NB: the following code is equivalent to nltk.Tree.productions, except for accepting unicode
def productions(tree):
	"""
	Generate the productions that correspond to the non-terminal nodes of the tree.
	For each subtree of the form (P: C1 C2 ... Cn) this produces a production of the
	form P -> C1 C2 ... Cn.
		@rtype: list of C{Production}s
	"""

	if not (isinstance(tree.node, str) or isinstance(tree.node, unicode)):
		raise TypeError, 'Productions can only be generated from trees having node labels that are strings'

	prods = [Production(Nonterminal(tree.node), tree._child_names())]
	for child in tree:
		if isinstance(child, Tree):
			prods += productions(child)
	return prods

class GoodmanDOP:
	def __init__(self, treebank, rootsymbol='S', wrap=False, parser=InsideChartParser, cleanup=True):
		""" initialize a DOP model given a treebank. uses the Goodman
		reduction of a STSG to a PCFG.  after initialization,
		self.parser will contain an InsideChartParser.

		>>> tree = Tree("(S (NP mary) (VP walks))")
		>>> d = GoodmanDOP([tree])
		>>> print d.grammar
			Grammar with 8 productions (start state = S)
				NP -> 'mary' [1.0]
				NP@1 -> 'mary' [1.0]
				VP -> 'walks' [1.0]
				VP@2 -> 'walks' [1.0]
				S -> NP VP [0.111111111111]
				S -> NP VP@2 [0.222222222222]
				S -> NP@1 VP [0.222222222222]
				S -> NP@1 VP@2 [0.444444444444]	
		>>> print d.parser.parse("mary walks".split())
		(S (NP@1 mary) (VP@2 walks)) (p=0.444444444444)		
		
		@param treebank: a list of Tree objects. Caveat lector:
			terminals may not have (non-terminals as) siblings.
		@param wrap: boolean specifying whether to add the start symbol
			to each tree
		@param parser: a class which will be instantiated with the DOP 
			model as its grammar. Support BitParChartParser.
		
		instance variables:
		- self.grammar a WeightedGrammar containing the PCFG reduction
		- self.fcfg a list of strings containing the PCFG reduction 
		  with frequencies instead of probabilities
		- self.parser an InsideChartParser object
		- self.exemplars dictionary of known parse trees (memoization)"""
		nonterminalfd, ids = FreqDist(), count()
		cfg = FreqDist()
		self.exemplars = {}
		if wrap:
			# wrap trees in a common root symbol (eg. for morphology)
			treebank = [Tree(rootsymbol, [a]) for a in treebank]
		# add unique IDs to nodes
		utreebank = list((tree, self.decorate_with_ids(tree, ids)) for tree in treebank)
		lexicon = set(reduce(chain, (a.leaves() for a,b in utreebank)))
		# count node frequencies
		for tree,utree in utreebank:
			#self.exemplars[tuple(tree.leaves())] = tree
			self.nodefreq(tree, nonterminalfd)
			self.nodefreq(utree, nonterminalfd)
			#cfg.extend(self.goodman(tree, utree))
			#cfg.update(zip(self.goodmanfd(tree, ids, nonterminalfd), ones))
			#cfg.extend(self.goodmanfd(tree, ids, nonterminalfd))
		#print type(parser) == type(InsideChartParser)
		#print type(parser) is type(InsideChartParser)
		if type(parser) == type(BitParChartParser):
			# this takes the most time, produce CFG rules:
			cfg = FreqDist(reduce(chain, (self.goodman(tree, utree) for tree, utree in utreebank)))
			# annotate rules with frequencies
			self.fcfg = self.frequencies(cfg, nonterminalfd)
			print "writing grammar"
			self.parser = BitParChartParser(self.fcfg, lexicon, rootsymbol, cleanup=False)
		else:
			cfg = FreqDist(reduce(chain, (self.goodman(tree, utree, False) for tree, utree in utreebank)))
			self.grammar = WeightedGrammar(Nonterminal(rootsymbol),
				self.probabilities(cfg, nonterminalfd))
			self.parser = InsideChartParser(self.grammar)
			
		#stuff for self.mccparse
		#the highest id
		#self.addresses = ids.next()
		#a list of interior + exterior nodes, 
		#ie., non-terminals with and without ids
		#self.nonterminals = nonterminalfd.keys()
		#a mapping of ids to nonterminals without their IDs
		#self.nonterminal = dict(a.split("@")[::-1] for a in 
		#	nonterminalfd.keys() if "@" in a)

		#clean up
		del cfg, nonterminalfd

	def goodmanfd(self, tree, ids, nonterminalfd):
		utree = self.decorate_with_ids(tree, ids)
		self.nodefreq(tree, nonterminalfd)
		self.nodefreq(utree, nonterminalfd)
		return self.goodman(tree, utree)
	
	def decorate_with_ids(self, tree, ids):
		""" add unique identifiers to each non-terminal of a tree.

		>>> tree = Tree("(S (NP mary) (VP walks))")
		>>> d = GoodmanDOP([tree])
		>>> d.decorate_with_ids(tree, count())
		Tree('S@0', [Tree('NP@1', ['mary']), Tree('VP@2', ['walks'])])

			@param ids: an iterator yielding a stream of IDs"""
		utree = tree.copy(True)
		for a in utree.subtrees():
			a.node = "%s@%d" % (a.node, ids.next())
		return utree
	
	def nodefreq(self, tree, nonterminalfd, leaves=1):
		"""count frequencies of nodes by calculating the number of
		subtrees headed by each node. updates "nonterminalfd" as 
		a side effect

		>>> fd = FreqDist()
		>>> tree = Tree("(S (NP mary) (VP walks))")
		>>> d = GoodmanDOP([tree])
		>>> d.nodefreq(tree, fd)
		9
		>>> fd.items()
		[('S', 9), ('NP', 2), ('VP', 2), ('mary', 1), ('walks', 1)]

			@param nonterminalfd: the FreqDist to store the counts in."""
		if isinstance(tree, Tree) and len(tree) > 0:
			n = reduce((lambda x,y: x*y), 
				(self.nodefreq(x, nonterminalfd) + 1 for x in tree))
			nonterminalfd.inc(tree.node, count=n)
			return n
		else:
			nonterminalfd.inc(str(tree), count=leaves)
			return leaves

	def goodman(self, tree, utree, bitparfmt=True):
		""" given a parsetree from a treebank, yield a goodman
		reduction of eight rules per node (in the case of a binary tree).

		>>> tree = Tree("(S (NP mary) (VP walks))")
		>>> d = GoodmanDOP([tree])
		>>> utree = d.decorate_with_ids(tree, count())
		>>> sorted(d.goodman(tree, utree, False))
		[(NP, ('mary',)), (NP, ('mary',)), (NP@1, ('mary',)), 
		(NP@1, ('mary',)), (S, (NP, VP)), (S, (NP, VP@2)), (S, (NP@1, VP)), 
		(S, (NP@1, VP@2)), (VP, ('walks',)), (VP, ('walks',)), 
		(VP@2, ('walks',)), (VP@2, ('walks',))]
		"""
		# linear: nr of nodes
		sep = "\t"
		for p, up in zip(tree.productions(), utree.productions()): 
			# THIS SHOULD NOT HAPPEN:
			if len(p.rhs()) == 0: raise ValueError
			if len(p.rhs()) == 1: rhs = (p.rhs(), up.rhs())
			#else: rhs = cartprod(*zip(p.rhs(), up.rhs()))
			else: rhs = cartpi(zip(p.rhs(), up.rhs()))

			# constant factor: 8
			#for l, r in cartpi(((p.lhs(), up.lhs()), rhs)):
			for l, r in cartprod((p.lhs(), up.lhs()), rhs):
				#yield Production(l, r)
				if bitparfmt:
					yield sep.join((str(l), sep.join(map(str, r))))
				else:
					yield l, r
				# yield a delayed computation that also gives the frequencies
				# given a distribution of nonterminals
				#yield (lambda fd: WeightedProduction(l, r, prob= 
				#	reduce(lambda x,y: x*y, map(lambda z: '@' in z and 
				#	fd[z] or 1, r)) / float(fd[l])))
	
	def probabilities(self, cfg, fd):
		"""merge cfg and frequency distribution into a pcfg with the right
		probabilities.

			@param cfg: a list of Productions
			@param nonterminalfd: a FreqDist of (non)terminals (with and
			without IDs)""" 
		#return [a(nonterminalfd) for a in cfg)
		def prob(l, r):
			return reduce((lambda x,y: x*y), map((lambda z: '@' in str(z) 
				and fd[str(z)] or 1), r)) / float(fd[str(l)])
		# format expected by mccparse()
		#self.pcfg = dict((Production(l, r), (reduce((lambda x,y: x*y), 
		#	map((lambda z: '@' in (type(z) == Nonterminal and z.symbol() or z) 
		#	and nonterminalfd[z] or 1), r)) / nonterminalfd[l]))
		#	for l, r in set(cfg))

		# merge identical rules:
		#return [WeightedProduction(rule[0], rule[1:], prob=freq*prob(rule[0], rule[1:])) for rule, freq in ((rule.split('\t'), freq) for rule,freq in cfg.items())]
		return [WeightedProduction(l, r, prob=freq*prob(l, r)) for (l,r),freq in cfg.items()]
		# do not merge identical rules
		#return [WeightedProduction(l, r, prob=prob(l, r)) for l, r in cfg]
	
	def frequencies(self, cfg, fd):
		"""merge cfg and frequency distribution into a list of weighted 
		productions with frequencies as weights (as expected by bitpar).

			@param cfg: a list of Productions
			@param nonterminalfd: a FreqDist of (non)terminals (with and
			without IDs)""" 
		def prob(r):
			return reduce((lambda x,y: x*y), map((lambda z: '@' in str(z) 
				and fd[str(z)] or 1), r), 1)

		# merge identical rules:
		#cfgfd = FreqDist(cfg)
		#for rule,cnt in cfgfd.items():
		#	cfgfd.inc(rule, count=(cnt-1) * prob(*rule))
		#return cfgfd
		return ((rule, freq * reduce((lambda x,y: x*y), map((lambda z: '@' in str(z) and fd[str(z)] or 1), rule.split('\t')[1:]), 1)) for rule, freq in cfg.items())
			#rule.append(prob(*rule))
		#return [(rule, prob(rule[1])) for rule in cfg]

	def parse(self, sent):
		""" memoize parse trees. TODO: maybe add option to add every
		parse tree to the set of exemplars, ie., incremental learning. """
		try:
			return self.exemplars[tuple(sent)]
		except KeyError:
			self.exemplars[tuple(sent)] = self.parser.parse(sent)
			return self.exemplars[tuple(sent)]

	def mccparse(self, sent):
		""" not working yet. almost verbatim translation of Goodman's (1996)
		most constituents correct parsing algorithm, except for python's
		zero-based indexing. needs to be modified to return the actual parse
		tree. expects a pcfg in the form of a dictionary from productions to
		probabilities """ 
		def g(s, t, x):
			def f(s, t, x):
				return self.pcfg[Production(rootsymbol, 
					sent[1:s] + [x] + sent[s+1:])]
			def e(s, t, x): 
				return self.pcfg[Production(x, sent[s:t+1])]
			return f(s, t, x) * e(s, t, x ) / e(1, n, rootsymbol)

		sumx = defaultdict(int) #zero
		maxc = defaultdict(int) #zero
		for length in range(2, len(sent)+1):
			for s in range(1, len(sent) + length):
				t = s + length - 1
				for x in self.nonterminals:
					sumx[x] = g(s, t, x)
				for k in range(self.addresses):
					#ordered dictionary here
					x = self.nonterminal[k]
					sumx[x] += g(s, t, "%s@%d" % (x, k))
				max_x = max(sumx[x] for x in self.nonterminals)
				#for x in self.nonterminals:
				#	max_x = argmax(sumx, x) #???
				best_split = max(maxc[(s,r)] + maxc[(r+1,t)] 
									for r in range(s, t))
				#for r in range(s, t):
				#	best_split = max(maxc[(s,r)] + maxc[(r+1,t)])
				maxc[(s,t)] = sumx(max_x) + best_split
		return maxc[(1, len(sent) + 1)]
				
def main():
	""" a basic REPL for testing """
	corpus = """(S (NP John) (VP (V likes) (NP Mary)))
(S (NP Peter) (VP (V hates) (NP Susan)))
(S (NP Harry) (VP (V eats) (NP pizza)))
(S (NP Hermione) (VP (V eats)))""".split('\n')
	corpus = [Tree(a) for a in corpus]
	#d = GoodmanDOP(corpus, rootsymbol='S')
	d = GoodmanDOP(corpus, rootsymbol='S', parser=BitParChartParser)
	#print d.grammar
	print "corpus"
	for a in corpus: print a
	w = "foo!"
	while w:
		print "sentence:",
		w = raw_input().split()
		try:
			print d.parse(w)
		except Exception as e:
			print "error", e

if __name__ == '__main__': 
	import doctest
	# do doctests, but don't be pedantic about whitespace (I suspect it is the
	# militant anti-tab faction who are behind this obnoxious default)
	fail, attempted = doctest.testmod(verbose=False,
	optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
	if attempted and not fail:
		print "%d doctests succeeded!" % attempted
	main()
