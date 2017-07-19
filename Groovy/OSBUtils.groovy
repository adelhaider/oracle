import javax.management.MBeanServerConnection;
import javax.management.ObjectName;
import javax.management.remote.JMXConnector;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;

import javax.naming.Context;

import com.bea.wli.config.Ref;
import com.bea.wli.sb.util.Refs;
import com.bea.wli.sb.util.EnvValueTypes
import com.bea.wli.sb.management.configuration.ALSBConfigurationMBean;
import com.bea.wli.sb.management.configuration.BusinessServiceConfigurationMBean;
import com.bea.wli.sb.management.configuration.CommonServiceConfigurationMBean;
import com.bea.wli.sb.management.configuration.ProxyServiceConfigurationMBean;
import com.bea.wli.sb.management.configuration.ServiceConfigurationMBean;
import com.bea.wli.sb.management.configuration.SessionManagementMBean;
//import com.bea.wli.sb.management.configuration.operations.LogSeverityLevel;
import com.bea.wli.sb.services.operations.LogSeverityLevel;
//import com.bea.wli.sb.management.configuration.operations.ServiceOperationsEntry;
import com.bea.wli.sb.management.query.BusinessServiceQuery;
import com.bea.wli.sb.management.query.ProxyServiceQuery;
import com.bea.wli.sb.management.query.ServiceQuery;
import com.bea.wli.config.resource.ResourceQuery;
import com.bea.wli.config.customization.Customization
import com.bea.wli.config.customization.ReferenceCustomization
import com.bea.wli.config.customization.EnvValueCustomization
import com.bea.wli.config.env.QualifiedEnvValue

import weblogic.management.jmx.MBeanServerInvocationHandler;
import weblogic.management.mbeanservers.domainruntime.DomainRuntimeServiceMBean;

import java.util.List;

class OSBUtils implements Serializable {

	def initialized = false
	def log = null
	def jmxConnector = null

	def setLog(log) {
		this.log = log
	}

	def initConnection(username, password, adminServerHost, adminServerPort) {
		if (!initialized) {
			try {
				def serviceURL = new JMXServiceURL("t3", adminServerHost, adminServerPort, "/jndi/" + DomainRuntimeServiceMBean.MBEANSERVER_JNDI_NAME);
				def props = new Hashtable();
				props.put(Context.SECURITY_PRINCIPAL, username);
				props.put(Context.SECURITY_CREDENTIALS, password);
				props.put(JMXConnectorFactory.PROTOCOL_PROVIDER_PACKAGES, "weblogic.management.remote");
				this.log.info "Connecting to ${serviceURL.protocol}://${serviceURL.host}:${serviceURL.port}${serviceURL.getURLPath()}"
				this.jmxConnector = JMXConnectorFactory.connect(serviceURL, props);
				this.log.info "Successfully connected"
				initialized = true
			} catch (Exception e) {
				this.log.info "Error connecting"
				throw e;
			}
		}
	}

	def ensureComponentsEnablement(serviceInfoArray) {
		if (this.jmxConnector == null) {
			throw new Exception("JMX Connection not initialized");
		}
		def sessionName = "SoapUI-JMX-" + System.currentTimeMillis()
		def serviceQuery = null
		def commonServiceConfigurationMBean = null
		def isSessionOpen = false
		def mbConnection = this.jmxConnector.getMBeanServerConnection()
		def domainService = MBeanServerInvocationHandler.newProxyInstance(mbConnection, new ObjectName(DomainRuntimeServiceMBean.OBJECT_NAME));
		def sessionManagementMBean = domainService.findService(SessionManagementMBean.NAME, SessionManagementMBean.TYPE, null)
		def alsbConfMB = null;

		this.log.info "Creating new Weblogic change session $sessionName";
		sessionManagementMBean.createSession(sessionName);
		alsbConfMB = (ALSBConfigurationMBean) domainService.findService(ALSBConfigurationMBean.NAME + "." + sessionName, ALSBConfigurationMBean.TYPE, null);

		def psSvcConfigBean = domainService.findService(ProxyServiceConfigurationMBean.NAME + "." + sessionName, ProxyServiceConfigurationMBean.TYPE, null);
		def bsSvcConfigBean = domainService.findService(BusinessServiceConfigurationMBean.NAME + "." + sessionName, BusinessServiceConfigurationMBean.TYPE, null);

		def serviceNames = ''
    def numChanges = 0
		for (serviceInfo in serviceInfoArray) {
			def servicePath = serviceInfo[0]
			def serviceName = serviceInfo[1]
			def isProxy = serviceInfo[2]
			def enable = serviceInfo[3]
			if (isProxy) {
				serviceQuery = new ProxyServiceQuery();
			} else {
				serviceQuery = new BusinessServiceQuery();
			}
			serviceQuery.setPath(servicePath + "*")
			serviceQuery.setLocalName(serviceName)
			def serviceRef = null
			def refs = alsbConfMB.getRefs(serviceQuery)

			if (refs.isEmpty()) {
				throw new RuntimeException("Error updating service (Service " + serviceName + " not found)")
			} else if (refs.size() > 1) {
				throw new RuntimeException("Error updating service (More than one service found matching the name \"${serviceName}\")")
			} else {
				commonServiceConfigurationMBean = isProxy? psSvcConfigBean : bsSvcConfigBean
				serviceRef = refs.iterator().next();
				def isEnabled = commonServiceConfigurationMBean.isEnabled(serviceRef);
				if (isEnabled != enable) {
                    numChanges++
					if (enable) {
						commonServiceConfigurationMBean.enableService(serviceRef);
					} else {
						commonServiceConfigurationMBean.disableService(serviceRef);
					}
				}
				if (!serviceNames.equals('')) {
					serviceNames = serviceNames + ", "
				}
				serviceNames = serviceNames + servicePath + "/" + serviceName + " (" + (enable?"enabled":"disabled") + ")"
			}
		}
        if (numChanges > 0) {
            sessionManagementMBean.activateSession(sessionName, serviceNames);
            this.log.info "Activated changes in the session: $sessionName"
        } else {
            sessionManagementMBean.discardSession(sessionName);
            this.log.info "Discarded session: $sessionName"
        }

		try {
			mbConnection.close()
		} catch (Exception e) {
		}
	}


	def setServiceEnabled(projectName, serviceName, isProxy, enable) {
		if (this.jmxConnector == null) {
			throw new Exception("JMX Connection not initialized");
		}
		def sessionName = "SoapUI-JMX-" + System.currentTimeMillis()
		def serviceQuery = null
		def commonServiceConfigurationMBean = null
		def isSessionOpen = false
		def mbConnection = this.jmxConnector.getMBeanServerConnection()
		def domainService = MBeanServerInvocationHandler.newProxyInstance(mbConnection, new ObjectName(DomainRuntimeServiceMBean.OBJECT_NAME));
		def sessionManagementMBean = domainService.findService(SessionManagementMBean.NAME, SessionManagementMBean.TYPE, null)
		def alsbConfMB = null;

		this.log.info "Creating new Weblogic change session $sessionName";
		sessionManagementMBean.createSession(sessionName);
		alsbConfMB = (ALSBConfigurationMBean) domainService.findService(ALSBConfigurationMBean.NAME + "." + sessionName, ALSBConfigurationMBean.TYPE, null);

		if (isProxy) {
			serviceQuery = new ProxyServiceQuery();
		} else {
			serviceQuery = new BusinessServiceQuery();
		}
		serviceQuery.setPath(projectName + "*")
		serviceQuery.setLocalName(serviceName)
		def proxyServiceRef = null
		def refs = alsbConfMB.getRefs(serviceQuery)

		if (refs.isEmpty()) {
			throw new RuntimeException("Error updating service (Service " + serviceName + " not found)")
		} else if (refs.size() > 1) {
			throw new RuntimeException("Error updating service (More than one service found matching the name \"${serviceName}\")")
		} else {
			proxyServiceRef = refs.iterator().next();
			this.log.info "Realizing changes in the session: " + sessionName
			if (isProxy) {
				commonServiceConfigurationMBean = domainService.findService(ProxyServiceConfigurationMBean.NAME + "." + sessionName, ProxyServiceConfigurationMBean.TYPE, null);
			} else {
				commonServiceConfigurationMBean = domainService.findService(BusinessServiceConfigurationMBean.NAME + "." + sessionName, BusinessServiceConfigurationMBean.TYPE, null);
			}
			if (enable) {
				commonServiceConfigurationMBean.enableService(proxyServiceRef);
			} else {
				commonServiceConfigurationMBean.disableService(proxyServiceRef);
			}
		}

		//sessionManagementMBean.activateSession(sessionName, (enabled ? "Enabled" : "Disabled") + " serviceName " + Arrays.toString(services));
		sessionManagementMBean.activateSession(sessionName, (enable ? "Enabled" : "Disabled") + " serviceName");
		this.log.info "Activated changes in the session: $sessionName"

		try {
			mbConnection.close()
		} catch (Exception e) {
		}
	}

	def areServicesEnabled(serviceInfoArray, overallResult) {
		if (this.jmxConnector == null) {
			throw new Exception("JMX Connection not initialized");
		}
		def isEnabled = false;
		def serviceQuery = null
		def commonServiceConfigurationMBean = null
        def areAllServicesEnabled = true
        def serviceEnablementFlags = []

		def mbConnection = this.jmxConnector.getMBeanServerConnection()
		def domainService = MBeanServerInvocationHandler.newProxyInstance(mbConnection, new ObjectName(DomainRuntimeServiceMBean.OBJECT_NAME));
		def alsbConfMB = (ALSBConfigurationMBean) domainService.findService(ALSBConfigurationMBean.NAME, ALSBConfigurationMBean.TYPE, null);

		for (serviceInfo in serviceInfoArray) {
			def projectName = serviceInfo[0]
			def serviceName = serviceInfo[1]
			def isProxy = serviceInfo[2]
			def enable = serviceInfo[3]
            serviceQuery = isProxy? new ProxyServiceQuery(): new BusinessServiceQuery();
            serviceQuery.setPath(projectName + "*")
            serviceQuery.setLocalName(serviceName)
            def serviceRef = null
            def refs = alsbConfMB.getRefs(serviceQuery)

            if (refs.isEmpty()) {
                throw new RuntimeException("Error finding service (Service " + serviceName + " not found)")
            } else if (refs.size() > 1) {
                throw new RuntimeException("Error finding service (More than one service found matching the name \"${serviceName}\")")
            } else {
                serviceRef = refs.iterator().next();
                if (isProxy) {
                    commonServiceConfigurationMBean = domainService.findService(ProxyServiceConfigurationMBean.NAME, ProxyServiceConfigurationMBean.TYPE, null);
                } else {
                    commonServiceConfigurationMBean = domainService.findService(BusinessServiceConfigurationMBean.NAME, BusinessServiceConfigurationMBean.TYPE, null);
                }
                def isThisServiceEnabled = commonServiceConfigurationMBean.isEnabled(serviceRef)
                areAllServicesEnabled = areAllServicesEnabled && isThisServiceEnabled
                serviceEnablementFlags.add([projectName, serviceName, isThisServiceEnabled])
            }
        }

		try {
			mbConnection.close()
		} catch (Exception e) {
		}

		return overallResult? areAllServicesEnabled : serviceEnablementFlags
    }

	def isServiceEnabled(projectName, serviceName, isProxy) {
		if (this.jmxConnector == null) {
			throw new Exception("JMX Connection not initialized");
		}
		def isEnabled = false;
		def serviceQuery = null
		def commonServiceConfigurationMBean = null

		def isSessionOpen = false

		def mbConnection = this.jmxConnector.getMBeanServerConnection()

		def domainService = MBeanServerInvocationHandler.newProxyInstance(mbConnection, new ObjectName(DomainRuntimeServiceMBean.OBJECT_NAME));
		def alsbConfMB = (ALSBConfigurationMBean) domainService.findService(ALSBConfigurationMBean.NAME, ALSBConfigurationMBean.TYPE, null);

		serviceQuery = isProxy? new ProxyServiceQuery(): new BusinessServiceQuery();
		serviceQuery.setPath(projectName + "*")
		serviceQuery.setLocalName(serviceName)
		def proxyServiceRef = null
		def refs = alsbConfMB.getRefs(serviceQuery)

		if (refs.isEmpty()) {
			throw new RuntimeException("Error finding service (Service " + serviceName + " not found)")
		} else if (refs.size() > 1) {
			throw new RuntimeException("Error finding service (More than one service found matching the name \"${serviceName}\")")
		} else {
			proxyServiceRef = refs.iterator().next();
			if (isProxy) {
				commonServiceConfigurationMBean = domainService.findService(ProxyServiceConfigurationMBean.NAME, ProxyServiceConfigurationMBean.TYPE, null);
			} else {
				commonServiceConfigurationMBean = domainService.findService(BusinessServiceConfigurationMBean.NAME, BusinessServiceConfigurationMBean.TYPE, null);
			}
			isEnabled = commonServiceConfigurationMBean.isEnabled(proxyServiceRef);
		}

		try {
			mbConnection.close()
		} catch (Exception e) {
		}

		return isEnabled
	}

	def switchEnablementIfRequired(project, serviceName, isProxy, shouldBeEnabled) {
		try {
			def isServiceEnabled = isServiceEnabled(project, serviceName, isProxy)
			log.info "Service ${project}\\...\\${serviceName} is ${isServiceEnabled?'enabled':'disabled'}"
			if (shouldBeEnabled != isServiceEnabled) {
				setServiceEnabled(project, serviceName, isProxy, shouldBeEnabled)
				log.info "Service ${project}\\...\\${serviceName} successfully ${shouldBeEnabled?'enabled':'disabled'}"
			}
			//previous status is returned so the invoker can know whether the service should be switched back or not
			return isServiceEnabled
		} catch (RuntimeException re) {
			//if the service should be disabled and it's not found then that's ok
			if (re.getMessage().endsWith("not found)") && !shouldBeEnabled) {
				return false //fake a "service was not enabled result"
			} else {
				throw re
			}
		}
	}

	def dispose() {
		try {
			if (this.jmxConnector != null) {
				this.jmxConnector.close();
			}
		} catch (IOException ioe) {
			logger.error("Error when closing the connection.");
		}
	}

	def customizePipeline(String target, String mappingSource, String mappingDestination) {
		customizePipeline(target, mappingSource, mappingDestination, "OSB Customization")
	}

    /*
    <?xml version="1.0" encoding="UTF-8"?>
<cus:Customizations xmlns:cus="http://www.bea.com/wli/config/customizations" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xt="http://www.bea.com/wli/config/xmltypes">
    <cus:customization xsi:type="cus:EnvValueActionsCustomizationType">
        <cus:description/>
        <cus:owners>
            <xt:owner>
                <xt:type>BusinessService</xt:type>
                <xt:path>EventServices/bp/ManageScanNoPANInstanced/v1/business/PublishScanReceivedJms</xt:path>
            </xt:owner>
        </cus:owners>
        <cus:actions>
            <xt:replace>
                <xt:envValueType>Service URI</xt:envValueType>
                <xt:location>0</xt:location>
                <xt:value xsi:type="xs:string" xmlns:xs="http://www.w3.org/2001/XMLSchema">jms:///uk.co.yodel.jms.eventservices.XAConnectionFactory/uk.co.yodel.jms.eventservices.v1.ScanReceived</xt:value>
            </xt:replace>
            <xt:replace>
                <xt:envValueType>Service URI Table</xt:envValueType>
                <xt:value xsi:type="tran:URITableType" xmlns:tran="http://www.bea.com/wli/sb/transports">
                    <tran:tableElement>
                        <tran:URI>jms:///uk.co.yodel.jms.eventservices.XAConnectionFactory/uk.co.yodel.jms.eventservices.v1.ScanReceived</tran:URI>
                        <tran:weight>0</tran:weight>
                    </tran:tableElement>
                </xt:value>
            </xt:replace>
       </cus:actions>
    </cus:customization>
</cus:Customizations>
    */

	def customizeBizSvcEndpoint(bizSvcReference, replacementURI) {
        log.info "customizeBizSvcEndpoint(${bizSvcReference}, ${replacementURI})"

		def customizations = new ArrayList<Customization>()

        def description = ""
        def owner = new Ref(Refs.BUSINESS_SERVICE_TYPE, bizSvcReference.split('/'))
        def envValues = new ArrayList()
        envValues.add(new QualifiedEnvValue(owner, EnvValueTypes.SERVICE_URI, "0", replacementURI))
        envValues.add(new QualifiedEnvValue(owner, EnvValueTypes.SERVICE_URI_WEIGHT, "0", '0'))
        def uritable = '<xml-fragment xmlns:tran="http://www.bea.com/wli/sb/transports" xmlns:cus="http://www.bea.com/wli/config/customizations" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xt="http://www.bea.com/wli/config/xmltypes">'
        uritable += '<tran:tableElement>'
        uritable += "<tran:URI>${replacementURI}</tran:URI>"
        uritable += '<tran:weight>0</tran:weight>'
        uritable += '</tran:tableElement>'
        uritable += '</xml-fragment>'
        def uriXML = org.apache.xmlbeans.XmlObject.Factory.parse(uritable)
        log.info "new QualifiedEnvValue(${owner}, ${EnvValueTypes.SERVICE_URI_TABLE}, '', ${uriXML})"
        envValues.add(new QualifiedEnvValue(owner, EnvValueTypes.SERVICE_URI_TABLE, '', uriXML))

        def evcustomization = new EnvValueCustomization(description, envValues)
        //print evcustomization.toXML()
        customizations.add(evcustomization)

        log.info "==> applyCustomizations(${customizations})"
        applyCustomizations(customizations)
    }

	/**
	 * Provide full paths of each argument
	 */
	def customizePipeline(String targetPath, String mappingSourcePath, String mappingDestinationPath, String description) {
		targets = new HashSet()
		targets.add(new Ref(Refs.PIPELINE_TYPE, targetPath.split('/')))

		def source = new Ref(Refs.BUSINESS_SERVICE_TYPE, mappingSourcePath.split('/'))
		this.log.info "source is ${source}"
		def destination = new Ref(Refs.BUSINESS_SERVICE_TYPE, mappingDestinationPath.split('/'))
		this.log.info "destination is ${destination}"

		mappings = new HashMap()
		mappings.put(source, destination)

        this.log.info "Customization of ${target.getLocalName()} as follows: changed source ${source.getLocalName()} to destination ${destination.getLocalName()}"

		customizations = new ArrayList<ReferenceCustomization>()
        customizations.add(new ReferenceCustomization(targets, description, mappings))
        applyCustomizations(customizations)
	}

	def applyCustomizations(customizations) {
        log.info "Applyging ${customizations.size()} customizations"
        def sessionName = "SoapUI-JMX-" + System.currentTimeMillis()
		def mbConnection = this.jmxConnector.getMBeanServerConnection()
		def domainService = MBeanServerInvocationHandler.newProxyInstance(mbConnection, new ObjectName(DomainRuntimeServiceMBean.OBJECT_NAME));
		def sessionManagementMBean = null
        def alsbConfMB = null;
		try {
			sessionManagementMBean = domainService.findService(SessionManagementMBean.NAME, SessionManagementMBean.TYPE, null)
			this.log.info "Creating new Weblogic change session $sessionName";
			sessionManagementMBean.createSession(sessionName);
			alsbConfMB = (ALSBConfigurationMBean) domainService.findService(ALSBConfigurationMBean.NAME + "." + sessionName, ALSBConfigurationMBean.TYPE, null);
			alsbConfMB.customize(customizations)
			sessionManagementMBean.activateSession(sessionName, "Activated SoapUI changes in the session: $sessionName");
			this.log.info "Activated changes in the session: $sessionName"
		} catch (Exception ex) {
			this.log.info "Exception occurred: ${ex}"
		}
	}
}
