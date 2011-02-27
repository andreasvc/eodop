#!/usr/bin/python
""" Shell interface to bitpar, an efficient chart parser for (P)CFGs.
Expects bitpar to be compiled and available in the PATH.
Currently only yields the one best parse tree without its probability.
Todo: 
 - yield n best parses with probabilites (parameter)
 - parse chart output"""
from collections import defaultdict
from subprocess import Popen, PIPE
from pexpect import spawn
from commands import getoutput
from time import sleep
from uuid import uuid1
from nltk import Tree, ProbabilisticTree, FreqDist, InsideChartParser
import threading, fcntl, os, re

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
		ProbabilisticTree('S', [ProbabilisticTree('NP', ['mary'])
		(p=1.0), ProbabilisticTree('VP@2', ['walks']) (p=1.0)])	(p=0.25)
		>>> d.parser.nbest_parse("mary walks".split(), 10)
		[ProbabilisticTree('S', [ProbabilisticTree('NP', ['mary']) (p=1.0),
			ProbabilisticTree('VP@2', ['walks']) (p=1.0)]) (p=0.25),
		ProbabilisticTree('S', [ProbabilisticTree('NP', ['mary']) (p=1.0),
			ProbabilisticTree('VP', ['walks']) (p=1.0)]) (p=0.25),
		ProbabilisticTree('S', [ProbabilisticTree('NP@1', ['mary']) (p=1.0),
			ProbabilisticTree('VP@2', ['walks']) (p=1.0)]) (p=0.25),
		ProbabilisticTree('S', [ProbabilisticTree('NP@1', ['mary']) (p=1.0),
			ProbabilisticTree('VP', ['walks']) (p=1.0)]) (p=0.25)]

		>>> d = GoodmanDOP([tree], parser=BitParChartParser)
		>>> d.parser.parse("mary walks".split())
		ProbabilisticTree('S', [Tree('NP', ['mary']), Tree('VP', ['walks'])]) (p=0.25)
		>>> list(d.parser.nbest_parse("mary walks".split()))
		[ProbabilisticTree('S', [Tree('NP', ['mary']), Tree('VP', ['walks'])]) (p=0.25), 
		ProbabilisticTree('S', [Tree('NP', ['mary']), Tree('VP@2', ['walks'])]) (p=0.25), 
		ProbabilisticTree('S', [Tree('NP@1', ['mary']), Tree('VP', ['walks'])]) (p=0.25), 
		ProbabilisticTree('S', [Tree('NP@1', ['mary']), Tree('VP@2', ['walks'])]) (p=0.25)]
		>>> list(d.parser.batch_parse(["mary walks".split()], n=10))
		[[ProbabilisticTree('S', [Tree('NP', ['mary']), Tree('VP', ['walks'])]) (p=0.25), 
		ProbabilisticTree('S', [Tree('NP', ['mary']), Tree('VP@2', ['walks'])]) (p=0.25), 
		ProbabilisticTree('S', [Tree('NP@1', ['mary']), Tree('VP', ['walks'])]) (p=0.25), 
		ProbabilisticTree('S', [Tree('NP@1', ['mary']), Tree('VP@2', ['walks'])]) (p=0.25)]]

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
		if self.cleanup or not self.name: Popen(cmd.split())
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
		#self.bitpar = Popen(self.cmd.split(), stdin=PIPE, stdout=PIPE, stderr=PIPE)
		self.bitpar = spawn(self.cmd)
		self.bitpar.setecho(False)
		# allow bitpar to initialize; just to be sure
		sleep(1)
		try: self.bitpar.read_nonblocking(size=1024, timeout=0)
		except: pass
	def stop(self):
		if not self.bitpar.terminated: self.bitpar.terminate()

	def parse(self, sent):
		return self.nbest_parse(sent).next()
		"""
		if self.bitpar.terminated: self.start()
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
		prob, tree = result.split("\n", 1)[0], result.split("\n", 2)[1].replace('\\','')
		prob = float(prob.split("=")[1])
		tree = Tree(tree)
		return ProbabilisticTree(tree.node, tree, prob=prob)
		"""

	def nbest_parse(self, sent, n_will_be_ignored=None):
		""" n has to be specified in the constructor because it is specified
		as a command line parameter to bitpar, allowing it here would require
		potentially expensive restarts of bitpar. """
		"""f = "/tmp/%s" % uuid1()
		open(f, "w").write("%s\n\n" % "\n".join(sent))
		bitpar = Popen((self.cmd + " " + f).split(), stdin=PIPE, stdout=PIPE, stderr=PIPE)
		output = bitpar.stdout.read().splitlines() """
		if self.bitpar.terminated: self.start()
		self.bitpar.send("\n".join(sent) + "\n\n")
		output = ""
		while not output.endswith("\r\n\r\n"):
			output += self.bitpar.read_nonblocking(size=32767, timeout=30)
		# remove bitpar's escaping (why does it do that?), strip trailing blank line
		results = re.sub(r"\\([/{}\[\]<>'\$])", r"\1", output).splitlines()[:-1]
		probs = (float(a.split("=")[1]) for a in results[::2] if "=" in a)
		trees = (Tree(a) for a in results[1::2])
		#Popen(("rm %s" % f).split())
		return (ProbabilisticTree(b.node, b, prob=a) for a, b in zip(probs, trees))

	def batch_parse(self, sents, n=1):
		"""Batch parse a series of sentences. Expects a lists of
		sentences in the form of lists of words.  Returns a list of lists, each being
		up to n resulting trees.
		Caveat: if you haven't supplied an unknown words file, bitpar
		will stop parsing after the first unknown word; if a sentence cannot
		be parsed for another reason, bitpar will continue. """
		f = "/tmp/%s" % uuid1()
		open(f, "w").writelines("%s\n\n" % "\n".join(sent) for sent in sents)
		bitpar = Popen((self.cmd + " " + f).split(), stdout=PIPE, stderr=PIPE)
		output = bitpar.stdout.read()
		output = re.sub(r"\\([/{}\[\]<>'\$])", r"\1", output).split("\n\n")[:-1]
		result = []
		for a in output:
			results = a.splitlines()
			if "No parse" in results[0]:
				result.append(( (), () ))
				continue
			probs = (float(a.split("=")[1]) for a in results[::2] if "=" in a)
			trees = (Tree(a) for a in results[1::2])
			result.append((probs, trees))
		Popen(("rm %s" % f).split())
		return ([ProbabilisticTree(b.node, b, prob=a) for a, b in zip(probs, trees)] for probs, trees in result)
		
	def writegrammar(self, f, l):
		""" write a grammar to files f and l in a format that bitpar 
		understands. f will contain the grammar rules, l the lexicon 
		with pos tags. """
		f, l = open(f, 'w'), open(l, 'w')
		lex = defaultdict(FreqDist)
		def process():
			for rule, freq in self.grammar:
				lhs, rhs = rule.split('\t',1)[0], rule.split('\t')[1:]
				#if len(rhs) == 1 and not isinstance(rhs[0], Nonterminal):
				if len(rhs) == 1 and rhs[0] in self.lexicon:
					#lex[rhs[0]].append(" ".join(map(repr, (lhs, freq))))
					lex[rhs[0]].inc(lhs, count=freq)
				# this should NOT happen: (drop it like it's hot)
				elif len(rhs) == 0 or '' in (str(a).strip() for a in rhs):
					print 'empty', rule, freq 
					raise ValueError
					continue 
				else:
					# prob^Wfrequency	lhs	rhs1	rhs2
					#print "%s\t%s" % (repr(freq), rule)
					yield u"%s\t%s\n" % (repr(freq), rule)
					#yield "%s\t%s\t%s\n" % (repr(freq), str(lhs), 
					#			"\t".join(str(x) for x in rhs))
		def proc(lex):
			for word, tags in lex.items():
				# word	POS1 prob^Wfrequency1	POS2 freq2 ...
				#print "%s\t%s" % (word, "\t".join(' '.join(map(str, a)) for a in tags.items()))
				yield u"%s\t%s\n" % (word, "\t".join(' '.join(map(str, a)) for a in tags.items() if a[0].strip()))
		f.writelines(process())
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
