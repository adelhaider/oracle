def fromSqlDate(sqlDate) {
    return new java.util.Date(sqlDate.getTime());
}

def toSqlDate(javaDate) {
    return new java.sql.Date(javaDate.getTime());
}

def loadSqlData(sql, file) {
	java.io.BufferedReader br = new java.io.BufferedReader(new java.io.FileReader(new java.io.File(file)));
	def line = null
	while ((line = br.readLine()) != null) {
		sql.execute line
	}
	br.close()
}