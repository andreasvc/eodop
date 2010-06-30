#!/bin/sh
sh procresult.sh <arbobanko.results >arbobanko.resproc
#evalb -e 1000 -p COLLINS.prm arbobanko.gold arbobanko.resproc
evalb -e 1000 arbobanko.gold arbobanko.resproc
