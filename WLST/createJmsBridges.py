#========================================
#  JMS Bridge Configuration script.
#  FileName:  jmsBridges.py
#=========================================
from java.util import *
from java.io import FileInputStream
import sys
import jarray

import os
#import dircache
#from java.io import File
#from java.lang import String

def loadProps(configPropFile):
	propInputStream = FileInputStream(configPropFile)
	configProps = Properties()
	configProps.load(propInputStream)
	return configProps

def deployToDomain(domainName):		
	global envConfigProp
	global environmentName
	global jmsBridgeGroupName
	global workspacePath
	global passwordOverride
	print "Deploying to domain " + domainName + " in environment " + environmentName
	targetName = environmentName + "." + domainName
	admin_host = envConfigProp.get("env." + targetName + ".admin_host")
	admin_port = envConfigProp.get("env." + targetName + ".admin_port")
	adminUrl = "t3://" + admin_host + ":" + admin_port
	wlsUser = envConfigProp.get("env." + targetName + ".username")
	wlsPassword = envConfigProp.get("env." + targetName + ".password")
	if passwordOverride != None:
		wlsPassword = passwordOverride

	#find file for the environment
	dsConfigFolderPath = workspacePath + '/Deployment/config/' + environmentName + '/JMSBridge/'
	dsConfigFileName = jmsBridgeGroupName + '.properties'
	if not os.path.isfile(dsConfigFolderPath + dsConfigFileName):
		dsConfigFileName = jmsBridgeGroupName + '_' + domainName + '.properties'
		if not os.path.isfile(dsConfigFolderPath + dsConfigFileName):
			print "Properties file not found for this environment/domain"
			raise 

	print "Connecting to " + adminUrl + " as " + wlsUser
	connect(wlsUser, wlsPassword, adminUrl)
	edit()
	startEdit()
	numChanges = 0

	configProps = loadProps(dsConfigFolderPath + dsConfigFileName)
	if configProps.get("jmsBridgeNames") is not None:
		jmsbNames = configProps.get("jmsBridgeNames").split(",")
		for jmsbName in jmsbNames:
			# if Bridge already exists skip
			print "Creating JMS Bridge Source Destination"
			MessagingBridge = configProps.get(jmsbName + ".MessageBridgeName")
			print "checking ... " + MessagingBridge
			ref = getMBean("/MessagingBridges/" + MessagingBridge)
			if(ref == None):
				numChanges += 1
				sDest = configProps.get(jmsbName + ".S_Dest")
				sConnURL = configProps.get(jmsbName + ".S_ConnURL")
				sConnFJNDI = configProps.get(jmsbName + ".S_ConnFJNDI")
				sDestJNDI = configProps.get(jmsbName + ".S_DestJNDI")
				sDestType = configProps.get(jmsbName + ".S_DestType")
				src = createDestination(sDest,sConnURL,sConnFJNDI,sDestJNDI,sDestType)

				print "Creating JMS Bridge Target Destination "
				 
				tDest = configProps.get(jmsbName + ".T_Dest") 
				tConnURL = configProps.get(jmsbName + ".T_ConnURL") 
				tConnFJNDI = configProps.get(jmsbName + ".T_ConnFJNDI") 
				tDestJNDI = configProps.get(jmsbName + ".T_DestJNDI") 
				tDestType = configProps.get(jmsbName + ".T_DestType")

				target = createDestination(tDest,tConnURL,tConnFJNDI,tDestJNDI,tDestType)

				print "Creating JMS Bridge"
				cluster = configProps.get(jmsbName + ".Target") 
				qos = configProps.get(jmsbName + ".QualityOfService") 
				createBridge(MessagingBridge,cluster,src,target,qos)
			else:
				pass

	if numChanges > 0:
		save()
		activate(block = "true")
		print "==> JMSBridge creation finished ... Please double check from WLS Console..."
	else:
		cancelEdit('y')

	disconnect()


def createDestination(JMSBridgeDestination,ConnectionURL,ConnectionFactoryJNDIName,DestinationJNDIName,DestinationType):
	if getMBean('/JMSBridgeDestinations/' + JMSBridgeDestination ) is None:
		print "Creating JMS Bridge destination #%s#" % JMSBridgeDestination
		cd('/')
		bridgeDestination = cmo.createJMSBridgeDestination(JMSBridgeDestination)
		cd("/JMSBridgeDestinations/" + JMSBridgeDestination )
		cmo.setDestinationType( DestinationType )
		cmo.setConnectionURL( ConnectionURL )
		cmo.setConnectionFactoryJNDIName( ConnectionFactoryJNDIName )
		cmo.setDestinationJNDIName( DestinationJNDIName )
		cmo.setInitialContextFactory("weblogic.jndi.WLInitialContextFactory")
		cmo.setAdapterJNDIName("eis.jms.WLSConnectionFactoryJNDIXA")
	else:
		print "JMS Bridge Destination %s already exists. Ignoring its creation " % JMSBridgeDestination
	
	return bridgeDestination
	

	

def createBridge(MessagingBridge,Cluster,srcbdest,TJMSBridgeDestination,qos):
	print "Creating JMS Bridge #%s#" % MessagingBridge
	cd("/")
	cmo.createMessagingBridge(MessagingBridge)
	bridge = cmo.lookupMessagingBridge(MessagingBridge)
	cluster = cmo.lookupCluster(Cluster)
	targets = bridge.getTargets()
	targets.append(cluster)
	bridge.setTargets(targets)
	bridge.setSourceDestination(srcbdest)
	bridge.setTargetDestination(TJMSBridgeDestination)
	bridge.setStarted(true)
	bridge.setSelector('')
	bridge.setQualityOfService(qos)
	#bridge.setQOSDegradationAllowed(true)
	#bridge.setAsyncEnabled(true)
	#bridge.setDurabilityEnabled(true)
	#bridge.setPreserveMsgProperty(false)
	#bridge.setIdleTimeMaximum('60')



try:

	#check parameters

	if len(sys.argv) != 3 and len(sys.argv) != 4:
		print "Usage: " + sys.argv[0] + " <environment> <JMSBridge group name>"
		raise 
	environmentName = sys.argv[1]
	jmsBridgeGroupName = sys.argv[2]
	passwordOverride = None
	if len(sys.argv) == 4:
		passwordOverride = sys.argv[3]

	#environment checks and configuration load
	workspacePath = System.getenv('WORKSPACE')
	if workspacePath == None:
		print 'WORKSPACE environment varible not set'
		raise 
		
	userHome = os.environ["HOME"]
	envConfigProp = loadProps(userHome + "/environments.properties")
	print "Loaded environments.properties"
	wlsResourcesProp = loadProps(userHome + "/wls_resources.properties")
	print "Loaded wls_resources.properties" 

	targetDomains = wlsResourcesProp.get("JMSBridge." + jmsBridgeGroupName + ".Targets")
	if targetDomains == None:
		print "Targeting metadata not found for JMSBridge group " + jmsBridgeGroupName
		raise 

	#deploy to every target:
	for domain in targetDomains.split(',') :
		deployToDomain(domain)    
					
					
except:
	traceback.print_exc()
	cancelEdit('y')
	disconnect()
