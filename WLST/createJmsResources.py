#================================
from java.io import FileInputStream
import sys
 
#================================
# Generic definitions
#================================
 
def loadProps(configPropFile):
    propInputStream = FileInputStream(configPropFile)
    configProps = Properties()
    configProps.load(propInputStream)
    return configProps

def getJmsDestinationMBeanPath(jmsModuleName, destinationName, destinationType):
    return '/JMSSystemResources/' + jmsModuleName + '/JMSResource/' + jmsModuleName + '/' + destinationType + 's/' + destinationName

def doesQueueExist(jmsModuleName, queueName):
    return getMBean(getJmsDestinationMBeanPath(jmsModuleName, queueName, 'Queue')) is not None or getMBean(getJmsDestinationMBeanPath(jmsModuleName, queueName, 'UniformDistributedQueue')) is not None

def doesTopicExist(jmsModuleName, topicName):
    return getMBean(getJmsDestinationMBeanPath(jmsModuleName, topicName, 'Topic')) is not None or getMBean(getJmsDestinationMBeanPath(jmsModuleName, topicName, 'UniformDistributedTopic')) is not None

def deployToDomain(domainName):
    global envConfigProp
    global environmentName
    global jmsResourceGroupName
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
    jmsConfigFolderPath = workspacePath + '/Deployment/config/' + environmentName + '/JMS/'
    jmsConfigFileName = jmsResourceGroupName + '.properties'
    if not os.path.isfile(jmsConfigFolderPath + jmsConfigFileName):
        jmsConfigFileName = jmsResourceGroupName + '_' + domainName + '.properties'
        if not os.path.isfile(jmsConfigFolderPath + jmsConfigFileName):
            print "Properties file not found for this environment/domain"
            raise

    print "Connecting to " + adminUrl + " as " + wlsUser
    connect(wlsUser, wlsPassword, adminUrl)
    edit()
    startEdit()

    configProps = loadProps(jmsConfigFolderPath + jmsConfigFileName)
    
    #==============================
    # Build JMS persistence stores
    #==============================
    persistenceStoresCreated = false
    for persistenceStoreName in configProps.get("persistenceStoreNames").split(","):
        persistenceStorePath = configProps.get(persistenceStoreName + ".StorePath")
        persistenceStoreTarget = configProps.get(persistenceStoreName + ".Target")
        persistenceStoreMBean = getMBean('/FileStores/' + persistenceStoreName)
        if persistenceStoreMBean is None:
            print "Creating persistence store %s, targeted to %s" % (persistenceStoreName, persistenceStoreTarget)
            cd('/')
            cmo.createFileStore(persistenceStoreName)
            cd('/FileStores/' + persistenceStoreName)
            cmo.setDirectory(persistenceStorePath)
            set('Targets', jarray.array([ObjectName('com.bea:Name=' + persistenceStoreTarget + ',Type=Server')], ObjectName))
            persistenceStoresCreated = true
        else:
            print "Skipping creation of store (already exists)"
    print "Done creating persistence stores"

    if persistenceStoresCreated == true:
        print "Activating current session and creating a new one for the rest of the resources"
        save()
        activate()
        startEdit()

    #keep count of the number of changes implemented (if no changes are made (i.e. all the resources do already exist) then do not activate the session but cancel it instead)
    numChanges = 0

    #================================
    # Build JMS Server(s)
    # For every MS in cluster define a JMSserver and target a single MS server
    #================================
    print "Start creating JMS servers"
    for jmsServerName in configProps.get("jmsServerNames").split(","):
        if getMBean('/Deployments/' + jmsServerName) is None:
            numChanges += 1
            print "Creating JMS server %s" % jmsServerName
            serverPersStoreName = configProps.get(jmsServerName + ".PersistenceStore")
            serverTarget = configProps.get(jmsServerName + ".Target")
            cd('/')
            cmo.createJMSServer(jmsServerName)
            cd('/Deployments/' + jmsServerName)
            cmo.setPersistentStore(getMBean('/FileStores/' + serverPersStoreName))
            set('Targets', jarray.array([ObjectName('com.bea:Name=' + serverTarget + ',Type=Server')], ObjectName))
        else:
            print "JMS server " + jmsServerName + " already exists. Ignoring its creation"
    print "Done creating JMS servers"
     
    #================================
    # Build JMS Module
    # target preferrable cluster, single-server DEV domain use server
    #================================
    print "Start creating JMS modules"
    for jmsModuleName in configProps.get("jmsModuleNames").split(","):
        if getMBean('/SystemResources/' + jmsModuleName) is None:
            print "Creating JMS module %s" % jmsModuleName
            numChanges += 1
            jmsModuleTarget = configProps.get(jmsModuleName + ".Target")
            cd('/')
            cmo.createJMSSystemResource(jmsModuleName)
            cd('/SystemResources/' + jmsModuleName)
            if 'cluster' in jmsModuleTarget or 'Cluster' in jmsModuleTarget:
                targetName = 'com.bea:Name=' + jmsModuleTarget + ',Type=Cluster'
            else:
                targetName = 'com.bea:Name=' + jmsModuleTarget + ',Type=Server'
            print "Targeting JMS module to %s" % targetName
            set('Targets',jarray.array([ObjectName(targetName)], ObjectName))
        else:
            print "JMS module %s already exists. Ignoring its creation " % jmsModuleName
    print "Done creating JMS modules"
        
    print "Start creating JMS module subdeployments"
    for jmsModuleName in configProps.get("jmsModuleNames").split(","):
        print "Creating subdeployments for module %s" % jmsModuleName
        for jmsSubdeploymentName in configProps.get(jmsModuleName + ".Subdeployments").split(","):
            if getMBean('/SystemResources/' + jmsModuleName + '/SubDeployments/' + jmsSubdeploymentName) is None:
                numChanges += 1
                print "Creating subdeployment %s" % jmsSubdeploymentName
                cd('/SystemResources/' + jmsModuleName)
                subDeployment = cmo.createSubDeployment(jmsSubdeploymentName)
                cd('/SystemResources/' + jmsModuleName + '/SubDeployments/' + jmsSubdeploymentName)
                subdeploymentTargets = jarray.array([], ObjectName)
                for subdeploymentTarget in configProps.get(jmsModuleName + "." + jmsSubdeploymentName + ".Targets").split(","):
                    print "Adding target %s to current subdeployment" % subdeploymentTarget
                    if 'cluster' in subdeploymentTarget or 'Cluster' in subdeploymentTarget:
                        subDeployment.addTarget(getMBean('/Clusters/' + subdeploymentTarget))
                    elif 'JmsServer' in subdeploymentTarget or 'JMSServer' in subdeploymentTarget:
                        subDeployment.addTarget(getMBean('/Deployments/' + subdeploymentTarget))
                    elif 'Server' in subdeploymentTarget or 'server' in subdeploymentTarget:
                        subDeployment.addTarget(getMBean('/Servers/' + subdeploymentTarget))
                    else:
                        raise
            else:
                print "JMS module subdeployment %s already exists. Ignoring its creation " % jmsSubdeploymentName
        print "Done creating subdeployments for %s" % jmsModuleName
    print "Done creating JMS module subdeployments for all modules"

    print "Start creating JMS connection factories"
    for jmsModuleName in configProps.get("jmsModuleNames").split(","):
        print "Creating connection factories for module %s" % jmsModuleName
        for connFactoryName in configProps.get(jmsModuleName + ".ConnectionFactoryNames").split(","):
            connFactoryMbeanPath = '/JMSSystemResources/' + jmsModuleName + '/JMSResource/' + jmsModuleName + '/ConnectionFactories/' + connFactoryName
            if getMBean(connFactoryMbeanPath) is None:
                print "Creating connection factory %s" % connFactoryName
                numChanges += 1
                cfJndiName = configProps.get(connFactoryName + ".JNDIName")
                cfSubdeploymentName = configProps.get(connFactoryName + ".SubDeploymentName")
                cfMaxMsgPerSession = configProps.get(connFactoryName + ".MessagesMaximum")
                isXAConnFactory = configProps.get(connFactoryName + ".EnableXA").lower() == 'true'
                cd('/JMSSystemResources/' + jmsModuleName + '/JMSResource/' + jmsModuleName)
                cmo.createConnectionFactory(connFactoryName)
                cd(connFactoryMbeanPath)
                cmo.setJNDIName(cfJndiName)
                cmo.setSubDeploymentName(cfSubdeploymentName)
                cd(connFactoryMbeanPath + '/SecurityParams/' + connFactoryName)
                cmo.setAttachJMSXUserId(false)
                cd(connFactoryMbeanPath + '/ClientParams/' + connFactoryName)
                cmo.setClientIdPolicy('Restricted')
                cmo.setSubscriptionSharingPolicy('Exclusive')
                if not(cfMaxMsgPerSession is None):
                    cmo.setMessagesMaximum(int(cfMaxMsgPerSession))
                cd(connFactoryMbeanPath + '/TransactionParams/' + connFactoryName)
                cmo.setXAConnectionFactoryEnabled(isXAConnFactory)
            else:
                print "JMS connection factory %s already exists. Ignoring its creation " % connFactoryName
        print "Done creating connection factories for %s" % jmsModuleName
    print "Done creating JMS connection factories for all modules"

    print "Start creating JMS queues"
    for jmsModuleName in configProps.get("jmsModuleNames").split(","):
        print "Creating queues for module %s" % jmsModuleName
        queueNames = configProps.get(jmsModuleName + ".QueueNames")
        if queueNames is not None and queueNames != '':
            for queueName in queueNames.split(","):
                if not doesQueueExist(jmsModuleName, queueName):
                    numChanges += 1
                    queueType = configProps.get(queueName + ".Type")
                    print "Creating Queue %s of type %s" % (queueName, queueType)
                    #load new queue's configuration
                    queueJndiName = configProps.get(queueName + ".JNDIName")
                    queueSubdeploymentName = configProps.get(queueName + ".SubDeploymentName")
                    queueRedeliveryLimit = configProps.get(queueName + ".RedeliveryLimit")
                    queueExpirationPolicy = configProps.get(queueName + ".ExpirationPolicy")
                    queueErrorDestination = configProps.get(queueName + ".ErrorDestination")
                    queueMBeanPath = getJmsDestinationMBeanPath(jmsModuleName, queueName, queueType)

                    print "Queue config loaded"

                    #create the queue
                    cd('/JMSSystemResources/' + jmsModuleName + '/JMSResource/' + jmsModuleName)
                    if queueType == 'Queue':
                        cmo.createQueue(queueName)
                    elif queueType == 'UniformDistributedQueue':
                        cmo.createUniformDistributedQueue(queueName);
                    else:
                        raise

                    print "Queue created"

                    #configure the queue
                    cd(queueMBeanPath)
                    if queueType == 'UniformDistributedQueue':
                        cmo.setLoadBalancingPolicy('Round-Robin')
                        cmo.setUnitOfOrderRouting('PathService');
                    cmo.setJNDIName(queueJndiName)
                    cmo.setSubDeploymentName(queueSubdeploymentName)
                    cd(queueMBeanPath + '/DeliveryFailureParams/' + queueName)
                    if queueRedeliveryLimit is not None:
                        cmo.setRedeliveryLimit(int(queueRedeliveryLimit))
                    if queueExpirationPolicy is not None:
                        cmo.setExpirationPolicy(queueExpirationPolicy)
                    if queueErrorDestination is not None:
                        cmo.setErrorDestination(getMBean(getJmsDestinationMBeanPath(jmsModuleName, queueErrorDestination, queueType)))
                    print "Queue configured"
                else:
                    print "Queue %s already exists. Ignoring its creation" % queueName
            print "Done creating queues for %s" % jmsModuleName
    print "Done creating queues for all modules"

    print "Start creating JMS topics"
    for jmsModuleName in configProps.get("jmsModuleNames").split(","):
        print "Creating topics for module %s" % jmsModuleName
        topicNames = configProps.get(jmsModuleName + ".TopicNames")
        if topicNames is not None and topicNames != '':
            for topicName in topicNames.split(","):
                if not doesTopicExist(jmsModuleName, topicName):
                    numChanges += 1
                    print "Creating Topic %s" % topicName
                    #load new topic's configuration
                    topicJndiName = configProps.get(topicName + ".JNDIName")
                    topicSubdeploymentName = configProps.get(topicName + ".SubDeploymentName")
                    topicType = configProps.get(topicName + ".Type")
                    topicRedeliveryLimit = configProps.get(topicName + ".RedeliveryLimit")
                    topicExpirationPolicy = configProps.get(topicName + ".ExpirationPolicy")
                    topicErrorDestination = configProps.get(topicName + ".ErrorDestination")

                    #create the topic
                    cd('/JMSSystemResources/' + jmsModuleName + '/JMSResource/' + jmsModuleName)
                    if topicType == 'Topic':
                        cmo.createTopic(topicName)
                    elif topicType == 'UniformDistributedTopic':
                        cmo.createUniformDistributedTopic(topicName);
                    else:
                        raise

                    #configure the new topic
                    cd(getJmsDestinationMBeanPath(jmsModuleName, topicName, topicType))
                    set('JNDIName', topicJndiName)
                    set('SubDeploymentName', topicSubdeploymentName)
                    #cd('/JMSSystemResources/' + jmsModuleName + '/JMSResource/' + jmsModuleName + '/' + topicType + 's/' + topicName + '/DeliveryFailureParams/' + topicName)
                    #cmo.setRedeliveryLimit(2)
                    #cmo.setExpirationPolicy('Redirect')
                    #cmo.setErrorDestination(getMBean('/JMSSystemResources/ScanHubJMSSystemModule/JMSResource/ScanHubJMSSystemModule/UniformDistributedQueues/ScanHub.PerformFailureQueue'))
                    
                    #cd('/JMSSystemResources/' + jmsModuleName + '/JMSResource/' + jmsModuleName + '/' + topicType + 's/' + topicName + '/DeliveryParamsOverrides/' + topicName)
                    #cmo.setDeliveryMode('Persistent')
                else:
                    print "Topic %s already exists. Ignoring its creation" % topicName
            print "Done creating topics for %s" % jmsModuleName
    print "Done creating topics for all modules"
     
    #==========================================================================
    # Finalize
    #==========================================================================
     
    if numChanges > 0:
        save()
        activate()
        print '==> JMS resource creation finished ... Please double check from WLS Console...'
    else:
        cancelEdit('y')

    disconnect()

try:
    #check parameters
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        print "Usage: " + sys.argv[0] + " <environment> <JMS module name>"
        raise
    environmentName = sys.argv[1]
    jmsResourceGroupName = sys.argv[2]
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

    targetDomains = wlsResourcesProp.get("JMS." + jmsResourceGroupName + ".Targets")
    if targetDomains == None:
        print "Targeting metadata not found for JMS module: " + jmsResourceGroupName
        raise

    #deploy to every target:
    for domain in targetDomains.split(',') :
        deployToDomain(domain)

except:
    traceback.print_exc()
    cancelEdit('y')
    disconnect()
