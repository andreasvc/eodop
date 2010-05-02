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
from nltk import Tree, FreqDist, InsideChartParser

class BitParChartParser:
	def __init__(self, weightedrules, lexicon, rootsymbol=None, unknownwords=None, cleanup=True):
		""" Interface to bitpar chart parser. Expects a list of weighted
		productions with frequencies (not probabilities).
		
		@param weightedrules: sequence of tuples with strings 
			(lhs and rhs separated by tabs, eg. "S NP VP") and
			frequencies. The reason we use this format is that
			it is close to bitpar's file format; converting a
			weighted grammar with probabilities to frequencies
			would be a detour.
		@param lexicon: set of strings belonging to the lexicon
			(ie., the set of terminals)
		@param rootsymbol: starting symbol for the grammar
		@param cleanup: boolean, when set to true the grammar will be
			removed when the BitParChartParser object is deleted.
		>>> wrules = (	("S\\tNP\\tVP", 1), \
				("NP\\tmary", 1), \
				("VP\\twalks", 1) )
		>>> p = BitParChartParser(wrules, set(("mary","walks")))
		>>> tree = p.parse("mary walks".split())
		>>> print tree
		(S (NP mary) (VP walks))

		>>> from dopg import GoodmanDOP
		>>> d = GoodmanDOP([tree], parser=InsideChartParser)
		>>> d.parser.parse("mary walks".split())
		ProbabilisticTree('S', [ProbabilisticTree('NP@1', ['mary'])
		(p=1.0), ProbabilisticTree('VP@2', ['walks']) (p=1.0)])
		(p=0.444444444444)
		>>> d = GoodmanDOP([tree], parser=BitParChartParser)
		    writing grammar
		>>> d.parser.parse("mary walks".split())
		Tree('S', [Tree('NP@1', ['mary']), Tree('VP@2', ['walks'])])

		should become: 
		(by parsing bitpar's chart output and or probabilites)
		ProbabilisticTree('S', [ProbabilisticTree('NP@1', ['mary'])
		(p=1.0), ProbabilisticTree('VP@2', ['walks']) (p=1.0)])
		(p=0.444444444444)"""

		self.grammar = weightedrules
		self.lexicon = lexicon
		self.rootsymbol = rootsymbol
		self.id = uuid1()
		self.cleanup = cleanup
		self.unknownwords = unknownwords
		self.writegrammar('/tmp/g%s.pcfg' % self.id, '/tmp/g%s.lex' % self.id)
		self.start()

	def __del__(self):
		cmd = "rm /tmp/g%s.pcfg /tmp/g%s.lex" % (self.id, self.id)
		if self.cleanup: Popen(cmd.split())
		self.stop()

	def start(self):
		# quiet, yield best parse, use frequencies
		options = "bitpar -q -b 1 -p "
		# if no rootsymbol is given, 
		# bitpar defaults to the first nonterminal in the rules
		if self.rootsymbol: options += "-s %s " % self.rootsymbol
		if self.unknownwords: options += "-u %s " % self.unknownwords
		options += "/tmp/g%s.pcfg /tmp/g%s.lex" % (self.id, self.id)
		#if self.debug: print options.split()
		self.bitpar = Popen(options.split(), stdin=PIPE, stdout=PIPE, stderr=PIPE)

	def stop(self):
		if not isinstance(self.bitpar.poll(), int):
			self.bitpar.terminate()

	def parse(self, sent):
		if isinstance(self.bitpar.poll(), int): self.start()
		result, stderr = self.bitpar.communicate("%s\n\n" % "\n".join(sent))
		try:
			return Tree(result)
		except:
			# bitpar returned some error or didn't produce output
			raise ValueError("no output. stdout: \n%s\nstderr:\n%s " % (result.strip(), stderr.strip()))

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
					yield "%s\t%s\n" % (repr(freq), rule)
					#yield "%s\t%s\t%s\n" % (repr(freq), str(lhs), 
					#			"\t".join(str(x) for x in rhs))
		#f.write(''.join(process()))
		f.writelines(process())
		def proc(lex):
			for word, tags in lex.items():
				# word	POS1 prob^Wfrequency1	POS2 freq2 ...
				#print "%s\t%s" % (word, "\t".join(' '.join(map(str, a)) for a in tags.items()))
				yield "%s\t%s\n" % (word, "\t".join(' '.join(map(str, a)) for a in tags.items()))
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
