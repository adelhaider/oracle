#!/bin/sh
#local
: "${FMW_HOME?Need to set FMW_HOME}"

source $FMW_HOME/wlserver/server/bin/setWLSEnv.sh
source $FMW_HOME/osb/tools/configjar/setenv.sh


#!/bin/sh
#remote
#ORIGINAL_PARAMS=$*
#CURR_FOLDER=$PWD
#echo sourcing setDomainEnv.sh
#. $DOMAIN_HOME/bin/setDomainEnv.sh
#cd $CURR_FOLDER
#$MW_HOME/osb/tools/configjar/wlst.sh $ORIGINAL_PARAMS
