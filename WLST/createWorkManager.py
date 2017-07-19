from java.io import FileInputStream
import sys
  
def loadProps(configPropFile):
    propInputStream = FileInputStream(configPropFile)
    configProps = Properties()
    configProps.load(propInputStream)
    return configProps

def deployToDomain(domainName):
    global envConfigProp
    global environmentName
    global workManagerName
    global workspacePath
    global passwordOverride
    print "Deploying to domain " + domainName + " in environment " + environmentName
    targetName = environmentName + "." + domainName
    admin_host = envConfigProp.get("env." + targetName + ".admin_host")
    admin_port = envConfigProp.get("env." + targetName + ".admin_port")
    adminUrl = "t3://" + admin_host + ":" + admin_port
    wlsUser = envConfigProp.get("env." + targetName + ".username")
    wlsPassword = envConfigProp.get("env." + targetName + ".password")
    wlsDomainName = envConfigProp.get("env." + targetName + ".domain_name")
    if passwordOverride != None:
        wlsPassword = passwordOverride
    #find file for the environment
    workManagerConfigFolderPath = workspacePath + '/Deployment/config/' + environmentName + '/WorkManagers/'
    workManagerConfigFileName = workManagerName + '.properties'
    if not os.path.isfile(workManagerConfigFolderPath + workManagerConfigFileName):
        workManagerConfigFileName = workManagerName + '_' + domainName + '.properties'
        if not os.path.isfile(workManagerConfigFolderPath + workManagerConfigFileName):
            print "Properties file not found for this environment/domain"
            raise
    configProp = loadProps(workManagerConfigFolderPath + workManagerConfigFileName)
    actualWorkManagerName = configProp.get("workManagerName")
    maxThreadConstraintName = configProp.get("maxThreadConstraintName")
    minThreadConstraintName = configProp.get("minThreadConstraintName")
    targetName = configProp.get("targetName")
    print "Loaded adapter configuration from %s" % (workManagerConfigFolderPath + workManagerConfigFileName)
    print "Connecting to " + adminUrl + " as " + wlsUser
    connect(wlsUser, wlsPassword, adminUrl)
    print '======= Processing workManager %s in %s =======' % (actualWorkManagerName, wlsDomainName)
    if getMBean('/SelfTuning/' + wlsDomainName + '/WorkManagers/' + actualWorkManagerName) is None:
        print '==> Work manager %s not found. Proceeding with its creation' % actualWorkManagerName
        edit()
        startEdit()
        cd('/SelfTuning/' + wlsDomainName + '/WorkManagers/')
        create(actualWorkManagerName, 'WorkManagers')
        cd('/SelfTuning/' + wlsDomainName + '/WorkManagers/' + actualWorkManagerName)
        if 'cluster' in targetName or 'Cluster' in targetName:
            cmo.addTarget(getMBean("/Clusters/" + targetName))
        else:
            cmo.addTarget(getMBean("/Servers/" + targetName))
        save()
        print ' WorkManager Created...'

        if maxThreadConstraintName is not None:
            maxThread = configProp.get(maxThreadConstraintName + ".maxThread")
            print '======= Creating MaxThreadsConstraint ======='
            cd('/SelfTuning/' + wlsDomainName + '/MaxThreadsConstraints/')
            try:
                create(maxThreadConstraintName, 'MaxThreadsConstraints')
            except Exception:
                print 'Issue in Creating MaxThreads exiting'
            cd('/SelfTuning/' + wlsDomainName + '/MaxThreadsConstraints/' + maxThreadConstraintName)
            if 'cluster' in targetName or 'Cluster' in targetName:
                cmo.addTarget(getMBean("/Clusters/" + targetName))
            else:
                cmo.addTarget(getMBean("/Servers/" + targetName))
            set('Count', maxThread)
            save()
            print '======= Assigning the MaxThreadConstraint to the WorkManager ======='
            cd('/SelfTuning/' + wlsDomainName + '/WorkManagers/' + actualWorkManagerName)
            bean = getMBean('/SelfTuning/' + wlsDomainName + '/MaxThreadsConstraints/' + maxThreadConstraintName)
            cmo.setMaxThreadsConstraint(bean)
            save()

        if minThreadConstraintName is not None:
            minThread = configProp.get(minThreadConstraintName + ".minThread")
            print '======= Creating MinThreadsConstraint ======='
            cd('/SelfTuning/' + wlsDomainName + '/MinThreadsConstraints/')
            try:
                create(minThreadConstraintName, 'MinThreadsConstraints')
            except Exception:
                print 'Issue In Creating MinThreads '
            cd('/SelfTuning/' + wlsDomainName + '/MinThreadsConstraints/' + minThreadConstraintName)
            if 'cluster' in targetName or 'Cluster' in targetName:
                cmo.addTarget(getMBean("/Clusters/" + targetName))
            else:
                cmo.addTarget(getMBean("/Servers/" + targetName))
            set('Count', minThread)
            save()
            print '======= Assigning the MinThreadConstraint to the WorkManager ======='
            cd('/SelfTuning/' + wlsDomainName + '/WorkManagers/' + actualWorkManagerName)
            bean = getMBean('/SelfTuning/' + wlsDomainName + '/MinThreadsConstraints/' + minThreadConstraintName)
            cmo.setMinThreadsConstraint(bean)
            save()

        save()
        activate(block = "true")
        print '==> WorkManager Creation Finished ... Please Double Check from AdminConsole...'
    else:
        print "Work manager already exists. Ignoring its creation"
    disconnect()

try:
    #check parameters
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        print "Usage: " + sys.argv[0] + " <environment> <Work manager name> [<password override>]"
        raise
    environmentName = sys.argv[1]
    workManagerName = sys.argv[2]
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

    targetDomains = wlsResourcesProp.get("WorkManager." + workManagerName + ".Targets")
    if targetDomains == None:
        print "Targeting metadata not found for JCA adapter: " + workManagerName
        raise

    #deploy to every target:
    for domain in targetDomains.split(',') :
        deployToDomain(domain)

    print '==> Work manager creation finished ... Please double check from WLS Console...'

except:
    dumpStack() 
    traceback.print_exc()
    cancelEdit('y')
    disconnect()