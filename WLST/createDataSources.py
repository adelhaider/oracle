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
    global datasourceGroupName
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
    dsConfigFolderPath = workspacePath + '/Deployment/config/' + environmentName + '/JDBC/'
    dsConfigFileName = datasourceGroupName + '.properties'
    if not os.path.isfile(dsConfigFolderPath + dsConfigFileName):
        dsConfigFileName = datasourceGroupName + '_' + domainName + '.properties'
        if not os.path.isfile(dsConfigFolderPath + dsConfigFileName):
            print "Properties file not found for this environment/domain"
            raise

    print "Connecting to " + adminUrl + " as " + wlsUser
    connect(wlsUser, wlsPassword, adminUrl)
    edit()
    startEdit()
    numChanges = 0

    configProps = loadProps(dsConfigFolderPath + dsConfigFileName)
    if configProps.get("dataSourceNames") is not None:
        dsNames = configProps.get("dataSourceNames").split(",")
        for dsName in dsNames:
            dsMBeanPath = '/JDBCSystemResources/' + dsName + '/JDBCResource/' + dsName
            if getMBean(dsMBeanPath) is None:
                numChanges += 1
                dsJNDIName = configProps.get(dsName + ".JndiName")
                datasourceTarget = configProps.get(dsName + ".Target")
                dsDatabaseName = configProps.get(dsName + ".DatabaseName")
                dsDriverName = configProps.get(dsName + ".DriverClass")
                dsURL = configProps.get(dsName + ".URL")
                dsUserName = configProps.get(dsName + ".Username")
                dsPassword = configProps.get(dsName + ".Password")
                dsTestQuery = configProps.get(dsName + ".TestQuery")
                dsTestConnection = configProps.get(dsName + ".TestConnection")
                dsTestFrequencySeconds = configProps.get(dsName + ".TestFrequencySeconds")
                dsShrinkFrequencySeconds = configProps.get(dsName + ".ShrinkFrequencySeconds")
                dsInactiveConnectionTimeoutSeconds = configProps.get(dsName + ".InactiveConnectionTimeoutSeconds")
                
                
                cd('/')
                cmo.createJDBCSystemResource(dsName)
                cd(dsMBeanPath)
                cmo.setName(dsName)

                cd(dsMBeanPath +  '/JDBCDataSourceParams/' + dsName)
                set('JNDINames', jarray.array([String('jdbc/' + dsName )], String))

                cd(dsMBeanPath +  '/JDBCDriverParams/' + dsName)
                cmo.setUrl(dsURL)
                cmo.setDriverName(dsDriverName)
                cmo.setPassword(dsPassword)
                cd(dsMBeanPath +  '/JDBCConnectionPoolParams/' + dsName)
                cmo.setTestTableName(dsTestQuery)				
                cmo.set('TestConnectionsOnReserve',dsTestConnection)
                cmo.set('TestFrequencySeconds',dsTestFrequencySeconds)
                cmo.set('ShrinkFrequencySeconds',dsShrinkFrequencySeconds)
                cmo.set('InactiveConnectionTimeoutSeconds',dsInactiveConnectionTimeoutSeconds)				
                cd(dsMBeanPath +  '/JDBCDriverParams/' + dsName + '/Properties/' + dsName)
                cmo.createProperty('user')
                cd(dsMBeanPath +  '/JDBCDriverParams/' + dsName + '/Properties/' + dsName + '/Properties/user')
                cmo.setValue(dsUserName)
                cd(dsMBeanPath +  '/JDBCDriverParams/' + dsName + '/Properties/' + dsName)
                cmo.createProperty('databaseName')
                cd(dsMBeanPath +  '/JDBCDriverParams/' + dsName + '/Properties/' + dsName + '/Properties/databaseName')
                cmo.setValue(dsDatabaseName)
                cd(dsMBeanPath +  '/JDBCDataSourceParams/' + dsName)
                if 'XA' in dsDriverName.upper():
                    cmo.setGlobalTransactionsProtocol('TwoPhaseCommit')
                cd('/SystemResources/' + dsName)
                targetType = ''
                targetObjectNames = []
                for targetName in datasourceTarget.split(","):
                    if 'cluster' in targetName or 'Cluster' in targetName:
                        targetType = 'Cluster'
                    else:
                        targetType = 'Server'
                    targetObjectNames.append(ObjectName('com.bea:Name=' + targetName + ',Type=' + targetType))
                set('Targets', jarray.array(targetObjectNames, ObjectName))
                print dsName + " successfully created"
            else:
                print dsName + " already exists. Ignoring"

    if configProps.get("multiDataSourceNames") is not None:
        mdsNames = configProps.get("multiDataSourceNames").split(",")
        for mdsName in mdsNames:
            mdsMBeanPath = '/JDBCSystemResources/' + mdsName + '/JDBCResource/' + mdsName
            if getMBean(mdsMBeanPath) is None:
                numChanges += 1
                mdsJNDIName = configProps.get(mdsName + ".JndiName")
                datasourceNames = configProps.get(mdsName + ".DatasourceNames")
                mdsTargets = configProps.get(mdsName + ".Targets")

                cd('/')
                cmo.createJDBCSystemResource(mdsName)

                cd(mdsMBeanPath)
                cmo.setName(mdsName)

                cd(mdsMBeanPath + '/JDBCDataSourceParams/' + mdsName)
                set('JNDINames', jarray.array([String(mdsJNDIName)], String))
                cmo.setAlgorithmType('Failover')
                cmo.setDataSourceList(datasourceNames)

                cd('/JDBCSystemResources/' + mdsName)
                targetType = ''
                targetObjectNames = []
                for targetName in mdsTargets.split(","):
                    if 'cluster' in targetName or 'Cluster' in targetName:
                        targetType = 'Cluster'
                    else:
                        targetType = 'Server'
                    targetObjectNames.append(ObjectName('com.bea:Name=' + targetName + ',Type=' + targetType))
                set('Targets', jarray.array(targetObjectNames, ObjectName))
                print mdsName + " successfully created"
            else:
                print mdsName + " already exists. Ignoring"

    if configProps.get("gridLinkDataSourceNames") is not None:
        gldsNames = configProps.get("gridLinkDataSourceNames").split(",")
        for gldsName in gldsNames:
            mdsMBeanPath = '/JDBCSystemResources/' + gldsName + '/JDBCResource/' + gldsName
            if getMBean(mdsMBeanPath) is None:
                numChanges += 1
                gldsJNDIName = configProps.get(gldsName + ".JndiName")
                if (gldsJNDIName is None):
                    raise Exception("JNDI name not found for " + gldsName)
                gldsTargets = configProps.get(gldsName + ".Targets")
                if (gldsTargets is None):
                    raise Exception("Target information  not found for " + gldsName)
                gldsJdbcUrl = configProps.get(gldsName + ".JdbcUrl")
                if (gldsJdbcUrl is None):
                    raise Exception("JDBC URL not found for " + gldsName)
                gldsDriverClass = configProps.get(gldsName + ".DriverClass")
                if (gldsDriverClass is None):
                    raise Exception("Driver class not found for " + gldsName)
                gldsUserName = configProps.get(gldsName + ".Username")
                if (gldsUserName is None):
                    raise Exception("User name not found for " + gldsName)
                gldsPassword = configProps.get(gldsName + ".Password")
                if (gldsPassword is None):
                    raise Exception("Password not found for " + gldsName)
                gldsTestQuery = configProps.get(gldsName + ".TestQuery")
                if (gldsTestQuery is None):
                    raise Exception("Test query not found for " + gldsName)	
                gldsTestConnection = configProps.get(gldsName + ".TestConnection")
                if (gldsTestConnection is None):
                    raise Exception("TestConnection property not found for " + gldsName)
                gldsTestFrequencySeconds = configProps.get(gldsName + ".TestFrequencySeconds")
                if (gldsTestFrequencySeconds is None):
                    raise Exception("TestFrequencySeconds property not found for " + gldsName)
                gldsShrinkFrequencySeconds = configProps.get(gldsName + ".ShrinkFrequencySeconds")
                if (gldsShrinkFrequencySeconds is None):
                    raise Exception("ShrinkFrequencySeconds property not found for " + gldsName)
                gldsInactiveConnectionTimeoutSeconds = configProps.get(gldsName + ".InactiveConnectionTimeoutSeconds")
                if (gldsInactiveConnectionTimeoutSeconds is None):
                    raise Exception("InactiveConnectionTimeoutSeconds property not found for " + gldsName)             
                
                cd('/')
                cmo.createJDBCSystemResource(gldsName)
                
                cd('/JDBCSystemResources/' + gldsName + '/JDBCResource/' + gldsName)
                cmo.setName(gldsName)
                
                cd('/JDBCSystemResources/' + gldsName + '/JDBCResource/' + gldsName + '/JDBCDataSourceParams/' + gldsName)
                set('JNDINames',jarray.array([String(gldsJNDIName)], String))
                
                cd('/JDBCSystemResources/' + gldsName + '/JDBCResource/' + gldsName + '/JDBCDriverParams/' + gldsName)
                cmo.setUrl(gldsJdbcUrl)
                cmo.setDriverName(gldsDriverClass)
                cmo.setPassword(gldsPassword)
                
                cd('/JDBCSystemResources/' + gldsName + '/JDBCResource/' + gldsName + '/JDBCConnectionPoolParams/' + gldsName)
                cmo.setTestTableName(gldsTestQuery)
                
                set('TestConnectionsOnReserve',gldsTestConnection)
                set('TestFrequencySeconds',gldsTestFrequencySeconds)
                set('ShrinkFrequencySeconds',gldsShrinkFrequencySeconds)
                set('InactiveConnectionTimeoutSeconds',gldsInactiveConnectionTimeoutSeconds)	
                
                cd('/JDBCSystemResources/' + gldsName + '/JDBCResource/' + gldsName + '/JDBCDriverParams/' + gldsName + '/Properties/' + gldsName + '')
                cmo.createProperty('user')

                cd('/JDBCSystemResources/' + gldsName + '/JDBCResource/' + gldsName + '/JDBCDriverParams/' + gldsName + '/Properties/' + gldsName + '/Properties/user')
                cmo.setValue(gldsUserName)

                cd('/JDBCSystemResources/' + gldsName + '/JDBCResource/' + gldsName + '/JDBCDataSourceParams/' + gldsName)
                if 'XA' in gldsDriverClass.upper():
                    print "Datasource identified as XA"
                    cmo.setGlobalTransactionsProtocol('TwoPhaseCommit')
                else:
                    cmo.setGlobalTransactionsProtocol('None')

                cd('/JDBCSystemResources/' + gldsName + '/JDBCResource/' + gldsName + '/JDBCOracleParams/' + gldsName)
                cmo.setFanEnabled(true)
                cmo.setOnsWalletFile('')
                cmo.setActiveGridlink(true)
                cmo.unSet('OnsWalletPasswordEncrypted')
                cmo.setOnsNodeList('')

                cd('/JDBCSystemResources/' + gldsName)
                targetType = ''
                targetObjectNames = []
                for targetName in gldsTargets.split(","):
                    if 'cluster' in targetName or 'Cluster' in targetName:
                        targetType = 'Cluster'
                    else:
                        targetType = 'Server'
                    targetObjectNames.append(ObjectName('com.bea:Name=' + targetName + ',Type=' + targetType))
                set('Targets', jarray.array(targetObjectNames, ObjectName))
                print gldsName + " successfully created"
            else:
                print gldsName + " already exists. Ignoring"
    if numChanges > 0:
        save()
        activate(block = "true")
        print '==> Datasource creation finished ... Please double check from WLS Console...'
    else:
        cancelEdit('y')

    disconnect()

try:
    #check parameters
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        print "Usage: " + sys.argv[0] + " <environment> <datasource group name>"
        raise
    environmentName = sys.argv[1]
    datasourceGroupName = sys.argv[2]
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

    targetDomains = wlsResourcesProp.get("DataSource." + datasourceGroupName + ".Targets")
    if targetDomains == None:
        print "Targeting metadata not found for Datasource group " + datasourceGroupName
        raise

    #deploy to every target:
    for domain in targetDomains.split(',') :
        deployToDomain(domain)

except:
    traceback.print_exc()
    cancelEdit('y')
    disconnect()
