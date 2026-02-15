# Sutra Paper 1 — LaTeX Build
# Target: ArXiv (cs.MA + cs.AI), then AAMAS 2027

MAIN = main
TEXBIN = $(HOME)/Library/TinyTeX/bin/universal-darwin
TEX = $(TEXBIN)/pdflatex -interaction=nonstopmode
BIB = $(TEXBIN)/bibtex

.PHONY: all clean watch quick

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex references.bib
	$(TEX) $(MAIN)
	$(BIB) $(MAIN)
	$(TEX) $(MAIN)
	$(TEX) $(MAIN)

# Single pass (no bib update) — for quick iteration
quick:
	$(TEX) $(MAIN)

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log \
	      $(MAIN).out $(MAIN).pdf $(MAIN).toc $(MAIN).lof \
	      $(MAIN).lot $(MAIN).fls $(MAIN).fdb_latexmk \
	      $(MAIN).synctex.gz missfont.log

watch:
	fswatch -o $(MAIN).tex references.bib | xargs -n1 -I{} make all
