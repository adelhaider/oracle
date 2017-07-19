from java.io import FileInputStream
from java.util import Date
from java.text import SimpleDateFormat
import sys
import os

def buildXPath(cfInterface, jndiName, propertyName, nameOrValue):
    return '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="' + cfInterface + '"]/connection-instance/[jndi-name="'+ jndiName + '"]/connection-properties/properties/property/[name="' + propertyName + '"]/' + nameOrValue

def loadProps(configPropFile):
    propInputStream = FileInputStream(configPropFile)
    configProps = Properties()
    configProps.load(propInputStream)
    return configProps

def makeDeploymentPlanVariable(wlstPlan, moduleOverrideName, moduleDescriptorName, name, value, xpath, origin = 'planbased'):
    while wlstPlan.getVariableAssignment(name, moduleOverrideName, moduleDescriptorName):
        wlstPlan.destroyVariableAssignment(name, moduleOverrideName, moduleDescriptorName)
    while wlstPlan.getVariable(name):
        wlstPlan.destroyVariable(name)
    variableAssignment = wlstPlan.createVariableAssignment(name, moduleOverrideName, moduleDescriptorName)
    variableAssignment.setXpath(xpath)
    variableAssignment.setOrigin(origin)
    wlstPlan.createVariable(name, value)

def deployToDomain(domainName):
    global envConfigProp
    global environmentName
    global jcaAdapterType
    global jcaAdapterName
    global workspacePath
    global mwHome
    global passwordOverride

    print "Deploying to domain " + domainName + " in environment " + environmentName

    targetName = environmentName + "." + domainName
    domainHome = '/DB09/' + envConfigProp.get("env." + targetName + ".domain_name")
    adminHost = envConfigProp.get("env." + targetName + ".admin_host")
    adminPort = envConfigProp.get("env." + targetName + ".admin_port")
    adminUrl = "t3://" + adminHost + ":" + adminPort
    wlsUser = envConfigProp.get("env." + targetName + ".username")
    wlsPassword = envConfigProp.get("env." + targetName + ".password")
    if passwordOverride != None:
        wlsPassword = passwordOverride

    #find file for the environment
    jcaConfigFolderPath = workspacePath + '/Deployment/config/' + environmentName + '/JCA/'
    jcaConfigFileName = jcaAdapterName + '.properties'
    if not os.path.isfile(jcaConfigFolderPath + jcaConfigFileName):
        jcaConfigFileName = jcaAdapterName + '_' + domainName + '.properties'
        if not os.path.isfile(jcaConfigFolderPath + jcaConfigFileName):
            print "Properties file not found for this environment/domain"
            raise
    configProp = loadProps(jcaConfigFolderPath + jcaConfigFileName)
    print "Loaded adapter configuration from %s" % (jcaConfigFolderPath + jcaConfigFileName)

    print "Connecting to " + adminUrl + " as " + wlsUser
    connect(wlsUser, wlsPassword, adminUrl)
    edit()
    startEdit()

    planPath = '/tmp/' + jcaAdapterType + 'Plan.xml'
    cd(('/AppDeployments/%s' % (jcaAdapterType)))
    if cmo.getAbsolutePlanPath() is None:
        print ('%s does not have a deployment plan yet. Generating an new one' % (jcaAdapterType))
        #os.system('rm %s' % (planPath))
        #if os.path.isfile(filename):
            #os.remove(filename)
    else:
        print "Copying existing deployment plan from remote server"
        remotePlanPath = cmo.getAbsolutePlanPath()
        print ('scp jendepl@%s:%s %s' % (adminHost, remotePlanPath, planPath))
        scpResult = os.system('scp jendepl@%s:%s %s' % (adminHost, remotePlanPath, planPath))
        if scpResult != 0:
            print ('Failed to copy remote deployment plan over')
            raise

    appPath = mwHome + '/soa/soa/connectors/' + jcaAdapterType + '.rar'
    moduleOverrideName = jcaAdapterType + '.rar'
    moduleDescriptorName = 'META-INF/weblogic-ra.xml'
    print 'Using plan ' + planPath
    myPlan = loadApplication(appPath, planPath)

    connectionPoolNames = configProp.get("connectionPoolNames").split(",")
    for connectionPoolName in connectionPoolNames:
        adapterConnectionPoolJndiName = configProp.get(connectionPoolName + ".jndiName")

        randomNumber0 = connectionPoolName + str(System.currentTimeMillis())
        randomNumber1 = randomNumber0 + '1'
        randomNumber2 = randomNumber0 + '2'
        randomNumber3 = randomNumber0 + '3'
        randomNumber4 = randomNumber0 + '4'
        randomNumber5 = randomNumber0 + '5'
        randomNumber6 = randomNumber0 + '6'

        print 'BEGIN change plan'
        if (jcaAdapterType == 'DbAdapter'):
            dsJndiName = configProp.get(connectionPoolName + ".dataSourceJndiName")
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConnectionInstance_'+ adapterConnectionPoolJndiName + '_JNDIName_' + randomNumber0, adapterConnectionPoolJndiName, '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="javax.resource.cci.ConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/jndi-name')
            if 'XA' in dsJndiName:
                makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_XADataSourceName_Name_' + randomNumber1, 'XADataSourceName', '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="javax.resource.cci.ConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/connection-properties/properties/property/[name="XADataSourceName"]/name')
                makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_XADataSourceName_Value_'+ randomNumber2, dsJndiName        , '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="javax.resource.cci.ConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/connection-properties/properties/property/[name="XADataSourceName"]/value')
            else:
                makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_DataSourceName_Name_' + randomNumber1, 'DataSourceName', '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="javax.resource.cci.ConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/connection-properties/properties/property/[name="DataSourceName"]/name')
                makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_DataSourceName_Value_'+ randomNumber2, dsJndiName      , '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="javax.resource.cci.ConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/connection-properties/properties/property/[name="DataSourceName"]/value')
        elif (jcaAdapterType == 'JmsAdapter'):
            jmsConnFactoryJndiName = configProp.get(connectionPoolName + ".jmsConnFactoryJndiName")
            isTransacted = configProp.get(connectionPoolName + ".isTransacted")
            factoryProperties = configProp.get(connectionPoolName + ".factoryProperties")
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConnectionInstance_'+ adapterConnectionPoolJndiName + '_JNDIName_' + randomNumber0, adapterConnectionPoolJndiName, '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="oracle.tip.adapter.jms.IJmsConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/jndi-name')
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_ConnectionFactoryLocation_Name_' + randomNumber1                   , 'ConnectionFactoryLocation'  , '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="oracle.tip.adapter.jms.IJmsConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/connection-properties/properties/property/[name="ConnectionFactoryLocation"]/name')
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_ConnectionFactoryLocation_Value_' + randomNumber2                  , jmsConnFactoryJndiName       , '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="oracle.tip.adapter.jms.IJmsConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/connection-properties/properties/property/[name="ConnectionFactoryLocation"]/value')
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_IsTransacted_Name_' + randomNumber3                                , 'IsTransacted'               , '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="oracle.tip.adapter.jms.IJmsConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/connection-properties/properties/property/[name="IsTransacted"]/name')
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_IsTransacted_Value_' + randomNumber4                               , isTransacted                 , '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="oracle.tip.adapter.jms.IJmsConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/connection-properties/properties/property/[name="IsTransacted"]/value')
            if factoryProperties is not None:
                makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_FactoryProperties_Name_' + randomNumber5 , 'FactoryProperties', '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="oracle.tip.adapter.jms.IJmsConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/connection-properties/properties/property/[name="FactoryProperties"]/name')
                makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_FactoryProperties_Value_' + randomNumber6, factoryProperties  , '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="oracle.tip.adapter.jms.IJmsConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/connection-properties/properties/property/[name="FactoryProperties"]/value')
        elif (jcaAdapterType == 'CoherenceAdapter'):
            configFileLocation = configProp.get(connectionPoolName + ".configFileLocation")
            serviceName = configProp.get(connectionPoolName + ".serviceName")
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConnectionInstance_'+ adapterConnectionPoolJndiName + '_JNDIName_' + randomNumber0, adapterConnectionPoolJndiName, '/weblogic-connector/outbound-resource-adapter/connection-definition-group/[connection-factory-interface="javax.resource.cci.ConnectionFactory"]/connection-instance/[jndi-name="'+ adapterConnectionPoolJndiName + '"]/jndi-name')
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_CacheConfigLocation_Name_' + randomNumber1                         , 'CacheConfigLocation'        , buildXPath('javax.resource.cci.ConnectionFactory', adapterConnectionPoolJndiName, 'CacheConfigLocation', 'name'))
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_CacheConfigLocation_Value_' + randomNumber2                        , configFileLocation           , buildXPath('javax.resource.cci.ConnectionFactory', adapterConnectionPoolJndiName, 'CacheConfigLocation', 'value'))
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_ServiceName_Name_' + randomNumber3                                 , 'ServiceName'                , buildXPath('javax.resource.cci.ConnectionFactory', adapterConnectionPoolJndiName, 'ServiceName', 'name'))
            makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_ServiceName_Value_' + randomNumber4                                , serviceName                  , buildXPath('javax.resource.cci.ConnectionFactory', adapterConnectionPoolJndiName, 'ServiceName', 'value'))
        elif (jcaAdapterType == 'AqAdapter'):
            dsJndiName = configProp.get(connectionPoolName + ".dataSourceJndiName")
            if 'XA' in dsJndiName:
                makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_XADataSourceName_Name_' + randomNumber1, 'XADataSourceName', buildXPath('javax.resource.cci.ConnectionFactory', adapterConnectionPoolJndiName, 'XADataSourceName', 'name'))
                makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_XADataSourceName_Value_'+ randomNumber2, dsJndiName        , buildXPath('javax.resource.cci.ConnectionFactory', adapterConnectionPoolJndiName, 'XADataSourceName', 'value'))
            else:
                makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_DataSourceName_Name_' + randomNumber1, 'DataSourceName', buildXPath('javax.resource.cci.ConnectionFactory', adapterConnectionPoolJndiName, 'DataSourceName', 'name'))
                makeDeploymentPlanVariable(myPlan, moduleOverrideName, moduleDescriptorName, 'ConfigProperty_DataSourceName_Value_'+ randomNumber2, dsJndiName      , buildXPath('javax.resource.cci.ConnectionFactory', adapterConnectionPoolJndiName, 'DataSourceName', 'value'))
        print 'EIS Connection factory ' + adapterConnectionPoolJndiName + ' configured';
    print 'DONE changing plan'
    myPlan.save();

    save()
    activate(block = 'true');
    cd('/AppDeployments/' + jcaAdapterType + '/Targets');
    redeploy(jcaAdapterType, planPath, upload = 'true');
    print 'All JCA connection pools created';

    disconnect()

try:
    #check parameters
    if len(sys.argv) != 4 and len(sys.argv) != 5:
        print "Usage: " + sys.argv[0] + " <environment> <JCA adapter name>"
        raise
    environmentName = sys.argv[1]
    jcaAdapterType = sys.argv[2]
    jcaAdapterName = sys.argv[3]
    passwordOverride = None
    if len(sys.argv) == 5:
        passwordOverride = sys.argv[4]

    #environment checks and configuration load
    workspacePath = System.getenv('WORKSPACE')
    if workspacePath == None:
        print 'WORKSPACE environment varible not set'
        raise
    mwHome = System.getenv('MW_HOME')
    if mwHome == None:
        print 'MW_HOME environment varible not set'
        raise
    print 'Middleware home folder: ' + mwHome

    print 'Detecting OS ...'
    myOS = os.getenv('os')
    if myOS is None:
        print 'OS could not be detected'
    else:
        print 'Detected OS is ' + myOS
    if myOS == 'Windows_NT':
        userHome = os.environ["USERPROFILE"]
    else:
        userHome = os.environ["HOME"]
    if userHome is None:
        print 'Failed to locate user home folder'
        raise
    print 'User home folder: ' + userHome
    envConfigProp = loadProps(userHome + "/environments.properties")
    print "Loaded environments.properties"
    wlsResourcesProp = loadProps(userHome + "/wls_resources.properties")
    print "Loaded wls_resources.properties"

    targetDomains = wlsResourcesProp.get(jcaAdapterType + "." + jcaAdapterName + ".Targets")
    if targetDomains == None:
        print "Targeting metadata not found for JCA adapter: " + jcaAdapterName
        raise

    #deploy to every target:
    for domain in targetDomains.split(',') :
        deployToDomain(domain)

    print '==> JCA adapter configuration creation finished ... Please double check from WLS Console...'

except:
    traceback.print_exc()
    cancelEdit('y')
    disconnect()
