from java.util import HashMap
from java.util import HashSet
from java.util import ArrayList
from java.io import FileInputStream
from java.io import FileOutputStream

from com.bea.wli.config import Ref
from com.bea.wli.config.customization import Customization
from com.bea.wli.sb.management.importexport import ALSBImportOperation
from com.bea.wli.config.resource import ResourceQuery

from xml.dom.minidom import parse

import sys
import os
import re
from datetime import datetime


#http://wlstbyexamples.blogspot.co.uk/2015/08/database-connect-from-wlst-offlinejython.html#.Vmrh70qyNBc
#from com.ziclix.python.sql import zxJDBC

#=======================================================================================
# Entry function to deploy project configuration and resources
#        into a ALSB domain
#=======================================================================================

def importToOSB(environmentName, mavenGroupId, mavenArtifactId, mavenVersionId, serviceGroupName, serviceType, serviceName, interfaceVersion, jarFileLocation, force, pwd):
    print 'environment name: ', environmentName
    print 'maven artifact coordinates: ', mavenGroupId, ':', mavenArtifactId, ':', mavenVersionId
    print 'jar file location: ', jarFileLocation
    print 'User home: ', os.environ["HOME"]
    userHome = os.environ["HOME"]
    workspacePath = System.getenv('WORKSPACE')
    if workspacePath == None:
        print 'WORKSPACE environment varible not set'
        raise
    try:
        artifactGroupMappings = loadProps(userHome + "/osb_maven_group_artifactids.properties")
        print "Loaded osb_maven_group_artifactids.properties"
        envConfigProp = loadProps(userHome + "/environments.properties")
        print "Loaded environments.properties"
        targetingConfigProp = loadProps(userHome + "/osb_maven_targets.properties")
        print "Loaded osb_maven_targets.properties"
        #find service target domains
        targetDomains = targetingConfigProp.get(serviceGroupName + "." + serviceName)
        if targetDomains == None:
            targetDomains = targetingConfigProp.get(serviceGroupName)
            if targetDomains == None:
                print "Targeting metadata not found for " + serviceGroupName + ":" + serviceName
                raise
        for targetDomain in targetDomains.split(","):
            customizationFile = getCustomizationFilePath(environmentName, serviceGroupName, serviceName, interfaceVersion, targetDomain)
            if not os.path.isfile(customizationFile):
                print 'Customization file not found for service ' + mavenArtifactId + ', environment ' + environmentName + ', domain ' + targetDomain
                raise

        currentDeployedVersion = getDeployedVersion(serviceGroupName, serviceName, interfaceVersion, environmentName)
        auditAction("Starting deployment of " + serviceGroupName + ' : ' + serviceName + ' ' + interfaceVersion + ' version ' + mavenVersionId + " to " + environmentName + " environment. Current version: " + currentDeployedVersion)

        compareResultMaven = mavenVersionCompare(currentDeployedVersion,mavenVersionId)

        #if currentDeployedVersion != "N/A" and currentDeployedVersion >= mavenVersionId:
        if currentDeployedVersion != "N/A" and compareResultMaven:
            #deployed version is known to be equal or more recent than the one on deployment
            if force != "true":
                auditAction("Cancelling deployment of " + serviceGroupName + ' : ' + serviceName + ' ' + interfaceVersion + ' version ' + mavenVersionId + " to " + environmentName + " environment. Version is already higher or equal (" + currentDeployedVersion + " Vs " + mavenVersionId + ") and deployment is not forced")
                print "Cancelling deployment: deployed version is more recent (" + currentDeployedVersion + " Vs " + mavenVersionId + "). If you are sure you want to do this, please use the --force option"
                raise

        if not validateDependencies(environmentName, serviceGroupName, serviceName, interfaceVersion):
            auditAction("Cancelling deployment of " + serviceGroupName + ' : ' + serviceName + ' ' + interfaceVersion + ' version ' + mavenVersionId + " to " + environmentName + " environment. Dependencies not met")
            print "Cancelling deployment: dependencies not met. Please deploy dependencies first and try again"
            raise

        for targetDomain in targetDomains.split(","):
            deployToTarget(envConfigProp, mavenGroupId, mavenArtifactId, mavenVersionId, serviceGroupName, serviceType, serviceName, interfaceVersion, jarFileLocation, environmentName, targetDomain, pwd)

            updateDeployedVersion(serviceGroupName, serviceName, interfaceVersion, mavenVersionId, environmentName)
        auditAction("Service " + mavenGroupId + ' : ' + mavenArtifactId + ' version ' + mavenVersionId + " deployed to " + environmentName + " environment")
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise

#=======================================================================================
# Utility function to compare Maven versions
#=======================================================================================
def mavenVersionCompare(currentMavenVersion, requiredMavenVersion):
    print 'Comparing maven versions ' + currentMavenVersion + ' with ' + requiredMavenVersion
    if currentMavenVersion == 'N/A' or requiredMavenVersion == 'N/A':
        return True

    # = temporary fix to remove SNAPSHOT
    toReplace = "-SNAPSHOT"
    currentMavenVersion.replace(toReplace,'')
    requiredMavenVersion.replace(toReplace,'')
    # ===
    versionRegex = re.compile('^\d*.\d*.\d*$')
    if versionRegex.match(currentMavenVersion) and versionRegex.match(requiredMavenVersion):
        currentMavenVersion = [int(i) for i in currentMavenVersion.split('.')]
        requiredMavenVersion = [int(i) for i in requiredMavenVersion.split('.')]
        result = currentMavenVersion >= requiredMavenVersion
    else:
        print 'Maven versions are not valid.'
        result = False

    return result
def deployToTarget(envConfigProp, mavenGroupId, mavenArtifactId, mavenVersionId, serviceGroupName, serviceType, serviceName, interfaceVersion, jarFileLocation, environmentName, domainName, pwd):
    print 'Deploying ' + mavenGroupId + ':' + mavenArtifactId + ' ' + interfaceVersion + ' (' + mavenVersionId + ') to ' + domainName + ' in ' + environmentName
    auditAction('Attempting deployment of ' + mavenGroupId + '::' + mavenArtifactId + ' version ' + mavenVersionId + "(" + interfaceVersion + ") to domain " + domainName + " in " + environmentName + " environment")

    try:
        SessionMBean = None
        targetName = environmentName + "." + domainName
        admin_host = envConfigProp.get("env." + targetName + ".admin_host")
        admin_port = envConfigProp.get("env." + targetName + ".admin_port")
        adminUrl = "t3://" + admin_host + ":" + admin_port
        importUser = envConfigProp.get("env." + targetName + ".username")
        importPassword = envConfigProp.get("env." + targetName + ".password")
        if pwd != None:
            importPassword = pwd

        print 'Target url: ', adminUrl
        print 'Importing :', jarFileLocation

        if importUser == None:
            print 'Connecting with config files'
            connectToServerWithConfig(configFile, keyFile, adminUrl)
        else:
            print 'Connecting with username/pwd'
            connectToServer(importUser, importPassword, adminUrl)

        print 'Attempting to import :', jarFileLocation, " on OSB Admin Server listening on :", adminUrl

        theBytes = readBinaryFile(jarFileLocation)
        print 'Read file', jarFileLocation
        sessionName = createSessionName()
        print 'Created session', sessionName
        SessionMBean = getSessionManagementMBean(sessionName)
        print 'SessionMBean started session'
        ALSBConfigurationMBean = findService(String("ALSBConfiguration.").concat(sessionName), "com.bea.wli.sb.management.configuration.ALSBConfigurationMBean")

        listOfAutoBackupEnabledEnvironments = envConfigProp.get("autobackupOnDeployment")
        if (listOfAutoBackupEnabledEnvironments != None):
            if (environmentName in listOfAutoBackupEnabledEnvironments):
                #take backup from domain
                print "Backing up artifact resources including the common bits"
                allRefs = None
                if (serviceGroupName == 'Common'):
                    #step 1: find version specific resources e.g. Common_CanonicalDataModel/v1
                    projectResourcesQuery = ResourceQuery(None)
                    projectResourcesQuery.setPath(serviceGroupName + '_' + serviceName + '/' + interfaceVersion + '/*')
                    artifactRefs = ALSBConfigurationMBean.getRefs(projectResourcesQuery)
                    allRefs = artifactRefs
                else:
                    #take backup from domain
                    print "Backing up artifact resources including the common bits"
                    #step 1: find project's own resources e.g. QueryServices/data/Parcel/v1
                    projectResourcesQuery = ResourceQuery(None)
                    projectResourcesQuery.setPath(serviceGroupName + '/' + serviceType + '/' + serviceName + "/" + interfaceVersion + "/*")
                    artifactRefs = ALSBConfigurationMBean.getRefs(projectResourcesQuery)
                    #step 2: find common group project resources e.g. QueryServices/common/v1
                    commonGroupResourcesQuery = ResourceQuery(None)
                    commonGroupResourcesQuery.setPath(serviceGroupName + '/common/' + interfaceVersion + "/*")
                    commonGroupRefs = ALSBConfigurationMBean.getRefs(commonGroupResourcesQuery)
                    #combine all the refs

                    allRefs = commonGroupRefs
                    allRefs.addAll(artifactRefs)

                exportJarBytes = ALSBConfigurationMBean.export(allRefs, false, None)
                todaysFormattedDate = java.text.SimpleDateFormat("yyyyMMdd").format(java.util.Date())
                exportFolder = os.environ["HOME"] + "/backups/" + environmentName
                File(exportFolder).mkdirs()
                if System.getenv('BUILD_TAG') is not None:
                    exportFileName = todaysFormattedDate + "_" + System.getenv('BUILD_TAG') + "_" + domainName + ".jar"
                else:
                    exportFileName = todaysFormattedDate + "_" + domainName + ".jar"
                exportFile = File(exportFolder, exportFileName)
                out = FileOutputStream(exportFile)
                out.write(exportJarBytes)
                out.close()
                print "Automatic backup taken to: "+ exportFileName

        print 'Uploading jar file'
        ALSBConfigurationMBean.uploadJarFile(theBytes)
        print 'Jar file uploaded'

        print 'Performing deployment'
        alsbJarInfo = ALSBConfigurationMBean.getImportJarInfo()
        #23/05/2016 Commenting this out as it is causing a deployment issue
#        alsbImportPlan = alsbJarInfo.getDefaultImportPlan()
#        alsbImportPlan.setPassphrase(passphrase)
#        alsbImportPlan.setPreserveExistingEnvValues(true)
        importResult = ALSBConfigurationMBean.importUploaded(None) #alsbImportPlan)
        if importResult.getFailed().isEmpty() == false:
            print 'One or more resources could not be imported properly:'
            printDiagMap(importResult.getImportDiagnostics())
            raise

        customizationFile = getCustomizationFilePath(environmentName, serviceGroupName, serviceName, interfaceVersion, domainName)
        print 'Applying customization file: ', customizationFile
        ALSBConfigurationMBean.customize(Customization.fromXML(FileInputStream(customizationFile)))

        groupCustomizationFile = getGroupCustomizationFilePath(environmentName, serviceGroupName, interfaceVersion, domainName)
        if (os.path.isfile(groupCustomizationFile)):
            print 'Applying group level customization file: ', groupCustomizationFile
            ALSBConfigurationMBean.customize(Customization.fromXML(FileInputStream(groupCustomizationFile)))

        print 'Activating change session'
        buildTag = System.getenv('BUILD_TAG')
        if buildTag == None:
            buildTag = ""
        else:
            buildTag = ". Jenkins build tag: " + buildTag
        SessionMBean.activateSession(sessionName, "Scripted import of " + serviceGroupName + ' : ' + serviceName + ' ' + interfaceVersion + ' version ' + mavenVersionId + buildTag)
        print "Deployment of : " + serviceGroupName + ' : ' + serviceName + ' ' + interfaceVersion + ' version ' + mavenVersionId + " successful"
        auditAction("Service " + serviceGroupName + ' : ' + serviceName + ' ' + interfaceVersion + ' version ' + mavenVersionId + " deployed to domain " + domainName + " in " + environmentName + " environment")
        SessionMBean = None
    except:
        auditAction("Failed to deploy service " + serviceGroupName + ' : ' + serviceName + ' ' + interfaceVersion + ' version ' + mavenVersionId + " to domain " + domainName + " in " + environmentName + " environment")
        print "Unexpected error:", sys.exc_info()[0]
        dumpStack()
        if SessionMBean != None:
            SessionMBean.discardSession(sessionName)
        raise

#return the path to the customization file. Should there be a domain specific one, use it. Otherwise, default to the environment generic one
def getCustomizationFilePath(environmentName, serviceGroupName, serviceName, interfaceVersion, targetDomain) :
    filePath = System.getenv('WORKSPACE') + '/Deployment/config/' + environmentName + '/OSB_customization/' + serviceGroupName + '/'
    fileName = serviceName + '_' + interfaceVersion + '_' + targetDomain + '.xml'
    if not os.path.isfile(filePath + fileName):
	    fileName = serviceName + '_' + interfaceVersion + '.xml'
#    print "getCustomizationFilePath(" + environmentName + ', ' + serviceGroupName + ', ' + serviceName + ', ' + interfaceVersion + ', ' + targetDomain + '): ' + filePath + fileName
    return filePath + fileName

def getGroupCustomizationFilePath(environmentName, serviceGroupName, interfaceVersion, targetDomain) :
    return getCustomizationFilePath(environmentName, serviceGroupName, 'Common', interfaceVersion, targetDomain)

def validateDependencies(environmentName, serviceGroupName, serviceName, interfaceVersion) :
    #TODO improve so pom.xml is taken from Nexus when it applies
    print "Dependency validation start"
    dependenciesMet = true
    pomFilePath = System.getenv('WORKSPACE') + '/OSB/Metadata/Maven/' + serviceGroupName + '/' + serviceName + '_' + interfaceVersion + '.pom'
    if not os.path.isfile(pomFilePath):
        print "Service's POM file not found (" + pomFilePath + ')'
        return false
    pomFile = parse(pomFilePath)
    for dependenciesNode in pomFile.getElementsByTagName('dependencies'):
        for dependencyNode in dependenciesNode.getElementsByTagName('dependency'):
            dependencyGroupId = dependencyNode.getElementsByTagName('groupId')[0].firstChild.data
            dependencyArtifactId = dependencyNode.getElementsByTagName('artifactId')[0].firstChild.data
            dependencyVersion = dependencyNode.getElementsByTagName('version')[0].firstChild.data
            deployedVersion = getDeployedVersion(serviceGroupFromMavenGroup(dependencyGroupId)
                                               , serviceNameFromMavenArtifact(dependencyArtifactId)
                                               , interfaceVersionFromMavenArtifact(dependencyArtifactId)
                                               , environmentName)
            validationResult = "[OK]"
            if deployedVersion == "N/A" or deployedVersion < dependencyVersion:
                dependenciesMet = false
                validationResult = "[Validation failed]"
            print "Validation of deployed version of : " + dependencyGroupId + ' : ' + dependencyArtifactId + ' on ' + environmentName + ". " + validationResult + " Expected " + dependencyVersion + ", found " + deployedVersion
    print "Dependency validation complete"
    return dependenciesMet

def updateDeployedVersion(serviceGroupName, serviceName, interfaceVersion, mavenVersionId, environmentName) :
    propInputStream = FileInputStream(os.environ["HOME"] + "/osb_deployed_versions.properties")
    configProps = Properties()
    configProps.load(propInputStream)
    propInputStream.close()
    configProps.put(serviceGroupName + "." + serviceName + "." + interfaceVersion + "." + environmentName, mavenVersionId)
    configProps.store(FileOutputStream(os.environ["HOME"] + "/osb_deployed_versions.properties"), "OSB Deployed versions. Updated on " + str(datetime.now()))

def getDeployedVersion(serviceGroupName, serviceName, interfaceVersion, environmentName) :
    propInputStream = FileInputStream(os.environ["HOME"] + "/osb_deployed_versions.properties")
    configProps = Properties()
    configProps.load(propInputStream)
    result = configProps.get(serviceGroupName + "." + serviceName + "." + interfaceVersion + "." + environmentName)
    if result == None:
        return "N/A"
    return result

def auditAction(actionText) :
    buildTag = System.getenv('BUILD_TAG')
    if buildTag == None:
        buildTag = ""
    else:
        buildTag = " build " + buildTag + " | "
    logFile = open(os.environ["HOME"] + "/osb_deployment.log", "ab")
    logFile.write("[" + str(datetime.now()) + "] " + buildTag + actionText + "\n")
    logFile.close()

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

#=======================================================================================
# Connect to the Admin Server
#=======================================================================================

def connectToServer(username, password, url):
    connect(username, password, url)
    domainRuntime()

def connectToServerWithConfig(configFile, keyFile, serverurl):
    connect(userConfigFile=configFile, userKeyFile=keyFile, url=serverurl)
    domainRuntime()

#=======================================================================================
# Utility function to read a binary file
#=======================================================================================
def readBinaryFile(fileName):
    file = open(fileName, 'rb')
    bytes = file.read()
    return bytes

#=======================================================================================
# Utility function to create an arbitrary session name
#=======================================================================================
def createSessionName():
    sessionName = String("SessionScript"+Long(System.currentTimeMillis()).toString())
    return sessionName

#=======================================================================================
# Utility function to load a session MBeans
#=======================================================================================
def getSessionManagementMBean(sessionName):
    SessionMBean = findService("SessionManagement", "com.bea.wli.sb.management.configuration.SessionManagementMBean")
    SessionMBean.createSession(sessionName)
    return SessionMBean

def serviceGroupFromMavenGroup(mavenGroupId):
    return mavenGroupId.split('.')[1]

def serviceTypeFromMavenGroup(mavenGroupId):
    mavenGroupParts =  mavenGroupId.split('.')
    if (len(mavenGroupParts) == 2):
        return ''
    else:
        return mavenGroupParts[2]

def serviceNameFromMavenArtifact(mavenArtifaceId):
    return mavenArtifaceId.split('_')[0]

def interfaceVersionFromMavenArtifact(mavenArtifaceId):
    return mavenArtifaceId.split('_')[1]

# IMPORT script init
try:
    # import the service bus configuration
    # argv[1] is the target environment name
    targetEnvironmentName = sys.argv[1]
    # argv[2] is the maven group id
    mavenGroupId = sys.argv[2]
    # argv[3] is the maven artifact id
    mavenArtifactId = sys.argv[3]
    # argv[4] is the service version id
    mavenVersionId = sys.argv[4]
    # argv[5] is the location of the jar file to deploy
    jarLocation = sys.argv[5]
    # argv[6] is the optional parameter (--force is expected so far)

    force = "false"
    if len(sys.argv) > 6:
        force = sys.argv[6]
    pwd = None
    if len(sys.argv) > 7:
        pwd = sys.argv[7]

    importToOSB(targetEnvironmentName, mavenGroupId, mavenArtifactId, mavenVersionId
              , serviceGroupFromMavenGroup(mavenGroupId), serviceTypeFromMavenGroup(mavenGroupId), serviceNameFromMavenArtifact(mavenArtifactId), interfaceVersionFromMavenArtifact(mavenArtifactId)
              , jarLocation, force, pwd)

except:
    print "Unexpected error: ", sys.exc_info()[0]
    dumpStack()
    raise
