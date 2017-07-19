//import static com.aestasit.infrastructure.ssh.DefaultSsh.*
import com.aestasit.infrastructure.ssh.dsl.SshDslEngine
import com.aestasit.infrastructure.ssh.SshOptions
import com.aestasit.infrastructure.ssh.log.SysOutLogger

class FileUtils implements Serializable {

	def initialized = false
	def log = null
	def URL = "oracle:welcome1@localhost:22"
	def engine = null

	/**
	Used for remote connections	
	*/
	def init(host, port, user, password, log) {
		this.log = log
		if (!initialized) {
			URL = user + ":" + password + "@" + host + ":" + port
			def options = new SshOptions()
			options.with {
			  logger = new SysOutLogger()

			  defaultHost = host
			  defaultUser = user
			  defaultPassword = password
			  defaultPort = port

			  reuseConnection = true
			  trustUnknownHosts = true

			  execOptions.with {
				showOutput = true
				failOnError = true
				succeedOnExitStatus = 0
				maxWait = 30000
			  }

			  scpOptions.with {
				verbose = true
				showProgress = true
			  }

			}
			engine = new SshDslEngine(options)
			initialized = true
		}
	}
	
//	def waitForFileConsumption(path) {
//		if (this.engine == null) {
//			throw new Exception("Remote SSH connection is not initialized");
//		}
//		try {
//			log.info "Waiting for file to be consumed ..."
//			def exists = true
//			while (exists) {
//				sleep(30000)
//				if (countFilesInRemoteFolder(path) == 0)
//					exists = false
//			}
//			log.info "... file Consumed!"
//		} catch (e) {
//			this.log.error "Error waiting for file consumption!"
//			throw e;
//		}
//	}
	
	//def waitForFileConsumption(file) {
	//	if (this.engine == null) {
	//		throw new Exception("Remote SSH connection is not initialized");
	//	}
	//	try {
	//		log.info "Waiting for file to be consumed ..."
			//engine.remoteSession() {
			//	def command = "while [ -f " + file + " ]; do sleep 1; done"
			//	exec command
			//}
			
	//		def command = "test -f " + file
	//		def exists = true
	//		while (exists) {
	//			countFilesInRemoteFolder(file)
	//		}
	//		log.info "... file Consumed!"
	//	} catch (e) {
	//		this.log.error "Error waiting for file consumption!"
	//		throw e;
	//	}
	//}	
		
	def clearRemoteFolder(path) {
		if (this.engine == null) {
			throw new Exception("Remote SSH connection is not initialized");
		}
		try {
			log.info "Clearing remote folder " + path
			engine.remoteSession() {
				def command = "rm -rf " + path + "/*"
				exec command
			}
			log.info "... done!"
		} catch (e) {
			this.log.error "Error counting files in remote folder " + path
			throw e;
		}
	}
	
	def uploadFile(source, target) {
		if (this.engine == null) {
			throw new Exception("Remote SSH connection is not initialized");
		}
		try {
			log.info"Uploading $source to $target"
			engine.remoteSession() {
				scp {
				  from { localFile source }
				  into { remoteFile target }
				}
			}
			log.info "... done!"
		} catch (e) {
			this.log.error "Error uploading file!"
			throw e;
		}
	}
		
	def countFilesInRemoteFolder(path) {
		if (this.engine == null) {
			throw new Exception("Remote SSH connection is not initialized");
		}
		def countResult = null
		try {
			log.info "Counting files in remote folder " + path
			engine.remoteSession() {
				def command = 'ls -1 ' + path + ' | wc -l'
				countResult = exec command
			}
			log.info("Number of files is " + countResult.getOutput())
		} catch (e) {
			this.log.error "Error counting files in remote folder " + path
			throw e;
		}
		return countResult.getOutput().toInteger()
	}

	
	/**
	Methods for Local changes
	*/
	def clearFolder(path) {
		new File(path).eachFile{ file ->                
			file.delete()
		}
	}

	def countFilesInFolder(path) {
		def numErrorFiles = 0
		new File(path).eachFile{ file ->                
			numErrorFiles++
		}
		return numErrorFiles
	}
}