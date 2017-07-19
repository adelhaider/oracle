import os
import sys
import jarray
import wlstModule

from com.bea.wli.config import Ref
from com.bea.wli.config.resource import ResourceQuery
#from com.bea.wli.config.component import AlreadyExistsException
from com.bea.wli.monitoring import StatisticType
from com.bea.wli.sb.management.configuration import ALSBConfigurationMBean
from com.bea.wli.sb.management.configuration import BusinessServiceConfigurationMBean
from com.bea.wli.sb.management.configuration import CommonServiceConfigurationMBean
from com.bea.wli.sb.management.configuration import ProxyServiceConfigurationMBean
from com.bea.wli.sb.management.configuration import SessionManagementMBean
from com.bea.wli.sb.management.query import BusinessServiceQuery
from com.bea.wli.sb.management.query import ProxyServiceQuery
from com.bea.wli.sb.util import Refs

from java.util import Collections
from propertyUtils import *
from sys import path

#=========================================================================
# Global Constants
#=========================================================================
_PROXY = 'PROXY'
_BUSINESS = 'BUSINESS'
_ENABLE = 'enable'
_DISABLE = 'disable'

# Simulate enumerations


def enum(**enums):
    return type('Enum', (), enums)


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

_LOG_LEVEL = enum(DEBUG=1, INFO=2, WARNING=3, ERROR=4)
currentLogLevel = _LOG_LEVEL.INFO


#=========================================================================
# Entry functions (i.e. main)
#=========================================================================
# def main():
#    projectNames=["DurableSubscriberForScanReceivedTest"]
#    initEnv('dev.soa3')
#    try:
#        openWLSConnection()
# undeployProjectsFromOSBDomain(projectNames)
#    except:
#        closeWLSConnection()
# Call the main function
# main()


#=========================================================================
# Utility functions
#=========================================================================
#
def loadCustomProperties(propertiesFile="/home/adel/bin/misc.properties"):
    '''Load custom properties'''
    global properties
    properties = loadProperties(propertiesFile)
    msg(properties, _LOG_LEVEL.DEBUG)

def initEnv(env="EMPTY"):
    '''Initialize the environment'''
    if ('properties' not in globals()):
        msg("Properties not loaded. Loading now...", _LOG_LEVEL.INFO)
        loadCustomProperties()
        msg("done!", _LOG_LEVEL.DEBUG)

    environments = properties.getProperty("environments")

    global host
    global username
    global password
    global adminUrl
    global nmUsername
    global nmPassword
    global nmPort
    global domainName
    global domainHome
    global adminServerName
    global adminServerName
    global osbClusterName
    global osbServers
    global jmsServers

    if (env not in environments):
        msg("Please choose a valid environment: " + environments, _LOG_LEVEL.WARNING)
    else:
        try:
            msg("Getting properties for env " + env, _LOG_LEVEL.INFO)
            host = properties.getProperty(env + ".host")
            username = properties.getProperty(env + ".wl.username")
            password = properties.getProperty(env + ".wl.password")

            adminServerName = properties.getProperty(env + ".admin.server.name")
            adminUrl = host + ":" + properties.getProperty(env + ".admin.server.port")

            nmUsername = properties.getProperty(env + ".nm.username")
            nmPassword = properties.getProperty(env + ".nm.password")
            nmPort = properties.getProperty(env + ".nm.port")

            domainName = properties.getProperty(env + ".domain.name")
            domainHome = properties.getProperty(env + ".domain.home")

            osbClusterName = properties.getProperty(env + ".osb.cluster.name")
            osbServers = properties.getProperty(env + ".osb.servers")

            jmsServers = properties.getProperty(env + ".jms.servers")

            echoEnv()
        except:
            msg("Properties may not been defined in file for environment: " + env, _LOG_LEVEL.WARNING)

def echoEnv():
    '''Display environment details'''
    try:
        msg("Host              : " + host, _LOG_LEVEL.INFO)
        msg("Username          : " + username, _LOG_LEVEL.INFO)
        msg("AdminUrl is       : " + adminUrl, _LOG_LEVEL.INFO)
        msg("NM username       : " + nmUsername, _LOG_LEVEL.INFO)
        msg("NM port           : " + nmPort, _LOG_LEVEL.INFO)
        msg("Domain Name is    : " + domainName, _LOG_LEVEL.INFO)
        msg("Domain Home is    : " + domainHome, _LOG_LEVEL.INFO)
        msg("Admin Server Name : " + adminServerName, _LOG_LEVEL.INFO)
        msg("OSB Cluster Name  : " + osbClusterName, _LOG_LEVEL.INFO)
        msg("OSB Servers       : " + osbServers, _LOG_LEVEL.INFO)
        msg("JMS Servers       : " + jmsServers, _LOG_LEVEL.INFO)
    except NameError:
        msg("Environment not set. Run initEnv().", _LOG_LEVEL.WARNING)

#=========================================================================
# Domain Functions
#=========================================================================
def listServers():
    '''List servers'''
    servers = ls('Servers', returnMap='true')
    for s in servers:
        state(s, 'Server')

def shutdownServers():
    '''Shutdown all servers'''
    stopOSB(1)
    stopAdmin()
    stopNodeManager()

def openWLSConnection():
    '''Open connection to WebLogic server and plug into domainRuntime tree'''
    connect(username, password, adminUrl)

def closeWLSConnection():
    '''Close connection to domain runtime and node manager'''
    disconnect()

def startAdmin():
    '''Start admin server'''
    startManagedServer(adminServerName)

def stopAdmin():
    '''Stop admin server'''
    killManagedServer(adminServerName)

def startOSB(n):
    '''Start OSB server'''
    startManagedServer(osbServerPrefix + str(n))

def stopOSB(n):
    '''Stop OSB server'''
    killManagedServer(osbServerPrefix + str(n))

def statusAdmin():
    '''Display status of admin server'''
    nmServerStatus(adminServerName)

def statusOSB(n):
    '''Display status of osb server'''
    nmServerStatus(osbServerPrefix + str(n))

def startManagedServer(serverName):
    '''Start managed server <serverName>'''
    try:
        nmConnect(username, password, host, nmPort,
                  domainName, domainHome, 'SSL')
        serverStatus = nmServerStatus(serverName)

        if serverStatus != 'RUNNING':
            msg("Server is currently " + serverStatus, _LOG_LEVEL.INFO)
            nmStart(serverName)
        else:
            msg("Server is already " + serverStatus, _LOG_LEVEL.INFO)
    except:
        raise

def killManagedServer(serverName):
    '''Stop managed server <serverName>'''
    try:
        nmConnect(username, password, host, nmPort,
                  domainName, domainHome, 'SSL')
        serverStatus = nmServerStatus(serverName)

        if serverStatus == 'RUNNING':
            msg("Server is currently " + serverStatus, _LOG_LEVEL.INFO)
            nmKill(serverName)
        else:
            msg("Server is already " + serverStatus, _LOG_LEVEL.INFO)
    except:
        raise

def serverStatus(serverName):
    '''Display status of server <serverName>'''
    try:
        #nmConnect(username, password, host, '5556',domainName, domainHome, 'SSL')
        serverStatus = nmServerStatus(serverName)
        if serverStatus == 'SHUTDOWN':
            msg("Server is " + serverStatus, _LOG_LEVEL.INFO)
        elif serverStatus == 'RUNNING':
            msg("Server is " + serverStatus, _LOG_LEVEL.INFO)
        elif serverStatus == 'UNKNOWN':
            msg("You specified an " + serverStatus +
                "Server!", _LOG_LEVEL.WARNING)
        else:
            msg("Something's wrong. Server is in state " +
                serverStatus, _LOG_LEVEL.ERROR)
    except:
        raise

#=========================================================================
# Node Manager functions
#=========================================================================
def startNodemgr():
    '''Start node manager'''
    startNodeManager()

def connectToNM():
    '''Connect to Node Manager'''
    msg("Connecting to NM with details {" + nmUsername + " | " + nmPassword + " | " +
        host + " | " + nmPort + " | " + domainName + " | " + domainHome + "}", _LOG_LEVEL.DEBUG)
    nmConnect(nmUsername, nmPassword, host, nmPort,
              domainName, domainHome, 'SSL')


#=========================================================================
# OSB Server Functions
#=========================================================================
def createOSBSession(sessionName):
    '''Create edit session'''
    msg("Creating session " + sessionName, _LOG_LEVEL.INFO)
    sessionMBean = findService(
        SessionManagementMBean.NAME, SessionManagementMBean.TYPE)
    sessionMBean.createSession(sessionName)
    msg("OSB Session Created: " + sessionName, _LOG_LEVEL.DEBUG)
    return sessionMBean

def activateSession(b, n, s, a):
    '''Activate edit session'''
    msg("Activate OSB Session: " + n, _LOG_LEVEL.INFO)
    b.activateSession(n, a + " " + s)

def discardSession(sessionManagementMBean, sessionName):
    '''discard edit session'''
    if sessionManagementMBean != None:
        if sessionManagementMBean.sessionExists(sessionName):
            sessionManagementMBean.discardSession(sessionName)
            msg("Session discarded " + serverStatus, _LOG_LEVEL.INFO)

def findWLService(serviceType, f, s, session, n):
    '''Find a service'''
    if (serviceType == _PROXY):
        srvConf = "ProxyServiceConfiguration." + n
        mbeanConfig = 'com.bea.wli.sb.management.configuration.ProxyServiceConfigurationMBean'
    elif (serviceType == _BUSINESS):
        srvConf = "BusinessServiceConfiguration." + n
        mbeanConfig = 'com.bea.wli.sb.management.configuration.BusinessServiceConfigurationMBean'
    else:
        raise 'Invalid Service Type ' + serviceType

    msg("Finding service: " + f + "/" + s, _LOG_LEVEL.INFO)
    mbean = findService(srvConf, mbeanConfig)
    folderRef = Refs.makeParentRef(f + '/')

    if (serviceType == _PROXY):
        serviceRef = Refs.makeProxyRef(folderRef, s)
    elif (serviceType == _BUSINESS):
        serviceRef = Refs.makeBusinessSvcRef(folderRef, s)
    else:
        raise 'Invalid Service Type ' + serviceType

    return serviceRef, mbean

def deleteOSBProject(alsbConfigurationMBean, projectName):
    '''Delete a OSB project'''
    try:
        msg("Trying to remove " + projectName, _LOG_LEVEL.INFO)
        projectRef = Ref(Ref.PROJECT_REF, Ref.DOMAIN, projectName)
        if alsbConfigurationMBean.exists(projectRef):
            msg("#### removing OSB project: " + projectName, _LOG_LEVEL.INFO)
            alsbConfigurationMBean.delete(Collections.singleton(projectRef))
            msg("#### removed project: " + projectName, _LOG_LEVEL.INFO)
        else:
            msg("OSB project <" + projectName +
                "> does not exist", _LOG_LEVEL.WARNING)
    except:
        msg("Error whilst removing project:" +
            sys.exc_info()[0], _LOG_LEVEL.ERROR)
        raise

def undeployProjectFromOSBDomain(projectName):
    '''Undeploy a OSB project'''
    try:
        domainRuntime()
        sessionName = "UndeployProjectStateSession_" + \
            str(System.currentTimeMillis())
        sessionManagementMBean = findService(
            SessionManagementMBean.NAME, SessionManagementMBean.TYPE)
        msg("SessionMBean started session", _LOG_LEVEL.INFO)
        sessionManagementMBean.createSession(sessionName)
        msg('Created session <' + sessionName + '>', _LOG_LEVEL.INFO)
        alsbConfigurationMBean = findService(
            ALSBConfigurationMBean.NAME + "." + sessionName, ALSBConfigurationMBean.TYPE)
        deleteOSBProject(alsbConfigurationMBean, projectName)
        sessionManagementMBean.activateSession(
            sessionName, "Complete project removal with customization using wlst")
    except:
        msg("Error whilst removing project:" +
            sys.exc_info()[0], _LOG_LEVEL.ERROR)
        discardSession(sessionManagementMBean, sessionName)
        raise

def undeployProjectsFromOSBDomain(projectNames):
    '''Undeploy multiple OSB projects'''
    sessionManagementMBean = None
    try:
        domainRuntime()
        sessionName = "UndeployProjectStateSession_" +  str(System.currentTimeMillis())
        sessionManagementMBean = findService(SessionManagementMBean.NAME, SessionManagementMBean.TYPE)
        msg("SessionMBean started session", _LOG_LEVEL.INFO)
        sessionManagementMBean.createSession(sessionName)
        msg('Created session <', sessionName, '>', _LOG_LEVEL.INFO)
        alsbConfigurationMBean = findService(ALSBConfigurationMBean.NAME + "." + sessionName, ALSBConfigurationMBean.TYPE)
        for projectName in projectNames:
            msg('Delete project ' + projectName, _LOG_LEVEL.INFO)
            deleteOSBProject(alsbConfigurationMBean, projectName)
        sessionManagementMBean.activateSession(sessionName, "Complete project removal with customization using wlst")
    except:
        msg("Error whilst removing project:" + sys.exc_info()[0], _LOG_LEVEL.ERROR)
        discardSession(sessionManagementMBean, sessionName)
        raise

def findProxyService(folder, serviceName, sessionName):
    '''Find a proxy service'''
    msg("Find proxy service: " + folder + "/" + serviceName, _LOG_LEVEL.INFO)
    pxyConf = "ProxyServiceConfiguration." + sessionName
    mbean = findService(pxyConf, 'com.bea.wli.sb.management.configuration.ProxyServiceConfigurationMBean')
    folderRef = Refs.makeParentRef(folder + '/')
    serviceRef = Refs.makeProxyRef(folderRef, serviceName)
    return serviceRef, mbean

def undeployProxyFromOSBDomain(relativePath, proxyServiceName):
    '''Remove a proxyservice'''
    try:
        domainRuntime()

        sessionName = "UndeployProxySession_" + str(System.currentTimeMillis())
        msg("Trying to remove " + proxyServiceName, _LOG_LEVEL.INFO)

        sessionManagementMBean = findService(
            SessionManagementMBean.NAME, SessionManagementMBean.TYPE)
        msg("SessionMBean started session", _LOG_LEVEL.INFO)
        sessionManagementMBean.createSession(sessionName)
        msg('Created session <' + sessionName + '>', _LOG_LEVEL.INFO)
        serviceRef, sessionBean = findProxyService(
            relativePath, proxyServiceName, sessionName)
        alsbConfigurationMBean = findService(
            ALSBConfigurationMBean.NAME + "." + sessionName, ALSBConfigurationMBean.TYPE)
        if alsbConfigurationMBean.exists(serviceRef):
            msg("#### removing OSB proxy service: " +
                proxyServiceName, _LOG_LEVEL.INFO)
            alsbConfigurationMBean.delete(Collections.singleton(serviceRef))
            sessionManagementMBean.activateSession(
                sessionName, "Complete service removal with customization using wlst")
        else:
            msg("OSB project <" + proxyServiceName +
                "> does not exist", _LOG_LEVEL.WARNING)
            discardSession(sessionManagementMBean, sessionName)
    except:
        msg("Error whilst removing project:" +
            sys.exc_info()[0], _LOG_LEVEL.ERROR)
        discardSession(sessionManagementMBean, sessionName)
        raise

def removeFolderFromOSBDomain(folder):
    '''remove a folder'''
    try:
        domainRuntime()

        sessionName = "RemoveFolderSession_" + str(System.currentTimeMillis())
        msg("Trying to remove " + folder, _LOG_LEVEL.INFO)

        sessionManagementMBean = findService(
            SessionManagementMBean.NAME, SessionManagementMBean.TYPE)
        msg("SessionMBean started session", _LOG_LEVEL.INFO)
        sessionManagementMBean.createSession(sessionName)
        msg('Created session <' + sessionName + '>', _LOG_LEVEL.INFO)
        folderRef = Refs.makeParentRef(folder)
        alsbConfigurationMBean = findService(
            ALSBConfigurationMBean.NAME + "." + sessionName, ALSBConfigurationMBean.TYPE)
        if alsbConfigurationMBean.exists(folderRef):
            msg("#### removing OSB folder: " + folder, _LOG_LEVEL.INFO)
            alsbConfigurationMBean.delete(Collections.singleton(folderRef))
            sessionManagementMBean.activateSession(
                sessionName, "Complete service removal with customization using wlst")
        else:
            msg("OSB folder <" + folder + "> does not exist", _LOG_LEVEL.WARNING)
            discardSession(sessionManagementMBean, sessionName)
        print
    except:
        msg("Error whilst removing project:" +
            sys.exc_info()[0], _LOG_LEVEL.ERROR)
        discardSession(sessionManagementMBean, sessionName)
        # raise

def disableProxyService(serviceFullPath):
    '''disable proxy service'''
    setServiceState(_PROXY, serviceFullPath, _DISABLE)

def enableProxyService(serviceFullPath):
    '''enable proxy service'''
    setServiceState(_PROXY, serviceFullPath, _ENABLE)

def disableBusinessService(serviceFullPath):
    '''disable business service'''
    setServiceState(_BUSINESS, serviceFullPath, _DISABLE)

def enableBusinessService(serviceFullPath):
    '''enable business service'''
    setServiceState(_BUSINESS, serviceFullPath, _ENABLE)

def setServiceState(serviceType, serviceFullPath, stateOnOff):
    '''set state of service'''
    try:
        sessionName = "CustomSession-" + \
            Long(System.currentTimeMillis()).toString()
        osbSession = CreateOSBSession(sessionName)

        projectPath = os.path.dirname(serviceFullPath)
        serviceName = os.path.basename(serviceFullPath)

        service, sessionBean = FindService(
            serviceType, projectPath, serviceName, osbSession, sessionName)
        setStateService(sessionBean, service, stateOnOff)
        ActivateSession(osbSession, sessionName, serviceName, stateOnOff)
    except:
        raise

def setStateService(b, s, a):
    '''set state of service'''
    if a == _DISABLE:
        msg("Disable Service", _LOG_LEVEL.INFO)
        b.disableService(s)
    else:
        msg("Enable Service", _LOG_LEVEL.INFO)
        b.enableService(s)
#=========================================================================
# JMS Functions
#=========================================================================
def deleteJMSBridges(bridgeNames):
    '''Delete all JMS bridges in bridgeNames parameter. If bridgeNames = None then all bridges will be deleted.'''
    edit()
    startEdit()
    try:
        if (bridgeNames != None):
            for name in bridgeNames:
                msg("Deleting JMS Bridge " + name, _LOG_LEVEL.INFO)
                bridge = getMBean('/MessagingBridges/' + name)
                if (bridge == None):
                    msg("JMS Bridge " + name + " not found!", _LOG_LEVEL.WARNING)
                    cancelEdit('y')
                else:
                    cmo.destroyMessagingBridge(bridge)
        else:
            listOfBridges = cmo.getMessagingBridges()
            for bridge in listOfBridges:
                msg("Deleting JMS Bridge " + bridge, _LOG_LEVEL.INFO)
                cmo.destroyMessagingBridge(bridge)
        save()
        activate()
    except:
        cancelEdit('y')


def deleteJMSBridge(name):
    '''Delete a complete message bridge:javax.management.ObjectName'''
    deleteJMSBridges([name])

# delete a bridge destination (source or target) by name
def deleteJMSBridgeDestination(name):
    msg("Deleting JMS Bridge Destination", _LOG_LEVEL.INFO)
    edit()
    startEdit()
    destination = getMBean('/JMSBridgeDestinations/' + name) # get jmsBridgeDestination:javax.management.ObjectName
    if (destination == None):
        msg("JMS Bridge Destination " + name + " not found!", _LOG_LEVEL.WARNING)
        cancelEdit('y')
    else:
        #cmo.destroyBridgeDestination(bridgeDestination:javax.management.ObjectName)
        cmo.destroyJMSBridgeDestination(destination)
        #save()
        #activate()

# delete a complete JMS module by bean:javax.management.ObjectName


def deleteJMSModule(object):
    msg("Still TODO", _LOG_LEVEL.INFO)
    # destroyJMSSystemResource(object)

# delete a JMS Queue by name


def deleteJMSQueue(jmsSystemResource, jmsModuleName, queueName, isDistributed=false):
    msg("Still TODO", _LOG_LEVEL.INFO)
    # cd('/JMSSystemResources/'+jmsSystemResource+'/JMSResource/'+jmsModuleName)
    # destroy the queue by providing the queue mbean
    # if (isDistributed)
    # cmo.destroyDistributedQueue(getMBean('/JMSSystemResources/'+jmsSystemResource+'/JMSResource/'+jmsModuleName+'/Queues/'+queueName))
    # else
    # cmo.destroyQueue(getMBean('/JMSSystemResources/'+jmsSystemResource+'/JMSResource/'+jmsModuleName+'/Queues/'+queueName))

# delete a JMS Topic by name


def deleteJMSTopic(jmsSystemResource, jmsModuleName, topicName, isDistributed=false):
    msg("Still TODO", _LOG_LEVEL.INFO)
    # cd('/JMSSystemResources/'+jmsSystemResource+'/JMSResource/'+jmsModuleName)
    # destroy the topic by providing the queue mbean
    # if (isDistributed)
    # cmo.destroyDistributedTopic(getMBean('/JMSSystemResources/'+jmsSystemResource+'/JMSResource/'+jmsModuleName+'/Queues/'+topicName))
    # else
    # cmo.destroyTopic(getMBean('/JMSSystemResources/'+jmsSystemResource+'/JMSResource/'+jmsModuleName+'/Queues/'+topicName))

# delete a bridge destination (source or target)
def deleteJMSModule(name):
    msg("Still TODO", _LOG_LEVEL.INFO)

# delete one JMS server (and it's subcomponents)
def deleteJMSServer(name):
    msg("Still TODO", _LOG_LEVEL.INFO)
    # destroyJMSServer(jmsServer:javax.management.ObjectName)

def deleteFileStore(name, persistent='true'):
    msg("Still TODO", _LOG_LEVEL.INFO)

#=========================================================================
# JCA Functions
#=========================================================================
def deleteDBAdapter(name):
    msg("Still TODO", _LOG_LEVEL.INFO)

def deleteAQAdapter(name):
    msg("Still TODO", _LOG_LEVEL.INFO)

#=========================================================================
# General functions (i.e. usage, output, logging, error, etc.)
#=========================================================================
def usage(operation='all'):
    if operation == 'all':
        operations[1]()
    elif operation == 'admin':
        operations[2]()
    elif operation == 'osb':
        operations[3]()
    elif operation == 'proxyService':
        operations[4]()
    elif operation == 'businessService':
        operations[5]()
    else:
        operations[0]()

def usageFunctions():
    print "The avaliable functions are:"
    print "   init & echoEnv"
    print "   disableProxyService & enableProxyService"
    print "   startAdmin & stopAdmin & statusAdmin"
    print "   startOSB1 & stopOSB1 & statusOSB1"


def usageUnknown():
    print "That function is Unknown."
    usageFunctions()


def usageInit():
    print "Usage: initEnv(env)"
    print "   Where env is one of the environments defined in the properties file."


def usageAdmin():
    print "Usage: Admin Server"
    print "   startAdmin()"
    print "   stopAdmin()"
    print "   statusAdmin()"


def usageOSB():
    print "Usage: OSB Server"
    print "   startOSB(n)"
    print "   stopOSB(n)"
    print "   statusOSB(n)"
    print "   n server number"


def usageProxyService():
    print "Usage: Proxy services"
    print "   disableProxyService(proxyServiceName)"
    print "   enableProxyService(proxyServiceName)"
#  print "   -f file with a list of proxy services"


def usageBusinessService():
    print "Usage: Business services"
    print "   disableBusinessService(businessServiceName)"
    print "   enableBusinessService(businessServiceName)"
#  print "   -f file with a list of business services"


# map the inputs to the function blocks
operations = {
    0: usageUnknown,
    1: usageFunctions,
    2: usageAdmin,
    3: usageOSB,
    4: usageProxyService,
    5: usageBusinessService,
}

def set_LOG_LEVEL(logLevel):
    '''set current log level'''
    currentLogLevel = logLevel

def msg(m, logLevel):
    '''write messages to the output'''
    if logLevel >= currentLogLevel:
        print m

def quit():
    '''close connections and exit'''
    #cancelEdit()
    closeWLSConnection()
    exit()
