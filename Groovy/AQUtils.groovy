import oracle.jdbc.pool.OracleDataSource;
import oracle.jdbc.OracleConnection;
import oracle.jdbc.aq.*;

import oracle.xdb.XMLType

class AQUtils implements Serializable {
  def isInitialized = false
  def log = null
  def ods = null
  def conn = null
  def notificationLister = null
  def defaultWait = 10

  def init(jdbcURL, username, password, log) {
    this.log = log
    if (this.isInitialized) {
			log.info "This AQUtils instance is already initialized"
			return
		}
    log.info "Creating Oracle DB connection to ${jdbcURL}"
    try {
        // create the data source
        ods = new OracleDataSource()

        // set connection properties
        ods.setURL(jdbcURL)
        ods.setUser(username)
        ods.setPassword(password)

        // open the connection to the database
        conn = (OracleConnection) ods.getConnection()
        log.info "Connection created"
        this.isInitialized = true
    } catch (all) {
      log.info "Unable to connect to ${jdbcURL} for AQ management due to ${all.getMessage()}"
    }
  }

  def close() {
      try {
          conn.close();
          ods.close();
      } catch (all) {
          log.info "Unable to close connection to ${conn} and/or data source ${ods} due to ${all.getMessage()}"
      } finally {
          this.isInitialized = false
      }
  }

  /*def registerNotificationListener(queueName) {
    //TODO - http://docs.oracle.com/database/121/JJDBC/streamsaq.htm#JJDBC28803
    notificationLister = new AQXMLTypeQueueListener(conn, queueName)
  }*/

  def enqueueMessage(queueName, agentName, message) {
    try {
      // Create the message properties object
      log.debug "Preparing message properties"
      AQMessageProperties msgprop = AQFactory.createAQMessageProperties()

      // Set some properties (optional)
      msgprop.setPriority(1)
      msgprop.setExpiration(0)
      //msgprop.setExceptionQueue("AQ\$_QT_DS_PARCEL_EVENT_E")

      log.debug "Creating agent"
      AQAgent agent = AQFactory.createAQAgent()
      agent.setName(agentName)
      //agent.setAddress(agentAddress)
      msgprop.setSender(agent)

      // Create the message
      log.debug "Creating message"
      AQMessage mesg = AQFactory.createAQMessage(msgprop)

      // Set the payload with XMLType object
      log.debug "Setting message payload"
      mesg.setPayload(new XMLType(conn,message))

      // Set the enqueue options using the setXXX methods of AQEnqueueOptions.
      AQEnqueueOptions options = new AQEnqueueOptions()

      // Enqueue the message
      log.info "Enqueuing message"
      conn.enqueue(queueName, options, mesg)
    } catch (all) {
      log.info "Unable to enqueue message to ${queueName} due to ${all.getMessage()}"
    }
  }

  def dequeueMessage(queueName, verbose) {
    dequeueMessage(queueName, null, verbose)
  }

  def dequeueMessage(queueName, options, verbose) {
    def message = null
    try {
      // Set the dequeue options using the setXXX methods of AQEnqueueOptions.
      if (options == null) {
          options = new AQDequeueOptions()
      }
      if (options.getWait() < 0){
        options.setWait(defaultWait) // set a wait time to default defined in this class
      }

      // Dequeue the message - remember to use XMLTYPE
      verbose ? log.info("Dequeuing message") : {}
      message = conn.dequeue(queueName, options, "XMLTYPE")
      if (message != null) {
        message = message.getXMLTypePayload().getStringVal()
      }
    } catch (all) {
      log.info "Unable to dequeue message from queue ${queueName} due to ${all.getMessage()}"
    } finally {
      return message
    }
  }

  def purgeQueue(queueName) {
    log.info "Purging AQ queue ${queueName}"
    def msgCount = 0
    try {
      def msg = null
      AQDequeueOptions options = new AQDequeueOptions()
      options.setWait(AQDequeueOptions.DEQUEUE_NO_WAIT)
      while (true) {
        msg = dequeueMessage(queueName, options, false)
        msgCount++
        if (msg == null) {
          break
        }
      }
      log.info "Purged ${msgCount} messages!"
    } catch (all) {
      log.info "Unable to purge message from ${queueName} due to ${all.getMessage()}"
    }
  }
}

/*class AQXMLTypeQueueListener implements AQNotificationListener
{
  def conn
  def queueName
  def typeName = "XMLTYPE"
  def payload

  int eventsCount = 0

  def AQXMLTypeQueueListener(oracleConnection, aqQueueName) {
     this.queueName = aqQueueName
     this.conn = oracleConnection;
  }

  def void onAQNotification(AQNotificationEvent e) {
      try {
         AQDequeueOptions options = new AQDequeueOptions()
         //options.setRetrieveMessageId(true)

         if(e.getConsumerName() != null)
           options.setConsumerName(e.getConsumerName())

         if((e.getMessageProperties()).getDeliveryMode() == AQMessageProperties.DeliveryMode.BUFFERED) {
           options.setDeliveryMode(AQDequeueOptions.DEQUEUE_BUFFERED)
           options.setVisibility(AQDequeueOptions.DEQUEUE_IMMEDIATE)
         }

         AQMessage msg = conn.dequeue(queueName, options, typeName)

         //log.info "ID of message dequeued is ${msg.getMessageId()}"
         //log.info(msg.getMessageProperties().toString())

         payload = msg.getXMLTypePayload().getStringVal()
      } catch(all) {
        log.info "Failure on notification event for queue ${queueName} due to ${all.getMessage()}"
      }
      eventsCount++
  }

  def getPayload() {
      return payload
  }

  def getEventsCount() {
      return eventsCount;
  }

  def closeConnection() {
      conn.close();
  }
}
*/
