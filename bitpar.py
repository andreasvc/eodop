#!/usr/bin/python
""" Shell interface to bitpar, an efficient chart parser for (P)CFGs.
Expects bitpar to be compiled and available in the PATH.
Currently only yields the one best parse tree without its probability.
Todo: 
 - yield n best parses with probabilites (parameter)
 - parse chart output"""
from collections import defaultdict
from subprocess import Popen, PIPE
from uuid import uuid1
from nltk import Tree, ProbabilisticTree, FreqDist, InsideChartParser

class BitParChartParser:
	def __init__(self, weightedrules=None, lexicon=None, rootsymbol=None, unknownwords=None, openclassdfsa=None, cleanup=True, n=10, name=''):
		""" Interface to bitpar chart parser. Expects a list of weighted
		productions with frequencies (not probabilities).
		
		@param weightedrules: sequence of tuples with strings 
			(lhs and rhs separated by tabs, eg. "S NP VP") and
			frequencies. The reason we use this format is that
			it is close to bitpar's file format; converting a
			weighted grammar with probabilities to frequencies
			would be a detour, and bitpar wants frequencies so
			it can do smoothing.
		@param lexicon: set of strings belonging to the lexicon
			(ie., the set of terminals)
		@param rootsymbol: starting symbol for the grammar
		@param unknownwords: a file with a list of open class POS tags 
			with frequencies
		@param openclassdfsa: a deterministic finite state automaton,
			refer to the bitpar manpage.
		@param cleanup: boolean, when set to true the grammar files will be
			removed when the BitParChartParser object is deleted.
		@param name: filename of grammar files in case you want to export it,
			if not given will default to a unique identifier
		@param n: the n best parse trees will be requested
		>>> wrules = (	("S\\tNP\\tVP", 1), \
				("NP\\tmary", 1), \
				("VP\\twalks", 1) )
		>>> p = BitParChartParser(wrules, set(("mary","walks")))
		>>> tree = p.parse("mary walks".split())
		>>> print tree
		(S (NP mary) (VP walks)) (p=1.0)

		>>> from dopg import GoodmanDOP
		>>> d = GoodmanDOP([tree], parser=InsideChartParser)
		>>> d.parser.parse("mary walks".split())
		ProbabilisticTree('S', [ProbabilisticTree('NP@1', ['mary'])
		(p=1.0), ProbabilisticTree('VP@2', ['walks']) (p=1.0)])
		(p=0.444444444444)
		>>> d.parser.nbest_parse("mary walks".split(), 10)
		[ProbabilisticTree('S', [ProbabilisticTree('NP@1', ['mary']) (p=1.0),
			ProbabilisticTree('VP@2', ['walks']) (p=1.0)]) (p=0.444444444444),
		ProbabilisticTree('S', [ProbabilisticTree('NP', ['mary']) (p=1.0),
			ProbabilisticTree('VP@2', ['walks']) (p=1.0)]) (p=0.222222222222),
		ProbabilisticTree('S', [ProbabilisticTree('NP@1', ['mary']) (p=1.0),
			ProbabilisticTree('VP', ['walks']) (p=1.0)]) (p=0.222222222222),
		ProbabilisticTree('S', [ProbabilisticTree('NP', ['mary']) (p=1.0),
			ProbabilisticTree('VP', ['walks']) (p=1.0)]) (p=0.111111111111)]

		>>> d = GoodmanDOP([tree], parser=BitParChartParser)
		    writing grammar
		>>> d.parser.parse("mary walks".split())
		ProbabilisticTree('S', [Tree('NP@1', ['mary']), Tree('VP@2', ['walks'])]) (p=0.444444)
		>>> list(d.parser.nbest_parse("mary walks".split()))
		[ProbabilisticTree('S', [Tree('NP@1', ['mary']), Tree('VP@2', ['walks'])]) 
		(p=0.444444),
		ProbabilisticTree('S', [Tree('NP', ['mary']), Tree('VP@2', ['walks'])])
		(p=0.222222),
		ProbabilisticTree('S', [Tree('NP@1', ['mary']), Tree('VP', ['walks'])])
		(p=0.222222), 
		ProbabilisticTree('S', [Tree('NP', ['mary']), Tree('VP', ['walks'])])
		(p=0.111111)]

		TODO: parse bitpar's chart output / parse forest
		"""

		self.grammar = weightedrules
		self.lexicon = lexicon
		self.rootsymbol = rootsymbol
		self.name = name
		if name: self.id = name
		else: self.id = uuid1()
		self.cleanup = cleanup
		self.n = n
		self.unknownwords = unknownwords
		self.openclassdfsa = openclassdfsa
		if weightedrules and lexicon:
			self.writegrammar('/tmp/g%s.pcfg' % self.id, '/tmp/g%s.lex' % self.id)
		elif not name:
			raise ValueError("need grammar or file name")
		self.start()

	def __del__(self):
		cmd = "rm /tmp/g%s.pcfg /tmp/g%s.lex" % (self.id, self.id)
		if self.cleanup: Popen(cmd.split())
		self.stop()

	def start(self):
		# quiet, yield best parse, show viterbi prob., use frequencies
		self.cmd = "bitpar -q -b %d -vp -p " % (self.n)
		# if no rootsymbol is given, 
		# bitpar defaults to the first nonterminal in the rules
		if self.rootsymbol: self.cmd += "-s %s " % self.rootsymbol
		if self.unknownwords: self.cmd += "-u %s " % self.unknownwords
		if self.openclassdfsa: self.cmd += "-w %s " % self.openclassdfsa
		if self.name:
			# TODO ??
			self.cmd += "/tmp/g%s.pcfg /tmp/g%s.lex" % (self.id, self.id)
		else:
			self.cmd += "/tmp/g%s.pcfg /tmp/g%s.lex" % (self.id, self.id)
		#if self.debug: print self.cmd.split()
		self.bitpar = Popen(self.cmd.split(), stdin=PIPE, stdout=PIPE, stderr=PIPE)

	def stop(self):
		if not isinstance(self.bitpar.poll(), int):
			self.bitpar.terminate()

	def parse(self, sent):
		if isinstance(self.bitpar.poll(), int): self.start()
		try:
			result, stderr = self.bitpar.communicate(u"%s\n\n" % "\n".join(sent))
		except:
			self.start()
			print self.bitpar.stderr.read()
			print self.bitpar.stdout.read()
			result, stderr = self.bitpar.communicate(u"%s\n\n" % "\n".join(sent))

		if not "=" in result:
			# bitpar returned some error or didn't produce output
			raise ValueError(u"no output. stdout: \n%s\nstderr:\n%s " % (result.strip(), stderr.strip()))
		prob, tree = result.split("\n", 1)[0], result.split("\n", 2)[1]
		prob = float(prob.split("=")[1])
		tree = Tree(tree)
		return ProbabilisticTree(tree.node, tree, prob=prob)

	def nbest_parse(self, sent, n_will_be_ignored=None):
		""" n has to be specified in the constructor because it is specified
		as a command line parameter to bitpar, allowing it here would require
		potentially expensive restarts of bitpar. """
		if isinstance(self.bitpar.poll(), int): self.start()
		result, stderr = self.bitpar.communicate(u"%s\n\n" % "\n".join(sent))
		results = result.splitlines()[:-1] #strip trailing blank line
		probs = (float(a.split("=")[1]) for a in results[::2] if "=" in a)
		trees = (Tree(a) for a in results[1::2])
		return (ProbabilisticTree(b.node, b, prob=a) for a, b in zip(probs, trees))

	def writegrammar(self, f, l):
		""" write a grammar to files f and l in a format that bitpar 
		understands. f will contain the grammar rules, l the lexicon 
		with pos tags. """
		f, l = open(f, 'w'), open(l, 'w')
		lex = defaultdict(list)
		lex = defaultdict(FreqDist)
		def process():
			for rule, freq in self.grammar:
				lhs, rhs = rule.split('\t',1)[0], rule.split('\t')[1:]
				#if len(rhs) == 1 and not isinstance(rhs[0], Nonterminal):
				if rhs[0] in self.lexicon:
					#lex[rhs[0]].append(" ".join(map(repr, (lhs, freq))))
					lex[rhs[0]].inc(lhs)
				# this should NOT happen: (drop it like it's hot)
				elif len(rhs) == 0 or '' in (str(a).strip() for a in rhs): continue #raise ValueError
				else:
					# prob^Wfrequency	lhs	rhs1	rhs2
					#print "%s\t%s" % (repr(freq), rule)
					yield u"%s\t%s\n" % (repr(freq), rule)
					#yield "%s\t%s\t%s\n" % (repr(freq), str(lhs), 
					#			"\t".join(str(x) for x in rhs))
		#f.write(''.join(process()))
		f.writelines(process())
		def proc(lex):
			for word, tags in lex.items():
				# word	POS1 prob^Wfrequency1	POS2 freq2 ...
				#print "%s\t%s" % (word, "\t".join(' '.join(map(str, a)) for a in tags.items()))
				yield u"%s\t%s\n" % (word, "\t".join(' '.join(map(str, a)) for a in tags.items() if a[0].strip()))
		l.writelines(proc(lex))
		f.close()
		l.close()

if __name__ == '__main__':
	import doctest
	# do doctests, but don't be pedantic about whitespace (I suspect it is the
	# militant anti-tab faction who are behind this obnoxious default)
	fail, attempted = doctest.testmod(verbose=False,
	optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
	if attempted and not fail:
		print "%d doctests succeeded!" % attempted
