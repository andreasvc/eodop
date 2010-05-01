# -*- coding: UTF-8 -*-
# Dua Libro, sen antauparolo
import nltk
corpus="""(S (S (NP (DT la) (N' (JJ venontajn) (N' (JJ apartajn) (NN pecojn)))) (VP (NP (PRP mi)) (VP (VBP donas)))) (S' (IN ke) (S (NP (DT la) (NN lernantoj)) (VP (VB povu) (VP (VP (VP (VB ripeti) (RB praktike)) (NP (NP (DT la) (NN regulojn)) (PP (IN de) (NP (DT l') (N' (NN gramatiko) (JJ internacia)))))) (VPC (CC kaj) (VP (VP (VB kompreni) (RB bone)) (NP (NP (NP (DT la) (NN signifon)) (NPC (CC kaj) (NP (DT la) (NN uzon)))) (PP (IN de) (NP (DT l') (N' (NN sufiksoj) (NC (CC kaj) (NN prefiksoj)))))))))))))
(S (NP (NN amiko)) (VP (VB venis)))
(S (NP (DT unu) (PP (IN el) (NP (DT la) (NN amikoj)))) (VP (VB venis)) )
(S (NP (DT la) (NN amiko)) (VP (VB venis)))
(S (NP (NP (DT la) (N' (JJ konata) (NN amiko))) (NPC (CC au) (NP (NP (DT la) (NNS amiko)) (S (NP (DT kiun)) (VP (NP (PRP oni)) (VP (VBD atendis))))))))
(S (VP (VP (VB donu) (PP (IN al) (NP (PRP mi)))) (NP (NN libron))))
(S (VP (VP (VB donu) (PP (IN al) (NP (PRP mi)))) (NP (NP (DT la) (NN libron)) (S (NP (DT kiun)) (VP (NP (PRP vi)) (VP (VB promesis) (PP (IN al) (NP (PRP mi)))))))))
(S (NP (DT (DT tiu) (RB chi)) (NN ghardeno)) (VP (VB estas) (NP (NP (JJ amata) (NN loko)) (PP (IN de) (NN birdoj)))) )
(S (NP (DT la) (NN fenestro)) (VP (VB estas) (NP (NP (JJ amata) (NN loko)) (PP (IN de) (NP (DT la) (NN birdoj))))))
(S (NP (PRP niaj) (NN birdoj)))
(S (NP (DT la) (N' (NN vorto) (NN "la"))) (VP (VB estas) (VP (VB nomata) (NP (NN artikulo)))))
(S (NP (PRP ghi)) (VP (VB estas) (VP (VB uzata) (NP (DT tian) (S (NP (DT kian)) (VP (NP (PRP ni)) (VP (VB parolas) (PP (IN pri) (N' (NN objektoj) (JJ konataj))))))))) )
(S (PP (IN anstatau) (NP (NN "la"))) (S (NP (PRP oni)) (VP (VP (VB povas) (RB ankau)) (VP (VP (VB diri) (NP (NN "l'"))) (PP (IN se) (S (NP (PRP ghi)) (VP (RB ne) (VP (VB estos) (RB malbonsone)))))))) )
(S (S (PP (IN se) (S (NP (DT iu)) (VP (VP (VP (RB ne) (VB komprenas)) (RB bone)) (NP (NP (DT la) (NN uzon)) (PP (IN de) (NP (DT la) (NN artikulo))))))) (S (NP (PRP li)) (VP (VP (VB povas) (RB tute)) (VP (NP (PRP ghin)) (VP (RB ne) (VB uzi)))))) (SC (CC char) (S (NP (PRP ghi)) (VP (VB estas) (NP (NP (JJ oportuna)) (NPC (CC sed) (NP (RB ne) (JJ necesa))))))))""".split('\n')
