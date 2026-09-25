.PHONY: help deps lint sanity test test-all matrix

TESTED   := $(notdir $(patsubst %/molecule,%,$(wildcard roles/*/molecule)))
DISTROS  := ubuntu2404 ubuntu2204 debian12

ROLE     ?=
SCENARIO ?= --all
DISTRO   ?= ubuntu2404

NAMESPACE := $(shell awk '/^namespace:/ {print $$2}' galaxy.yml)
NAME      := $(shell awk '/^name:/ {print $$2}' galaxy.yml)

help:
	@echo "make lint                                yamllint and ansible-lint, production profile"
	@echo "make sanity                              ansible-test sanity in Docker"
	@echo "make test ROLE=consul                    every scenario of one role on $(DISTRO)"
	@echo "make test ROLE=vault SCENARIO='-s guard' one scenario"
	@echo "make test ROLE=nomad DISTRO=debian12     another distribution"
	@echo "make test-all                            every role with molecule, on $(DISTRO)"
	@echo "make matrix ROLE=consul                  one role on $(DISTROS)"
	@echo "roles with scenarios: $(TESTED)"

deps:
	ansible-galaxy collection install community.crypto community.general .

lint:
	yamllint .
	ansible-lint --profile production

sanity:
	@dir=$$(mktemp -d)/ansible_collections/$(NAMESPACE)/$(NAME); \
	mkdir -p "$$dir" \
	&& rsync -a --exclude .git --exclude __pycache__ ./ "$$dir/" \
	&& cd "$$dir" && ansible-test sanity --docker default --python 3.12

test:
	@test -n "$(ROLE)" || { echo "ROLE is required, one of: $(TESTED)" >&2; exit 1; }
	cd roles/$(ROLE) && MOLECULE_DISTRO=$(DISTRO) molecule test $(SCENARIO)

test-all:
	@for role in $(TESTED); do \
		echo "== $$role on $(DISTRO)"; \
		(cd roles/$$role && MOLECULE_DISTRO=$(DISTRO) molecule test --all) || exit 1; \
	done

matrix:
	@test -n "$(ROLE)" || { echo "ROLE is required, one of: $(TESTED)" >&2; exit 1; }
	@for distro in $(DISTROS); do \
		echo "== $(ROLE) on $$distro"; \
		(cd roles/$(ROLE) && MOLECULE_DISTRO=$$distro molecule test --all) || exit 1; \
	done
