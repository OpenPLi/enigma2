#!/bin/bash
# Script to generate po files outside of the normal build process
# Author: Pr2 for OpenPLi Team
# Version: 1.3
# 
# This script is derivated from updateallpo.sh it is intended to all you
# create the updated version of the po files on different environment:
# For Windows, please download and install the following program:
# Python:
# https://www.python.org/
# GitForWindows:
# https://gitforwindows.org/ 
#
# Pre-requisite for Windows:
# -> install python on your PC
# -> install Git for Windows, you can keep all default installation settings.
# -> Start the installed:  git-bash  you will see a command prompt.
# -> At the git-bash command prompt we will clone OpenPLi repository (see below):
#
# For Mac OSX download and install homebrew following explanation from:
# https://brew.sh/
#
# For Mac OSX with homebrew and also Linux users:
# The following tools must be installed on your system and accessible from path:
# gawk, find, gettext, gnu-sed, python
# Start and terminal and clone OpenPLi repository (see below):
#
# On All platforms please download and install:
#
# PoEdit:  https://poedit.net/
#
# You then need to clone the OpenPLi repository with the following command:
# -------------------------------------------------------------------------------------
# git clone https://github.com/OpenPLi/enigma2.git
# cd enigma2/po
# -------------------------------------------------------------------------------------
# Run this script from within the po folder.
#
remote="origin"
branch="develop"
python="python"
localgsed="gsed"
xml2po="xml2po.py"
findoptions=""
delete=1

function this_help () {
	printf "Possible options are:\n"
	printf " -r | --remote to specify the remote git to use,   default[origin]\n" 
	printf " -b | --branch to specify the branch to translate, default[develop]\n"
	printf " -p | --python to specify the python runtime name, default[python]\n"
	printf " -n | --nodelete to keep the .pot files, useful to find where a message came from\n"
	printf " -h | --help   this text\n\n"
	printf "To translate for the develop branch simply run this script without any option.\n"
	printf "To translate for the rc branch simply specify:\n"
	printf "%s -branch rc \nor\n%s -b rc\n" $0 $0
	printf "\n\n"
	printf "Pre-requisites:\n\n"
	printf "Please read the OpenPLi translators wiki page:\n"
	printf "https://wiki.openpli.org/Information_for_Translators\n"
	return 0
}

while [ "$1" != "" ]; do
    case "$1" in
    -b|--branch)
    	shift
    	branch="$1"
    	;;
    -r|--remote)
    	shift
    	remote="$1"
    	;;
    -p|--python)
    	shift
    	python="$1"
    	;;
    -n|--nodelte)
    	delete=0
    	;;
    -h|--help)
    	this_help
    	exit 0
    	;;
    *)
    	printf "Error: unknown parameter [%s]\n\n" "$1"
		this_help
    	exit 1
	esac
	shift
done
#
# Checking if defined remote exist
#

(git remote -v | grep -q "$remote\s") \
	&& { printf "Remote git    : [%s]\n" $remote; } \
	|| { printf "Sorry this remote doesn't exist: [%s]\n Valid remotes are:\n" $remote; \
	      git remote -v ; exit 1; }
#
# Checking if remote branch exist on the defined remote
#

(git branch -r | grep -q "$remote/""$branch""$") \
	 && { printf "Remote branch : [%s]\n" $branch; } \
	 || { printf "Sorry this branch doesn't exist: [%s]\n Valid branches are:\n" $branch; \
	      git branch -r | grep $remote | sed 's/"$remote"\///'; exit 1; }
#
# Checking for Python version number to select the right python script to use
#
command -v "$python" >/dev/null 2>&1 || { printf >&2 "Script requires python but it's not installed.  Aborting."; \
		 printf "Please download latest version and install it from: https://www.python.org/\n"; exit 1; }
ver=$("$python" -V 2>&1 | sed 's/.* \([0-9]\).\([0-9]\).*/\1\2/')
if [ "$ver" -ge "30" ]; then
   xml2po="xml2po-python3.py"
fi
printf "Python used [%s] script used [%s]: " "$python" "$xml2po"
"$python" --version
#
# Checking for gettext component
#
command -v xgettext --version  >/dev/null 2>&1  || { printf "Please install gettext package on your system. Aborting.\n"; exit 1; }
command -v msguniq --version  >/dev/null 2>&1 || { printf "Please install gettext package on your system. Aborting.\n"; exit 1; }
#
# On Mac OSX find option are specific
#
if [[ "$OSTYPE" == "darwin"* ]]
	then
		# Mac OSX
		printf "Script running on Mac OSX [%s]\n" "$OSTYPE"
    	findoptions=" -s -X "
fi
#
# Script only run with gsed but on some distro normal sed is already gsed so checking it.
#
sed --version 2> /dev/null | grep -q "GNU"
if [ $? -eq 0 ]; then
	localgsed="sed"
else
	"$localgsed" --version | grep -q "GNU"
	if [ $? -eq 0 ]; then
		printf "GNU sed found: [%s]\n" $localgsed
	fi
fi
#
# Needed when run in git-bash for Windows
#
export PYTHONIOENCODING=utf-8
#
# To fix the LF (Linux, Mac) and CRLF (Windows) conflict
#
git config core.eol lf
git config core.autocrlf input
git config core.safecrlf true
#
# Git commands to sync with origin and create the branch MyTranslation to work on.
#
git reset HEAD --hard
git checkout -B $branch $remote/$branch
git pull
git branch -D MyTranslation
git checkout -B MyTranslation
#
# Retrieve languages from Makefile.am LANGS variable for backward compatibility
#
printf "Po files update/creation from script starting.\n"
languages=($(gawk ' BEGIN { FS=" " } 
		/^LANGS/ {
			for (i=3; i<=NF; i++)
				printf "%s ", $i
		} ' Makefile.am ))

# If you want to define the language locally in this script uncomment and defined languages
#languages=("ar" "bg" "ca" "cs" "da" "de" "el" "en" "es" "et" "fa" "fi" "fr" "fy" "he" "hk" "hr" "hu" "id" "is" "it" "ku" "lt" "lv" "nl" "nb" "nn" "pl" "pt" "pt_BR" "ro" "ru" "sk" "sl" "sr" "sv" "th" "tr" "uk" "zh")

#
# Arguments to generate the pot and po files are not retrieved from the Makefile.
# So if parameters are changed in Makefile please report the same changes in this script.
#

printf "Creating temporary file enigma2-py.pot\n"
find $findoptions .. -name "*.py" -exec xgettext --no-wrap -L Python --from-code=UTF-8 -kpgettext:1c,2 --add-comments="TRANSLATORS:" -d enigma2 -s -o enigma2-py.pot {} \+
"$localgsed" --in-place enigma2-py.pot --expression=s/CHARSET/UTF-8/
printf "Creating temporary file enigma2-xml.pot\n"
find $findoptions .. -name "*.xml" -exec "$python" "$xml2po" {} \+ > enigma2-xml.pot
printf "Merging pot files to create: enigma2.pot\n"
cat enigma2-py.pot enigma2-xml.pot | msguniq --no-wrap --no-location -o enigma2.pot -
OLDIFS=$IFS
IFS=" "
for lang in "${languages[@]}" ; do
	if [ -f $lang.po ]; then \
		printf "Updating existing translation file %s.po\n" $lang
		msgmerge --backup=none --no-wrap --no-location -s -U $lang.po enigma2.pot && touch $lang.po; \
		msgattrib --no-wrap --no-obsolete $lang.po -o $lang.po; \
		msgfmt -o $lang.mo $lang.po; \
	else \
		printf "New file created: %s.po, please add it to github before commit\n" $lang
		msginit -l $lang.po -o $lang.po -i enigma2.pot --no-translator; \
		msgfmt -o $lang.mo $lang.po; \
	fi
done
if [ $delete -eq 1 ]; then \
	rm enigma2-py.pot enigma2-xml.pot enigma2.pot; \
fi
IFS=$OLDIFS
printf "Po files update/creation from script finished!\n"
printf "Edit with PoEdit the po file that you want to translate located in:\n\n"
command -v cygpath > /dev/null && { cygpath -w "$PWD"; } || { pwd; }
printf "\nthen post it back to OpenPLi forum:\n\n"
printf "https://forums.openpli.org/forum/55-en-enduser-support/\n\n"
printf "Please always specify that it is for branch [%s]\n\n" $branch
printf "PoEdit: https://poedit.net/\n"
printf "IMPORTANT: in PoEdit go into Files-Preferences menu select the advanced tab\n"
printf "           1) select Unix(recommended) for carriage return\n"
printf "           2) unselect wrap text\n"
printf "           3) unselect keep original file format\n"
printf "You only need to do this once in PoEdit.\n\n"
printf "Please read the translators wiki page:\n"
printf "\nhttps://wiki.openpli.org/Information_for_Translators\n"
