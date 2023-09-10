#
DOCKER         := docker
DOCKER_COMPOSE := docker-compose

# Default docker-compose file
#
COMPOSE_FILE_DEFAULT_NAME := docker-compose.yml

# Default container for docker actions
# NOTE: EDIT THIS TO AVOID WARNING/ERROR MESSAGES
#
CONTAINER_DEFAULT :=

# Shell command for 'shell' target
#
SHELL_CMD := /bin/bash

ME := $(realpath $(firstword $(MAKEFILE_LIST)))

# Expected to be parent folder of compose file
# Contains trailing '/'
#
PWD := $(dir $(ME))

container ?= $(CONTAINER_DEFAULT)
file      ?= $(PWD)$(COMPOSE_FILE_DEFAULT_NAME)
service   ?=
services  ?= $(service)

.DEFAULT_GOAL := help

##
# help
# Displays a (hopefully) useful help screen to the user
help: about targets args ## This help screen
ifeq ($(CONTAINER_DEFAULT),)
	$(warning WARNING: CONTAINER_DEFAULT is not set. Please edit makefile)
endif

about:
	@echo
	@echo "Makefile to help manage docker-compose services"

args:
	@echo
	@echo "Target arguments:"
	@echo
	@echo "    " "file"      "\t" "Location of docker-compose file (default = './$(COMPOSE_FILE_DEFAULT_NAME)')"
	@echo "    " "service"   "\t" "Target service for docker-compose actions (defauilt = all services)"
	@echo "    " "services"  "\t" "Target services for docker-compose actions (defauilt = all services)"
	@echo "    " "container" "\t" "Target container for docker actions (default = '$(CONTAINER_DEFAULT)')"

##
# list
# Displays a list of targets, using '##' comment as target description
#
# NOTE: ONLY targets with ## comments are shown
#
list: targets ## see 'targets'
targets:  ## Lists targets
	@echo
	@echo "Make targets:"
	@echo
	@cat $(ME) | \
	sed -n -E 's/^([^.][^: ]+)\s*:(([^=#]*##\s*(.*[^[:space:]])\s*)|[^=].*)$$/    \1	\4/p' | \
	sort -u | \
	expand -t15
	@echo

##
# services
#
services: ## Lists services
	@$(DOCKER_COMPOSE) -f "$(file)" ps --services

##
# build
#
build: ## Builds service images [file|service|services]
	@$(DOCKER_COMPOSE) -f "$(file)" build $(services)

##
# up
#
up: ## Starts containers (in detached mode) [file|service|services]
	@$(DOCKER_COMPOSE) -f "$(file)" up --detach $(services)

##
# down
#
down: ## Removes containers (preserves images and volumes) [file]
	@$(DOCKER_COMPOSE) -f "$(file)" down

##
# rebuild
#
rebuild: down build ## Stops containers (via 'down'), and rebuilds service images (via 'build')

##
# clean
#
clean: ## Removes containers, images, volumes [file], build cache
	@$(DOCKER_COMPOSE) -f "$(file)" down --volumes --rmi all && \
	docker builder prune -f

##
# start
#
start: ## Starts previously-built containers (see 'build') [file|service|services]
	@$(DOCKER_COMPOSE) -f "$(file)" start $(services)

##
# ps
#
status: ps ## see 'ps'
ps:        ## Shows status of containers [file|service|services]
	@$(DOCKER_COMPOSE) -f "$(file)" ps $(services)

##
# logs
#
logs:  ## Shows output of running containers (in 'follow' mode) [file|service|services]
	@$(DOCKER_COMPOSE) -f "$(file)" logs --follow $(services)

##
# stop
#
stop: ## Stops containers (without removing them) [file|service|services]
	@$(DOCKER_COMPOSE) -f "$(file)" stop $(services)

##
# restart
#
restart: stop start ## Stops containers (via 'stop'), and starts them again (via 'start')

##
# shell
#
sh:    shell ## see 'shell'
bash:  shell ## see 'shell' (may not actually be bash)
shell:       ## Brings up a shell in default (or specified) container [container]
ifeq ($(container),)
	$(error ERROR: 'container' is not set. Please provide 'container=' argument or edit makefile and set CONTAINER_DEFAULT)
endif
	@echo
	@echo "Starting shell ($(SHELL_CMD)) in container '$(container)'"
	@$(DOCKER) exec -it "$(container)" "$(SHELL_CMD)"