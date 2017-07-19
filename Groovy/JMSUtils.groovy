import javax.naming.*
import javax.jms.*;
import oracle.jms.TopicReceiver;
import javax.management.*;
import javax.management.openmbean.CompositeData;
import javax.management.remote.*;
import java.io.Closeable;

class JMSUtils implements Serializable {

	def isInitialized = false
	def log = null
	def ctxs = null
	def jmxCons = null
	def context = null
	def xmlUtils = null
	def urls = null
	def username = null
	def passwd = null

	def wlsJmsNamespaces = [
		  ['wlsjms', 'http://www.bea.com/WLS/JMS/Message']
	]

	def init(urls, username, passwd, log) {
		if (this.isInitialized) {
			log.info "This JMSUtils instance is already initialized"
			return
		}
		this.log = log
		this.urls = urls
		this.username = username
		this.passwd = passwd

		this.ctxs = []
		this.jmxCons = []
		urls.each { url ->
			log.info "Creating JNDI connection to ${url}"
			try {
				Hashtable<String, String> properties = new Hashtable<String, String>()
				properties.put(Context.INITIAL_CONTEXT_FACTORY, "weblogic.jndi.WLInitialContextFactory")
				properties.put(Context.PROVIDER_URL, 't3://' + url);
				properties.put(Context.SECURITY_PRINCIPAL, username)
				properties.put(Context.SECURITY_CREDENTIALS, passwd)
				this.ctxs.add new InitialContext(properties)
				log.info "Got InitialContext for ${url}"
			} catch (all) {
				log.info "Unable to connect to ${url} for JNDI lookups due to ${all.getMessage()}"
			}

			log.info "Creating JMX connection to ${url}"
			try {
				def fullServerURL = "service:jmx:iiop://" + url + "/jndi/weblogic.management.mbeanservers.runtime";
				def serviceUrl = new JMXServiceURL(fullServerURL);

				def env = new Hashtable<String, String>();
				env.put(JMXConnectorFactory.PROTOCOL_PROVIDER_PACKAGES, "weblogic.management.remote");
				env.put(Context.INITIAL_CONTEXT_FACTORY, "weblogic.jndi.WLInitialContextFactory");
				env.put(Context.SECURITY_PRINCIPAL, username);
				env.put(Context.SECURITY_CREDENTIALS, passwd);

				def jmxCon = JMXConnectorFactory.newJMXConnector(serviceUrl, env);
				jmxCon.connect();
				this.jmxCons.add jmxCon
			} catch (all) {
				log.info "Unable to connect to ${url} for JMX management due to ${all.getMessage()}"
			}
		}
		if (this.jmxCons.size() == 0 || this.jmxCons.size() == 0) {
			throw new RuntimeException("Unable to create at least one connection of each type")
		}
		this.isInitialized = true
	}
	
	def getNewInitialContext(url) {
		try {
			Hashtable<String, String> properties = new Hashtable<String, String>()
			properties.put(Context.INITIAL_CONTEXT_FACTORY, "weblogic.jndi.WLInitialContextFactory")
			properties.put(Context.PROVIDER_URL, 't3://' + url);
			properties.put(Context.SECURITY_PRINCIPAL, username)
			properties.put(Context.SECURITY_CREDENTIALS, passwd)
			def ctx = new InitialContext(properties)
			return ctx
		} catch (all) {
			log.info "Unable to connect to ${url} for JNDI lookups due to ${all.getMessage()}"
		}
		throw new RuntimeException("Unable to create at new initial context!")
	}
	
	def setContext(context) {
		this.context = context
	}
	
	def setXmlUtils(xmlUtils) {
		this.xmlUtils = xmlUtils
	}

	/*
		Queues
	*/
		
	def sendMessage(connectionFactoryName, queueName, messageText) {
		def msgSent = false
		def index = 0
		def currCtx
		def qsndr
		def qsess
		def qc
		while (!msgSent && index < ctxs.size) {
			try {
				currCtx = ctxs[index]
				def qcf = currCtx.lookup(connectionFactoryName)
				qc = qcf.createQueueConnection()
				qsess = qc.createQueueSession(false, 0)
				def q = (Queue) currCtx.lookup(queueName)
				qsndr = qsess.createSender(q)
				def message = qsess.createTextMessage()
				message.setText(messageText)
				qsndr.send(message)
				log.debug "Message sent to ${queueName}"
				msgSent = true
			} catch (all) {
				log.info "Error sending message to Q (${queueName}) via ${currCtx}: ${all}"
			} finally {
				close(qsndr, qsess, qc)
			}
			index++
		}
		if (!msgSent) {
			throw new Exception("Error sending message")
		}
	}
	
	/* deprecated - use purgeQueue/purgeTopic
	def clearQueue(connectionFactoryName, queueName) {
		log.info "Clearing queue"
		def msg = receiveMessageFromQueue(connectionFactoryName, queueName)
		while (msg != null) {
			log.info "Message found. Ignoring it and looking for more."
			msg = receiveMessageFromQueue(connectionFactoryName, queueName)
		}
	}
	*/

	def receiveMessageFromQueue(connectionFactoryName, queueName) {
		return receiveMessageFromQueue(connectionFactoryName, queueName, 1)
	}
	
	def receiveMessageFromQueue(cfJndiName, qJndiName, qName, timeout) {
		def t0 = System.currentTimeMillis()
		def msg = receiveMessageFromQueue(cfJndiName, qJndiName, 1)
		if (msg == null) {
			def cnt = getCurrentMsgCount(qName)
			while (cnt > 0 && (System.currentTimeMillis() - t0) < timeout) {
				msg = receiveMessageFromQueue(cfJndiName, qJndiName, 1)
				if (msg != null) {
					return msg
				}
				cnt = getCurrentMsgCount(qName)
			}
		} else {
			return msg
		}
		return null
	}

	def receiveMessageFromQueue(connectionFactoryName, queueName, timeout) {
		log.info "receiveMessageFromQueue($queueName)"
		def currCtx = null
		def qc = null
		def qsess = null
		def qr = null
		def index = 0
		def msgReceived = false
		def msg = null
		for (String url: urls) {
			log.info "Trying to receive msg from $queueName @ $url"
			try {
				currCtx = getNewInitialContext(url)
				def qcf = currCtx.lookup(connectionFactoryName)
				qc = qcf.createQueueConnection()
				qsess = qc.createQueueSession(false, QueueSession.SESSION_TRANSACTED)
				def q = currCtx.lookup(queueName)
				qr = qsess.createReceiver(q)
				qc.start()
				msg = qr.receive(timeout)
				if (msg != null) {
					log.info "Returning message from node $url"
					msgReceived = true
          if (msg instanceof TextMessage) {
              return ((TextMessage) msg).getText();
					} else if (msg instanceof BytesMessage) {
              int msgLength = (int)((BytesMessage)msg).getBodyLength()
              byte[] byteArr = new byte[msgLength];
              for (int i = 0; i < msgLength; i++) {
                byteArr[i] = msg.readByte();
              }
              return new String(byteArr);
					} else {
              return msg.toString();
					}
				}
			} catch (all) {
				log.info "Error receiving message via ${currCtx}: ${all}"
			} finally {
				close(qr, qsess, qc, currCtx)
			}
		}
		log.info "Didn't find messages in any node"
		return null
//		if (!msgReceived) {
//			throw new Exception("Error receiving message from queue")
//		}
	}
	
	/*
		Topics
	*/
	
	def clearTopic(connectionFactoryName, topicName, subscriberName) {
        def connection = null;
        def session = null;
		def index = 0
		while (index < ctxs.size) {
			try {
				def ctx = ctxs.get(index);
				def qcf = ctx.lookup(connectionFactoryName);
				connection = qcf.createTopicConnection();
				connection.setClientID(subscriberName);
				session = connection.createTopicSession(false, 0);
				def t = ctx.lookup(topicName);
				def topicSubscriber = session.createDurableSubscriber(t, subscriberName);
				connection.start();
				def msg = topicSubscriber.receive(1);
				while (msg != null) {
					msg = topicSubscriber.receive(1);
				}
				connection.stop();
				return;
			} catch (all) {
				all.printStackTrace(System.err);
				throw all
			} finally {
				close(session, connection);
			}
			index++
		}
    }

	def consumeFromTopic(connectionFactoryName, topicName, subscriberName, timeout) {
		log.info "Consuming from topic $connectionFactoryName/$topicName >> $subscriberName"
        def connection = null;
        def session = null;
		def index = 0
		while (index < ctxs.size) {
			try {
				def ctx = ctxs.get(index);
				def qcf = ctx.lookup(connectionFactoryName);
				connection = qcf.createTopicConnection();
				connection.setClientID(subscriberName);
				session = connection.createTopicSession(false, 0);
				def t = ctx.lookup(topicName);
				def topicSubscriber = session.createDurableSubscriber(t, subscriberName);
				connection.start();
				def msg = topicSubscriber.receive(timeout);
				log.info "Retrieved message from topic $msg"
				if (msg != null) {
					if (msg instanceof TextMessage) {
						return ((TextMessage) msg).getText();
					} else if (msg instanceof BytesMessage) {
						return ((BytesMessage) msg).readUTF();
					} else {
						return msg.toString();
					}
				}
				connection.stop();
			} catch (Exception jmse) {
				log.info jmse.getMessage()
			} finally {
				close(session, connection);
			}
			index++
		}
        return null;
    }
	
	def postToTopic(connectionFactoryName, topicName, messageText) {
		def msgSent = false;
		def index = 0;
		def currCtx = null;
		def tc = null
		def tsess = null
		def tpub = null
		while (!msgSent && index < ctxs.size()) {
			try {
				currCtx = ctxs.get(index);
				def cf = (TopicConnectionFactory) currCtx.lookup(connectionFactoryName);
				tc = cf.createTopicConnection();
				tsess = tc.createTopicSession(false, 0);
				def t = (Topic) currCtx.lookup(topicName);
				tpub = tsess.createPublisher(t);
				def message = tsess.createTextMessage();
				message.setText(messageText);
				tpub.send(message);
				log.info "Message sent to ${topicName}";
				close(tc, tsess, tpub);
				msgSent = true;
			} catch (all) {
				log.error "Error sending message via ${currCtx}: ${all}";
			}
			index++;
        }
		if (!msgSent) {
			throw new RuntimeException("Error sending message");
		}
    }


	def getCurrentMsgCount(queueName) {
		def msgCount = 0L
		this.jmxCons.each { jmxCon ->
			def con = jmxCon.getMBeanServerConnection();
			def objectQuery = "com.bea:Type=JMSDestinationRuntime,Name=*!*" + queueName + "*,*";
			def query_obj_name = new ObjectName(objectQuery);
			def searchResult = con.queryNames(query_obj_name, null)
			for (ObjectName obj_name : searchResult) {
				def actualQueueName = obj_name.getKeyProperty("Name")
				def currentQueueMsgCount = con.getAttribute(obj_name, "MessagesCurrentCount")
				log.debug "Found ${currentQueueMsgCount} msgs for queue ${actualQueueName}"
				msgCount += currentQueueMsgCount
			}
		}
		return msgCount
	}

	def getTotalMsgCount(queueName) {
		def msgCount = 0L
		this.jmxCons.each { jmxCon ->
			def con = jmxCon.getMBeanServerConnection();
			def objectQuery = "com.bea:Type=JMSDestinationRuntime,Name=*!*" + queueName + "*,*";
			def query_obj_name = new ObjectName(objectQuery);
			for (ObjectName obj_name : con.queryNames(query_obj_name, null)) {
				def actualQueueName = obj_name.getKeyProperty("Name")
				def currentQueueMsgCount = con.getAttribute(obj_name, "MessagesReceivedCount")
				log.debug "Found ${currentQueueMsgCount} msgs for queue ${actualQueueName}"
				msgCount += currentQueueMsgCount
			}
		}
		return msgCount
	}

	def purgeQueue(queueName) {
		this.jmxCons.each { jmxCon ->
			def con = jmxCon.getMBeanServerConnection();
			def objectQuery = "com.bea:Type=JMSDestinationRuntime,Name=*!*" + queueName + "*,*";
			def query_obj_name = new ObjectName(objectQuery);
			for (ObjectName obj_name : con.queryNames(query_obj_name, null)) {
				def actualQueueName = obj_name.getKeyProperty("Name")
				Object[] paramValues = ["1=1"] as Object[]
				String[] paramTypes = ['java.lang.String'] as String[]
				try {
					Integer deletionCount = con.invoke(obj_name, "deleteMessages", paramValues, paramTypes)
					log.info "Purged queue (${deletionCount} messages deleted)"
				} catch (javax.naming.NamingException jne) {
					log.info jne.getMessage()
					throw jne
				} catch (all) {
					log.info all.getMessage()
					throw all
				}
			}
		}
	}
	
	def queueMsgCurrentCount(queueName) {
		for (jmxCon in jmxCons) {
			def con = jmxCon.getMBeanServerConnection();
			def objectQuery = "com.bea:Type=JMSDestinationRuntime,Name=*!*" + queueName + "*,*";
			log.debug "Looking up topic: " + objectQuery
			def query_obj_name = new ObjectName(objectQuery);
			for (ObjectName obj_name : con.queryNames(query_obj_name, null)) {
				def actualQueueName = obj_name.getKeyProperty("Name")
				log.debug "Counting messages (current) for  $actualQueueName"
				Integer msgCurrentCount = con.getAttribute(obj_name, "MessagesCurrentCount")
				log.debug "Found  $msgCurrentCount messages"
				return msgCurrentCount
			}
		}
		return null
	}

	
	def purgeTopic(topicName, subscriberName) {
		this.jmxCons.each { jmxCon ->
			def con = jmxCon.getMBeanServerConnection();
			def objectQuery = "com.bea:Type=JMSDurableSubscriberRuntime,Name=" + subscriberName + "*,*";
			log.info "Looking up topic: " + objectQuery
			def query_obj_name = new ObjectName(objectQuery);
			for (ObjectName obj_name : con.queryNames(query_obj_name, null)) {
				def actualTopicName = obj_name.getKeyProperty("Name")
				log.info "Purging topic $actualTopicName"
				Object[] paramValues = ["1=1"] as Object[]
				String[] paramTypes = ['java.lang.String'] as String[]
				try {
					Integer deletionCount = con.invoke(obj_name, "deleteMessages", paramValues, paramTypes)
					log.info "Purged topic (${deletionCount} messages deleted)"
				} catch (javax.naming.NamingException jne) {
					log.info jne.getMessage()
					throw jne
				} catch (all) {
					log.info all.getMessage()
					throw all
				}
			}
		}
	}
	
	def topicSubscriberMsgCurrentCount(topicName, subscriberName) {
		for (jmxCon in jmxCons) {
			def con = jmxCon.getMBeanServerConnection();
			def objectQuery = "com.bea:Type=JMSDurableSubscriberRuntime,Name=" + subscriberName + "*,*";
			log.debug "Looking up topic: " + objectQuery
			def query_obj_name = new ObjectName(objectQuery);
			for (ObjectName obj_name : con.queryNames(query_obj_name, null)) {
				def actualTopicName = obj_name.getKeyProperty("Name")
				log.debug "Counting messages (current) for  $actualTopicName"
				Integer msgCurrentCount = con.getAttribute(obj_name, "MessagesCurrentCount")
				log.debug "Found  $msgCurrentCount messages"
				return msgCurrentCount
			}
		}
		return null
	}
	
	def findMessage(queueName, msgId) {
		assert context != null && xmlUtils != null, "Context or XML utils not initialized"
		
		def msgBody = null
		for (jmxCon in jmxCons) {
			def con = jmxCon.getMBeanServerConnection();
			def objectQuery = "com.bea:Type=JMSDestinationRuntime,Name=*!*" + queueName + "*,*";
			def query_obj_name = new ObjectName(objectQuery);
			for (ObjectName obj_name : con.queryNames(query_obj_name, null)) {
				def actualQueueName = obj_name.getKeyProperty("Name")
				String msgSelector = "SceeMessageId='" + msgId + "'";
				Object[] paramValues = [msgSelector, new Integer(300), new Integer(0x7fffffff)] as Object[]
				String[] paramTypes = ["java.lang.String", "java.lang.Integer", "java.lang.Integer"] as String[]
				String newCursor = con.invoke(obj_name, "getMessages", paramValues, paramTypes);
				paramValues = [newCursor] as Object[]
				paramTypes = ["java.lang.String"] as String[]
				int cursorSize = con.invoke(obj_name, "getCursorSize", paramValues, paramTypes)
				log.debug "$cursorSize messages found in queue $actualQueueName with ID $msgId"
				if (cursorSize > 0) {
					paramValues = [newCursor, 0L, 10] as Object[]
					paramTypes = ["java.lang.String", "java.lang.Long", "java.lang.Integer"] as String[]
					def data = (CompositeData[]) con.invoke(obj_name, "getItems", paramValues, paramTypes)
					for (CompositeData resItem : data) {
						def msgInfoHolder = xmlUtils.getXmlHolder(context, resItem.get("MessageXMLText"), wlsJmsNamespaces)
						def jmsMsgId = msgInfoHolder['/wlsjms:WLJMSMessage/wlsjms:Header/wlsjms:JMSMessageID']
						log.debug "JMS Message ID: " + jmsMsgId
						paramTypes = ["java.lang.String", "java.lang.String"] as String[]
						def messageData = con.invoke(obj_name, "getMessage", [newCursor, jmsMsgId] as Object[], paramTypes);
						def msgBodyHolder = xmlUtils.getXmlHolder(context, messageData.get("MessageXMLText"), wlsJmsNamespaces)
						return msgBodyHolder['/wlsjms:WLJMSMessage/wlsjms:Body/wlsjms:Text']
					}
				}
			}
		}
		return null
	}

	/*
		public BrowsingResult browse(Environment env, String system, Server server, String username, String password, String queueName, String cursor, int page, int pageSize) {
			CompositeData[] data = null;
			BrowsingResult result = new BrowsingResult();

			JMXConnector jmxCon = null;
			try {
				jmxCon = getJMXConnector(server, username, password);
				jmxCon.connect();
				MBeanServerConnection con = jmxCon.getMBeanServerConnection();
				ObjectName destination = findQueueObjectName(con, SYSTEM_OSB.equals(system) ? env.getOsbJmsModuleName() : env.getSoaJmsModuleName(), queueName);

				Long initialPosition = Long.valueOf((page - 1L) * pageSize);
				if (cursor == null) {
					String newCursor = (String) con.invoke(destination, "getMessages", new Object[] { "true", QueuePersistenceJmxImpl.BROWSE_TIMEOUT }, OP_GET_MESSAGES_SIGNATURE);
					result.setCursor(newCursor);
					con.invoke(destination, "sort", new Object[] { newCursor, POSITION_UNDEFINED, DEFAULT_ORDERING_ATTRS, DEFAULT_ORDER }, OP_SORT_SIGNATURE);
					result.setNumMessages((Long) con.invoke(destination, "getCursorSize", new Object[] { newCursor }, OP_GET_CURSOR_SIZE_SIGNATURE));
					data = (CompositeData[]) con.invoke(destination, "getItems", new Object[] { newCursor, initialPosition, pageSize }, OP_GET_ITEMS_SIGNATURE);
				} else {
					try {
						data = (CompositeData[]) con.invoke(destination, "getItems", new Object[] { cursor, initialPosition, pageSize }, OP_GET_ITEMS_SIGNATURE);
						// TODO: Make sure that the old ManagementException
						// (type-safe API) matches with this one in pure JMX
					} catch (IOException me) {// cursor timeout
						String newCursor = (String) con.invoke(destination, "getMessages", new Object[] { "true", QueuePersistenceJmxImpl.BROWSE_TIMEOUT }, OP_GET_MESSAGES_SIGNATURE);
						result.setCursor(newCursor);
						con.invoke(destination, "sort", new Object[] { newCursor, POSITION_UNDEFINED, DEFAULT_ORDERING_ATTRS, DEFAULT_ORDER }, OP_SORT_SIGNATURE);
						result.setNumMessages((Long) con.invoke(destination, "getCursorSize", new Object[] { newCursor }, OP_GET_CURSOR_SIZE_SIGNATURE));
						data = (CompositeData[]) con.invoke(destination, "getItems", new Object[] { newCursor, initialPosition, pageSize }, OP_GET_ITEMS_SIGNATURE);
					}
				}
				if (data != null) {
					List<JmsMessage> messages = null;
					messages = new ArrayList<JmsMessage>(data.length);
					for (CompositeData messageData : data) {
						JmsMessage msg = toJmsMessage(messageData);
						messages.add(msg);
					}
					result.setMessages(messages);
				}
			} catch (Exception e) {
				throw new RuntimeException("Error while browsing messages", e);
			} finally {
				if (jmxCon != null)
					try {
						jmxCon.close();
					} catch (IOException e) {
						// Silently ignore it
					}
			}

			return result;

		}

		def updatePauseStatus(Environment environment, String systemName, queueNames, boolean pause, boolean forceAll) {
			Vector<QueueInfo> updatedQueues = new Vector<QueueInfo>();
			Collection<Server> serverList;
			String jmsModuleName, username, password;

				serverList = environment.getOsbRuntimeServerList();
				jmsModuleName = environment.getOsbJmsModuleName();
				username = environment.getOsbUsername();
				password = environment.getOsbPassword();


				for (Server server : serverList) {
				JMXConnector jmxCon = null;
				try {
					jmxCon = getJMXConnector(server, username, password);
					jmxCon.connect();
					MBeanServerConnection con = jmxCon.getMBeanServerConnection();
					String action = pause?"pauseConsumption":"resumeConsumption";
					Exception exception = null;
					for (String queueName: queueNames) {
						exception = null;
						try {
							ObjectName destination = findQueueObjectName(con, jmsModuleName, queueName);
							if (pause) {
								Object pauseConsResult = con.invoke(destination, action, null, null);							
								logger.info("Result from pauseConsumption: " + pauseConsResult);
							} else {
								Object resumeConsResult = con.invoke(destination, action, null, null);
								logger.info("Result from resumeConsumption: " + resumeConsResult);
							}
							updatedQueues.add(new QueueInfo(systemName, queueName));
						} catch (NotFoundException nfe) {						
							exception = nfe;
							logger.error("Queue not found name "+jmsModuleName+":"+queueName);
							if (forceAll) {
								throw nfe;
							}
						} catch(Exception e){
							exception = e;
						}finally{
							Audit.getInst().msg(Audit.AuditAction.PauseQueue, action+" of "+jmsModuleName+":"+queueName+" "+" on "+server.getName()+" "+(exception==null?"success":"failed"), null, exception);
						}
					}

				} catch (Exception ioe) {
					//TODO: review
					// throw new RuntimeException("Error while pausing the queue", ioe);
					// ignore the error and continue working with the rest of the nodes
					logger.error("Error while pausing the queue on " + server, ioe);
				} finally {
					if (jmxCon != null)
						try {
							jmxCon.close();
						} catch (IOException e) {
							logger.error("Error while closing JMX connection", e);
						}
				}
			}
			return updatedQueues;
		}
	*/

	def close(Object... closeables) {
		for (closeable in closeables) {
			if (closeable != null) {
//				if (closeable instanceof Closeable) {
					try {
						closeable.close()
					} catch (Exception e) {
					}
//				} else {
//					def clazz = closeable.class
//					while (clazz != null) {
//						def ifaces = closeable.class.interfaces
//						log.info "Implemented interfaces: ${ifaces}"
//						clazz = clazz.parent
//					}
//				}
			}
		}
	}

	/*
	def close(Closeable... closeables) {
		for (closeable in closeables) {
			if (closeable != null) {
				try {
					closeable.close()
				} catch (Exception e) {
				}
			}
		}
	}

	def close(sender, receiver, session, connection) {
		if (sender != null) {
			try {
				sender.close()
			} catch (Exception e) {
			}
		}
		if (receiver != null) {
			try {
				receiver.close()
			} catch (Exception e) {
			}
		}
		if (session != null) {
			try {
				session.close()
			} catch (Exception e) {
			}
		}
		if (connection != null) {
			try {
				connection.close()
			} catch (Exception e) {
			}
		}
	}
	
	def close(conn, tsess, tpub) {
        if (conn != null) {
            try {
                conn.close();
            } catch (all) {
            }
        }
        if (tsess != null) {
            try {
                tsess.close();
            } catch (all) {
            }
        }
        if (tpub != null) {
            try {
                tpub.close();
            } catch (all) {
            }
        }
    }
	*/
}