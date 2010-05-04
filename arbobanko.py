#!/usr/bin/python
"""treebank conversion script; expects no arguments, uses stdin & stdout.
input is VISL horizontal tree format
see: http://beta.visl.sdu.dk/treebanks.html#The_source_format
output: s-expression, ie., tree in bracket notation.
TODO: turn this into a nltk.Corpus reader
"""

example = """X:np
=H:n("konsekvenco" <*> <ac> P NOM)	Konsekvencoj
=DN:pp
==H:prp("de")	de
==DP:np
===DN:adj("ekonomia" <Deco> P NOM)	ekonomiaj
===H:n("transformo" P NOM)	transformoj"""

example2 = """STA:fcl
=S:np
==DN:pron-dem("tia" <*> <Dem> <Du> <dem> DET P NOM)     Tiaj
==H:n("akuzo" <act> <sd> P NOM) akuzoj
=fA:adv("certe")        certe
=P:v-fin("dauxri" <va+TEMP> <mv> FUT VFIN)      dauxros
."""


from nltk import Tree
from nltk.tokenize import word_tokenize, wordpunct_tokenize
from sys import stdin, stdout, stderr
import re
from itertools import chain

def cnf(tree):
	""" make sure all terminals have POS tags; 
	invent one if necessary ("parent_word") """
	result = tree.copy(True)
	for a in tree.treepositions('leaves'):
		if len(tree[a[:-1]]) != 1:
			result[a] = Tree("%s_%s" % (tree[a[:-1]].node, tree[a]), [tree[a]])
	for a in tree.treepositions():
		if isinstance(tree[a], Tree) and len(tree[a]) == 0:
			tree[a] += tree[a].node
			# = Tree("%s_%s" % (tree[a[:-1]].node, tree[a]), [tree[a]])
	return result

def leaves(xx):
	"""include "non-terminals" if they have no children"""
	def node(a):
		if isinstance(a, Tree): return a.node
		else: return a
	def splitword(a):
		return node(a).split("_")
	return list(reduce(chain, [splitword(xx[a]) for a in xx.treepositions() if (not isinstance(xx[a], Tree)) or len(xx[a]) == 0]))

def parse(input, stripmorph=True):
	"""parse a horizontal tree into an s-expression (ie., WSJ format). 
	Defaults to stripping morphology information. 
	Parentheses in the input are converted to braces.
	
	>>> print example
	X:np
	=H:n("konsekvenco" <*> <ac> P NOM)	Konsekvencoj
	=DN:pp
	==H:prp("de")	de
	==DP:np
	===DN:adj("ekonomia" <Deco> P NOM)	ekonomiaj
	===H:n("transformo" P NOM)	transformoj	
	>>> parse(example.split('\\n'))
	'(X:np (H:n Konsekvencoj) (DN:pp (H:prp de) (DP:np (DN:adj ekonomiaj) (H:n transformoj))))'	
	>>> print example2
	STA:fcl
	=S:np
	==DN:pron-dem("tia" <*> <Dem> <Du> <dem> DET P NOM)     Tiaj
	==H:n("akuzo" <act> <sd> P NOM) akuzoj
	=fA:adv("certe")        certe
	=P:v-fin("dauxri" <va+TEMP> <mv> FUT VFIN)      dauxros
	.

	>>> parse(example2.split('\\n'))
	'(STA:fcl (S:np (DN:pron-dem Tiaj) (H:n akuzoj)) (fA:adv certe) (P:v-fin dauxros) .)'
	"""
	n = -1
	open = 0
	out = []
	for a in input:
		if a.count('=') == n and n != 0:
			out += ') ('
		else:
			if a.count('=') > n:
				out += ' (' * (a.count('=') - n)
				open += (a.count('=') - n)
			elif a.count('=') < n:
				out += "%s %s" % (')' * n, a.count('=') * '(')
				open -= (n - a.count('='))
		n = a.count('=')
		# remove morphology tags & lemma; replace other parentheses with braces because nltk.Tree gets confused
		if stripmorph:
			word = re.sub("=+|\(.*\)", "", a).replace('(','{').replace(')','}').split()
		else:
			word = a.replace('(','{').replace(')','}').split()
		#every terminal should have a POS tag, be creative if it does not
		if len(word) == 1: word == (word, word)
		out += " " + " ".join(word)
		
	out += open * ')'
	return "".join(out).replace('( ', '(')[1:]

def main():
	"""take a treebank from stdin in horizontal tree format, and output it
	in s-expression format (ie., bracket notation, WSJ format). Checks
	whether original sentence and leaves of the tree match, and discards
	the tree if they don't. Also removes trees marked problematic with the
	tag "CAVE" in the comments.  Example input:
	<s_id=812>
	SOURCE: id=812
	ID=812 Necesus adapti la metodon por iuj alilandaj klavaroj.
	A1
	STA:fcl
	=P:v-fin("necesi" <*> <mv> COND VFIN)   Necesus
	=S:icl
	==P:v-inf("adapti" <mv>)        adapti
	==Od:np
	===DN:art("la") la
	===H:n("metodo" <ac> S ACC)     metodon
	===DN:pp
	====H:prp("por" <aquant>)       por
	====DP:np
	=====DN:pron("iu" <quant> DET P NOM)    iuj
	=====DN:adj("alilanda" P NOM)   alilandaj
	=====H:n("klavaro" <cc-h> <tool-mus> P NOM)     klavaroj
	.

	</s>
	"""
	correct = n = cave = mismatch = failed = 0
	s = False
	for a in stdin:
		if s and a[:4] == "</s>":
			s = 0
			x = parse(tree)
			try:
				xx = Tree(x)
				if sent == leaves(xx):
					#cnf(xx)
					stdout.write("%s\n" % str(cnf(xx)).replace('\n',''))
					correct += 1
				else:
					# this happens when the leaves do not agree with the original sentence
					stderr.write("""sentence-leaves mismatch!
expected: %s
got:      %s
tree:
%s
""" % (repr(sent), repr(leaves(xx)), str(x)))
					mismatch += 1
			except ValueError:
				# this only happens when our output failes to parse (malformed s-expression):
				stderr.write("""failed to parse:
input:  %s
output: %s
""" % ("".join(tree), str(x)))
				failed += 1
		elif s and a[:2] == "ID":
			#ID=123 the sentence. => ['the', 'sentence', '.']
			# we need this monstrosity because word_tokenize does
			# not tokenize "word.)" into three tokens like it
			# should
			#sent = wordpunct_tokenize(" ".join(word_tokenize(a[a.index(' ')+1:].replace('(','{').replace(')','}'))))
			def mytokenize(a):
				pass
			sent = word_tokenize(a[a.index(' ')+1:].replace('(','{').replace(')','}'))
		elif s and "CAVE" in a:
			#skip trees with errors
			cave += 1
			s = 0
		elif s:
			s += 1
		
		if a[0] == "#": 
			continue

		if s >= 4:
			tree.append(a)

		if not s and a[:2] == "<s":
			s = 1
			n += 1
			tree = []
	stderr.write("converted %d of %d trees in input\n" % (correct, n))
	stderr.write("cave circularities: %d, sentence-leaves mismatches: %d\nmalformed s-expression output: %d\n" % (cave, mismatch, failed))


if __name__ == '__main__':
	import doctest
	# do doctests, but don't be pedantic about whitespace (I suspect it is the
	# militant anti-tab faction who are behind this obnoxious default)
	fail, attempted = doctest.testmod(verbose=False,
		optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS)
	if attempted and not fail:
		stderr.write("%d doctests succeeded!\n" % attempted)
	main()
