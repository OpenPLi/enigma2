#!/bin/sh

setup_git() {
  git config --global user.email "bot@openpli.org"
  git config --global user.name "OpenPLi python bot"
}

commit_files() {
  git clean -fd
  rm -rf *.pyc
  rm -rf *.pyo
  rm -rf *.mo
  git checkout develop
  ./PEP8.sh
}

upload_files() {
  git remote add upstream https://${GH_TOKEN}@github.com/OpenPLi/enigma2.git > /dev/null 2>&1
  git push --quiet upstream develop || echo "failed to push with error $?"
}

setup_git
commit_files
upload_files
