from java.io import FileInputStream
from java.io import FileOutputStream
from java.io import ByteArrayInputStream
from java.util import ArrayList
from java.util import Collections
from java.util import StringTokenizer

from javax.xml.parsers import DocumentBuilder
from javax.xml.parsers import DocumentBuilderFactory
from com.sun.org.apache.xpath.internal import XPathAPI

from com.bea.wli.config.resource import ResourceQuery

from java.util.zip import ZipEntry
from java.util.zip import ZipFile
from java.util.zip import ZipInputStream

import os
import sys
import jarray

from xml.dom.minidom import parse,parseString

#=======================================================================================
# Utility function to load properties from a config file
#=======================================================================================
def checkForInconsistencies(environment, domain, password):
    try:
        envConfigProp = loadProps(os.environ["HOME"] + "/environments.properties")
		propertyPrefix = "env." + environment + "." + domain + "."

        adminUrl = 't3://' + envConfigProp.get(propertyPrefix + "admin_host") + ':' + envConfigProp.get(propertyPrefix + "admin_port")
        exportUser = envConfigProp.get(propertyPrefix + "username")
        exportPasswd = envConfigProp.get(propertyPrefix + "password")

        connectToServer(exportUser, exportPasswd, adminUrl)

        SessionMBean = findService("SessionManagement", "com.bea.wli.sb.management.configuration.SessionManagementMBean")
        SessionMBean.createSession(String("SessionScript" + Long(System.currentTimeMillis()).toString()))
        ALSBConfigurationMBean = findService("ALSBConfiguration", "com.bea.wli.sb.management.configuration.ALSBConfigurationMBean")
        print "ALSBConfiguration MBean found"

        resourcesQuery = ResourceQuery(None)
        resourcesQuery.setLocalName("version")
        zipFileContent = ALSBConfigurationMBean.export(ALSBConfigurationMBean.getRefs(resourcesQuery), false, None)

        zipFile = ZipInputStream(ByteArrayInputStream(zipFileContent))
        zipEntry = zipFile.getNextEntry()
        bufferSize = 32 * 1024
        buffer = jarray.zeros(bufferSize, "b")
        while (zipEntry != None):
            if "ExportInfo" != zipEntry.getName():
                len = zipFile.read(buffer, 0, bufferSize)
                xmlContent = String(buffer, 0, len, "UTF-8")
                osbXmlDoc = parseDom(xmlContent)
                nsNode = createNsNode(osbXmlDoc, "con=http://www.bea.com/wli/sb/resources/config")
                versionXmlContent = XPathAPI.eval(osbXmlDoc, "/con:xmlEntry/con:xml-content", nsNode).str()
                versionXmlDoc = parseDom(String(versionXmlContent))
                nsNode2 = createNsNode(versionXmlDoc, "mvn=http://maven.apache.org/POM/4.0.0")
                groupId = XPathAPI.eval(versionXmlDoc, "/mvn:project/mvn:groupId", nsNode2).str()
                artifactId = XPathAPI.eval(versionXmlDoc, "/mvn:project/mvn:artifactId", nsNode2).str()
                versionId = XPathAPI.eval(versionXmlDoc, "/mvn:project/mvn:version", nsNode2).str()
                #print 'found ' + groupId + '::' + artifactId + '::' + versionId
				deployedVersionFromFile = getDeployedVersionFromFile(artifactId, environment)
				if deployedVersionFromFile != versionId:
                    print 'Inconsistent version found! current is ' + versionId + ', while registered one is ' + deployedVersionFromFile
            zipEntry = zipFile.getNextEntry()

    except:
        raise

def parseDom(xmlText):
    baos = ByteArrayInputStream(xmlText.getBytes("UTF-8"))
    dfactory = DocumentBuilderFactory.newInstance()
    dfactory.setNamespaceAware(true)
    dfactory.setValidating(false)
    documentBuilder = dfactory.newDocumentBuilder()
    return documentBuilder.parse(baos)

def createNsNode(inputDoc, namespaces):
    nsNode = inputDoc.createElement("NAMESPACE")
    st = StringTokenizer(namespaces)
    while (st.hasMoreTokens()):
        token = st.nextToken().split('=')
        nsNode.setAttribute("xmlns:" + token[0], token[1])
    return nsNode;

def getDeployedVersionFromFile(mavenArtifactId, environmentName) :
    propInputStream = FileInputStream(os.environ["HOME"] + "/osb_deployed_versions.properties")
    configProps = Properties()
    configProps.load(propInputStream)
    result = configProps.get(mavenArtifactId + "." + environmentName)
    if result == None:
        return "N/A"
    return result

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

# EXPORT script init
try:
    checkForInconsistencies(sys.argv[1], sys.argv[2], sys.argv[3])

except:
#    print "Unexpected error: ", sys.exc_info()[0]
    dumpStack()
    raise