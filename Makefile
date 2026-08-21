# One definition of "passing". A human, a Claude Code hook, a pre-push gate and
# CI all call the same target -- if they each had their own idea of the checks,
# the invariants would be customary rather than real.
KSRC := $(HOME)/.claude/knowledge
PY   := python3

.PHONY: check check-store check-retrieval check-routing check-vendor test-gate vendor help

help:
	@echo "make check         everything below; this is the gate"
	@echo "make check-store   claims type-check (tagged union, one live claim per conflict-key)"
	@echo "make check-retrieval  every claim is findable by its own asked-as questions"
	@echo "make check-routing    pipeline configs name LIVE claim ids"
	@echo "make check-vendor  knowledge-bin/ has not drifted from $(KSRC)"
	@echo "make test-gate     the stagnation gate's own test suite"
	@echo "make vendor        refresh knowledge-bin/ from $(KSRC)"

check: check-vendor check-store check-retrieval check-routing test-gate
	@echo "== ALL CHECKS PASSED"

check-store:
	@$(PY) knowledge-bin/check-knowledge.py

check-retrieval:
	@$(PY) knowledge-bin/check-retrieval.py

check-routing:
	@n=0; for c in $$(git ls-files '*/pipeline*.json' 'jobs/*/route*.json' 2>/dev/null); do \
	  $(PY) knowledge-bin/check-routing.py --config $$c || exit 1; n=$$((n+1)); done; \
	  if [ $$n -eq 0 ]; then echo "routing: no pipeline configs to check"; \
	  else echo "routing: $$n config(s) name live claims"; fi

# Vendoring buys portability and costs a second copy. This is what stops the
# copy rotting: the moment knowledge-bin/ disagrees with the source of truth,
# the build fails. Where the source is absent (CI, a fresh clone) there is
# nothing to compare against, and the check says so rather than passing quietly.
check-vendor:
	@if [ -d "$(KSRC)/bin" ]; then \
	  for f in knowledge-bin/*.py; do \
	    b=$$(basename $$f); \
	    if [ -f "$(KSRC)/bin/$$b" ] && ! diff -q "$$f" "$(KSRC)/bin/$$b" >/dev/null; then \
	      echo "VENDOR DRIFT: knowledge-bin/$$b differs from $(KSRC)/bin/$$b"; \
	      echo "  the knowledge repo is the source of truth -- run 'make vendor', or"; \
	      echo "  fix it there first if the change belongs upstream"; exit 1; fi; done; \
	  for f in knowledge-bin/hooks/*; do \
	    b=$$(basename $$f); \
	    if [ -f "$(HOME)/.claude/hooks/$$b" ] && ! diff -q "$$f" "$(HOME)/.claude/hooks/$$b" >/dev/null; then \
	      echo "VENDOR DRIFT: knowledge-bin/hooks/$$b differs from ~/.claude/hooks/$$b"; \
	      exit 1; fi; done; \
	  echo "vendor: knowledge-bin matches $(KSRC)"; \
	else echo "vendor: $(KSRC) not present -- drift NOT checked on this machine"; fi

test-gate:
	@if [ -f knowledge-bin/test-stagnation-gate.py ]; then \
	  $(PY) knowledge-bin/test-stagnation-gate.py; \
	else echo "test-gate: no suite vendored"; fi

vendor:
	@cp $(KSRC)/bin/*.py knowledge-bin/
	@cp $(HOME)/.claude/hooks/knowledge-check.sh $(HOME)/.claude/hooks/knowledge-session-start.sh \
	    $(HOME)/.claude/hooks/state-report-stop.sh $(HOME)/.claude/hooks/stagnation-gate.sh \
	    $(HOME)/.claude/hooks/show-me-pixels-stop.sh $(HOME)/.claude/hooks/stagnation_gate.py \
	    $(HOME)/.claude/hooks/show_me_pixels.py knowledge-bin/hooks/
	@rm -rf knowledge-bin/__pycache__ knowledge-bin/hooks/__pycache__
	@sed -i '' "s|^commit   .*|commit   $$(cd $(KSRC) && git rev-parse HEAD)|" knowledge-bin/VENDORED-FROM
	@sed -i '' "s|^vendored .*|vendored $$(date +%Y-%m-%d)|" knowledge-bin/VENDORED-FROM
	@echo "vendored from $(KSRC) at $$(cd $(KSRC) && git rev-parse --short HEAD)"
