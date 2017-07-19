//http://www.robert-nemet.com/2011/11/groovy-xml-parsing-in-soapui.html

import com.eviware.soapui.support.XmlHolder

import javax.xml.*;
import javax.xml.validation.*;
import javax.xml.transform.stream.*;

import org.xml.sax.SAXException;
import org.xml.sax.SAXParseException;

import org.custommonkey.xmlunit.*;

def getXmlHolder(context, xmlText, customNamespaces) {
	def namespaces = [
		  ['soap11', 'http://schemas.xmlsoap.org/soap/envelope/']
		, ['soap12', 'http://www.w3.org/2003/05/soap-envelope']
		, ['wlsjms', 'http://www.bea.com/WLS/JMS/Message']
	]
	def groovyUtils = new com.eviware.soapui.support.GroovyUtils(context)
	def newHolder = groovyUtils.getXmlHolder(xmlText)

	//add default namespace prefixes
	for (namespace in namespaces) {
		newHolder.declareNamespace(namespace[0], namespace[1])
	}
	if (customNamespaces != null) {
		for (customNamespace in customNamespaces) {
			newHolder.declareNamespace(customNamespace[0], customNamespace[1])
		}
	}

	return newHolder
}

def getXmlHolderFromNode(node, customNamespaces) {
	def namespaces = [
		  ['soap11', 'http://schemas.xmlsoap.org/soap/envelope/']
		, ['soap12', 'http://www.w3.org/2003/05/soap-envelope']
		, ['wlsjms', 'http://www.bea.com/WLS/JMS/Message']
	]
	def newHolder = new XmlHolder(node)

	//add default namespace prefixes
	for (namespace in namespaces) {
		newHolder.declareNamespace(namespace[0], namespace[1])
	}
	if (customNamespaces != null) {
		for (customNamespace in customNamespaces) {
			newHolder.declareNamespace(customNamespace[0], customNamespace[1])
		}
	}

	return newHolder
}

def getXmlHolder(context, xmlText) {
	return getXmlHolder(context, xmlText, null)
}

def fromXmlDate(xmlDate) {
	def xmlTypeFactory = javax.xml.datatype.DatatypeFactory.newInstance()
	def calendar = xmlTypeFactory.newXMLGregorianCalendar(xmlDate)
	return calendar.toGregorianCalendar().getTime()
}

def isXmlDateTime(strDateTime) {
	try {
		new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ").parse(strDateTime)
		return true
	} catch (java.text.ParseException pe) {
		return false;
	}
}

def validateXmlAgainsXsd(String xml, File xsd) {
	def localXml = xml
	try {
		if (localXml.startsWith("<?xml")) {
			def xmlHeaderEnd = localXml.indexOf(">")
			localXml = localXml.substring(xmlHeaderEnd + 1)
		}
		SchemaFactory factory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
		Schema schema = factory.newSchema(new StreamSource(xsd));
		Validator validator = schema.newValidator();
		validator.validate(new StreamSource(new StringReader(localXml)));
		return null;
	} catch (all) {
		return all.message;
	}
}

def printSchemaValidationErrors(xml, xsd, log) {
    SchemaFactory factory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
    Schema schema = factory.newSchema(new StreamSource(xsd));
    Validator validator = schema.newValidator();
    validator.setErrorHandler(new org.xml.sax.ErrorHandler() {
		def logger = null;
		public void warning(SAXParseException exception) throws SAXException {
			logger.info String.format(" >>> warning :: line %s, col %s :: %s", exception.getLineNumber(), exception.getColumnNumber(), exception.getMessage());
		}
		public void error(SAXParseException exception) throws SAXException {
			logger.info String.format(" >>> error :: line %s, col %s :: %s", exception.getLineNumber(), exception.getColumnNumber(), exception.getMessage());
        }
        public void fatalError(SAXParseException exception) throws SAXException {
			logger.info String.format(" >>> fatalError :: line %s, col %s :: %s", exception.getLineNumber(), exception.getColumnNumber(), exception.getMessage());
		}
        public org.xml.sax.ErrorHandler init(logger) {
			this.logger = logger
			return this
		}
	}.init(log));
	validator.validate(new StreamSource(new StringReader(xml)));
}

def compareXML(String firstXML, String secondXML) {
    XMLUnit.setIgnoreWhitespace(true)
    XMLUnit.setIgnoreComments(true)
    XMLUnit.setIgnoreDiffBetweenTextAndCDATA(true)
    XMLUnit.setNormalizeWhitespace(true)

    return XMLUnit.compareXML(firstXML, secondXML)
}

def isXMLIdentical(String firstXML, String secondXML) {
    return compareXML(firstXML, secondXML).identical()
}
