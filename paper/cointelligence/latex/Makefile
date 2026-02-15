# Cointelligence Paper — LaTeX Build
# IJCAI-ECAI 2026 format, BibTeX references

MAIN = main
TEXBIN = $(HOME)/Library/TinyTeX/bin/universal-darwin
TEX = $(TEXBIN)/pdflatex -interaction=nonstopmode
BIB = $(TEXBIN)/bibtex

.PHONY: all clean watch

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex references.bib ijcai26.sty named.bst
	$(TEX) $(MAIN)
	$(BIB) $(MAIN)
	$(TEX) $(MAIN)
	$(TEX) $(MAIN)

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log \
	      $(MAIN).out $(MAIN).pdf $(MAIN).toc $(MAIN).lof \
	      $(MAIN).lot $(MAIN).fls $(MAIN).fdb_latexmk \
	      $(MAIN).synctex.gz

watch:
	fswatch -o $(MAIN).tex references.bib | xargs -n1 -I{} make all
