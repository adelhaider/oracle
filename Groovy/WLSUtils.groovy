
import javax.jms.ConnectionFactory;
import javax.jms.JMSException;
import javax.jms.Message;
import javax.jms.Queue;
import javax.jms.QueueConnectionFactory;
import javax.jms.Session;
import javax.management.MBeanServerConnection;
import javax.management.MalformedObjectNameException;
import javax.management.ObjectName;
import javax.management.openmbean.CompositeData;
import javax.management.remote.JMXConnector;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;
import javax.naming.Binding;
import javax.naming.Context;
import javax.naming.InitialContext;
import javax.naming.NamingEnumeration;
import javax.naming.NamingException;
import javax.naming.event.EventContext;
import weblogic.management.mbeanservers.domainruntime.DomainRuntimeServiceMBean;

def init(url, username, passwd, log) {
	this.log = log
	this.jmxCon = null

    log.info "Creating JMX connection to ${url}"
    try {
        //def fullServerURL = "service:jmx:iiop://" + url + "/jndi/weblogic.management.mbeanservers.runtime";
        def fullServerURL = "service:jmx:iiop://" + url + "/jndi/" + DomainRuntimeServiceMBean.MBEANSERVER_JNDI_NAME
        def serviceUrl = new JMXServiceURL(fullServerURL);

        def env = new Hashtable<String, String>();
        env.put(JMXConnectorFactory.PROTOCOL_PROVIDER_PACKAGES, "weblogic.management.remote");
        env.put(Context.INITIAL_CONTEXT_FACTORY, "weblogic.jndi.WLInitialContextFactory");
        env.put(Context.SECURITY_PRINCIPAL, username);
        env.put(Context.SECURITY_CREDENTIALS, passwd);

        this.jmxCon = JMXConnectorFactory.newJMXConnector(serviceUrl, env);
        this.jmxCon.connect();
    } catch (all) {
        log.info "Unable to connect to ${url} for JMX management due to ${all.getMessage()}"
    }
	if (this.jmxCon == null) {
		throw new RuntimeException("Unable to create connection")
	}
}
	
def switchDatasourceEnablementIfRequired(datasourceName, shouldBeEnabled) {
	def isDsEnabled = isDatasourceEnabled(datasourceName)
	log.info "Datasource ${datasourceName} is ${isDsEnabled?'enabled':'disabled'}"
	if (shouldBeEnabled != isDsEnabled) {
		setDatasourceEnabled(datasourceName, shouldBeEnabled)
		log.info "Datasource ${datasourceName} successfully ${shouldBeEnabled?'enabled':'disabled'}"
	}
	//previous status is returned so the invoker can know whether the service should be switched back or not
	return isDsEnabled
}
	
//returns true if the DS is enabled in at least one managed server
def isDatasourceEnabled(dsName) {
	boolean enabled = false;
    try {
        con = this.jmxCon.getMBeanServerConnection()
		//JDBC*DataSourceRuntime matches both JDBCDataSourceRuntime (standard data source) and JDBCOracleDataSourceRuntime (GridLink data source)
		def objNameList = con.queryNames(new ObjectName("com.bea:Type=JDBC*DataSourceRuntime,Name=" + dsName + ",*"), null)
		if (objNameList.isEmpty()) {
			throw new IllegalArgumentException("Datasource not found")
		}
        for (ObjectName objName : objNameList) {
            enabled = enabled || ((Boolean) con.getAttribute(objName, "Enabled"))
        }
    } catch (Exception e) {
        log.info 'Error while retrieving the list of remote endpoints -> ' + e
    }
	return enabled;
}

def setDatasourceEnabled(dsName, shouldBeEnabled) {
	def action = shouldBeEnabled? "resume" : "suspend";
    try {
        con = this.jmxCon.getMBeanServerConnection()
		def objNameList = con.queryNames(new ObjectName("com.bea:Type=JDBC*DataSourceRuntime,Name=" + dsName + ",*"), null)
		if (objNameList.isEmpty()) {
			throw new IllegalArgumentException("Datasource not found")
		}
        for (ObjectName objName : objNameList) {
            con.invoke(objName, action, null, null);							
            log.info "Executed action " + action + " for " + objName
        }
    } catch (Exception e) {
        log.info 'Error while retrieving the list of remote endpoints: ' + e.getMessage()
    }
}