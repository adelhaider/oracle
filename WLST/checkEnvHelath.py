from java.util import HashMap
from java.util import HashSet
from java.util import ArrayList
from java.io import FileInputStream
from java.io import FileOutputStream

import sys
import os
from datetime import datetime

def checkEnvironmentHealth(environmentName):
    errors = 0
    warnings = 0
    logFile = open("/tmp/checkEnvHealth", "ab")
    envConfigProp = loadProps(os.environ["HOME"] + "/environments.properties")
    print 'Checking health of environment: ', environmentName
    logFile.write("Health status report for environment %s \n" % environmentName)
    try:
        for domainName in ["soa1", "soa2", "soa3"]:
            logFile.write("####################\nDomain %s \n####################\n" % environmentName)
            print "#####################################"
            print "###### Checking domain %s ########" % domainName
            print "#####################################"
            targetName = environmentName + "." + domainName
            admin_host = envConfigProp.get("env." + targetName + ".admin_host")
            admin_port = envConfigProp.get("env." + targetName + ".admin_port")
            adminUrl = "t3://" + admin_host + ":" + admin_port
            importUser = envConfigProp.get("env." + targetName + ".username")
            importPassword = envConfigProp.get("env." + targetName + ".password")
            print 'Target url: ', adminUrl
            print 'Connecting with username/pwd'
            connect(importUser, importPassword, adminUrl)

            serverNames = []
            serverNameMap = ls('/Servers', returnMap='true')
            for serverNameKey in serverNameMap:
                serverNames.append(serverNameKey)

            domainRuntime()

            for serverName in serverNames:
                serverRuntimeMBean = getMBean('/ServerRuntimes/' + serverName)
                if serverRuntimeMBean is None:
                    if "osb" in serverName:
                        errors += 1
                    else:
                        warnings += 1
                    print "Server %s not running (server runtime MBean not found) " % serverName
                    logFile.write("Server %s not running (server runtime MBean not found) \n" % serverName)
                else:
                    if "RUNNING" != serverRuntimeMBean.getState():
                        errors += 1
                        print "Server %s not running. Current state is %s \n" % (serverName, serverRuntimeMBean.getState())
                        logFile.write("Server %s not running. Current state is %s \n" % (serverName, serverRuntimeMBean.getState()))
                    else:
                        print "Server %s is healthy" % serverName
                        logFile.write("Server %s is healthy\n" % serverName)
            disconnect()
#        if errors > 0:
#            print "WARNING: Unhealthy/shutdown servers found"
#        if errors > 0:
#            raise "Unhealthy servers found"
    except:
        print "Unexpected error:", sys.exc_info()[0]
        dumpStack()
        logFile.close()
        raise


#=======================================================================================
# Utility function to print the list of operations
#=======================================================================================
def printOpMap(map):
    set = map.entrySet()
    for entry in set:
        op = entry.getValue()
        print op.getOperation(),
        ref = entry.getKey()
        print ref
    print

#=======================================================================================
# Utility function to print the diagnostics
#=======================================================================================
def printDiagMap(map):
    set = map.entrySet()
    for entry in set:
        diag = entry.getValue().toString()
        print diag
    print

#=======================================================================================
# Utility function to load properties from a config file
#=======================================================================================

def loadProps(configPropFile):
    propInputStream = FileInputStream(configPropFile)
    configProps = Properties()
    configProps.load(propInputStream)
    return configProps

try:
    # check server health
    # argv[1] is the target environment name

    checkEnvironmentHealth(sys.argv[1])

except:
    print "Unexpected error: ", sys.exc_info()[0]
    dumpStack()
    raise
