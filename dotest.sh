#!/bin/sh
# -p grammar has frequencies
# -b 1 use best pares, ie. most probable derivation
# -s top is the root node for complete parse trees
# -u unknownwordsm contains pos tags for unknown words (m for monato corpus)
# -w pos.dfsa is the deterministic finite state automaton to assign word classes
# syntax.pcfg the grammar, only non-terminals and frequencies
# syntax.lex the lexicon, ie., terminals with POS tags and frequencies
# arbobanko.test containing only the words of the sentences in the test corpus, one word on each line, sentences seperated by empty lines
# arbobanko.results write results here 
time bitpar -p -b 1 -s top -u unknownwordsm -w pos.dfsa /tmp/gsyntax.pcfg /tmp/gsyntax.lex arbobanko.test arbobanko.results
